"""Gerador de código para a linguagem JSS, usando a API `llvmlite.ir`.

Como este gerador funciona
----------------------------
O compilador percorre a AST (a árvore que o `parser.py` construiu) uma vez,
visitando cada nó com um método `visit_<TipoDoNo>` (o clássico "padrão
Visitor"). Cada visitante devolve o valor LLVM correspondente ao nó (uma
constante ou o resultado de uma instrução) e o seu tipo LLVM.

A diferença para uma versão anterior deste arquivo é *como* as instruções
LLVM são criadas: em vez de montar cada linha como texto (`f"{r} = add i32
{a}, {b}"`) e concatenar tudo em uma grande string `.ll`, aqui usamos a API
orientada a objetos `llvmlite.ir`. Cada instrução vira uma chamada de método
do `IRBuilder` (`builder.add(a, b)`), e o resultado é um objeto Python que
"sabe" seu próprio tipo LLVM - não existe mais texto para formatar ou
analisar. Isso elimina uma classe inteira de bugs bobos (nomes de registrador
duplicados, tipos escritos errado, blocos mal fechados) porque quem garante
a validade sintática do IR agora é a própria biblioteca, não nós.

Alguns conceitos de LLVM usados neste arquivo, para quem está lendo pela
primeira vez:
- `alloca`: reserva espaço na pilha da função atual para uma variável -
  o equivalente LLVM de declarar uma variável local em C.
- Bloco básico (`basic block`): uma sequência de instruções que só pode ser
  entrada pelo topo e só sai pelo fim, através de uma instrução terminadora
  (`br`/`ret`). Todo desvio de controle (`if`, `while`, `for`, curto-
  circuito de `&&`/`||`) em LLVM vira uma divisão em múltiplos blocos ligados
  por `br` (desvio incondicional) ou `br i1 cond, ...` (desvio condicional).
- `phi`: a forma que o LLVM usa para dizer "o valor desta variável depende de
  por qual bloco anterior a execução chegou até aqui" - é como resolvemos o
  resultado de `a && b` sem nunca ter avaliado `b` quando `a` já era falso.
- `getelementptr` (GEP): calcula o *endereço* de um elemento dentro de um
  vetor ou de um campo dentro de uma struct, sem ler memória nenhuma - só
  aritmética de ponteiros guiada pelos tipos.
"""

import llvmlite.ir as ir

from frontend.ast_nodes import (
    ProgramNode, VarDeclarationNode, AssignmentNode, BlockNode,
    IfNode, WhileNode, ForNode, BreakNode, FunctionNode, ReturnNode,
    CallNode, BinaryOpNode, UnaryOpNode, ArrayAccessNode, ArrayLiteralNode,
    ClassDeclarationNode, ClassConstructorNode, AttributeAccessNode,
    NewObjectNode, ConsoleLogNode, InputNode, CastNode, NumberNode,
    StringNode, BooleanNode, NullNode, IdentifierNode
)
from backend.runtime_ir import build_runtime

# --- Triple/datalayout do alvo de compilação (Windows x86-64 via MinGW) ---
# `main.py` usa exatamente os mesmos valores para configurar o TargetMachine
# que converte este módulo em código objeto x86 - manter os dois em sincronia
# aqui evita que o LLVM avise sobre incompatibilidade entre o módulo e o alvo.
TARGET_TRIPLE = "x86_64-w64-windows-gnu"
TARGET_DATALAYOUT = (
    "e-m:w-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"
)

# --- Tipos LLVM correspondentes aos tipos primitivos do JSS ---
i1 = ir.IntType(1)          # bool
i32 = ir.IntType(32)        # int
i64 = ir.IntType(64)        # usado em cálculos de tamanho (bytes)
f64 = ir.DoubleType()       # real
i8p = ir.PointerType(ir.IntType(8))  # str (equivalente a "char*")
void = ir.VoidType()


def _zero32():
    """Atalho para a constante i32 0, usada em quase todo `getelementptr`."""
    return ir.Constant(i32, 0)


class Scope:
    """Uma tabela de símbolos encadeada (escopo léxico).

    Cada bloco `{ ... }`, função, método ou construtor abre um novo `Scope`
    que aponta para o escopo onde ele está aninhado (`parent`). Procurar uma
    variável (`lookup`) primeiro olha no escopo atual e, se não achar, sobe
    para o escopo pai - exatamente como a resolução de nomes de blocos
    aninhados funciona na própria linguagem JSS.
    """

    def __init__(self, parent=None):
        self.parent = parent
        self.vars = {}  # nome_jss -> (ponteiro_llvm, tipo_llvm, tipo_jss, dimensao)

    def define(self, name, llvm_ptr, llvm_type, jss_type, dimension=None):
        self.vars[name] = (llvm_ptr, llvm_type, jss_type, dimension)

    def lookup(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.lookup(name)
        return None


class CodeGenerator:
    """Percorre a AST do JSS e constrói um `llvmlite.ir.Module` equivalente."""

    def __init__(self):
        # Cada CodeGenerator usa seu próprio `Context`: isso evita que tipos de
        # struct com o mesmo nome (ex.: duas compilações na mesma execução do
        # Python, como acontece nos testes) colidam entre si no contexto
        # global padrão da llvmlite.
        self.context = ir.Context()
        self.module = ir.Module(name="jss_module", context=self.context)
        self.module.triple = TARGET_TRIPLE
        self.module.data_layout = TARGET_DATALAYOUT

        self.builder = None                 # IRBuilder do bloco sendo preenchido no momento
        self.current_function = None        # ir.Function sendo compilada no momento
        self.current_function_ret_type = None

        self.current_scope = Scope()
        self.loop_stack = []                # pilha de blocos "fim do laço", usada pelo `break`

        self.strings = {}                   # cache de constantes de string do programa do usuário

        # class_name -> {'attrs', 'attr_types', 'attr_dims', 'struct_type', 'methods', 'constructor'}
        self.classes = {}
        # nome_da_funcao_jss -> ir.Function (já com a assinatura completa)
        self.user_functions = {}

        # Injeta print_int, str_concat, ipow, etc. no mesmo módulo - ver runtime_ir.py
        self.runtime = build_runtime(self.module)

    # ------------------------------------------------------------------
    # Pré-processamento: declarar todos os tipos e assinaturas primeiro
    # ------------------------------------------------------------------
    #
    # Antes de compilar qualquer corpo de função/método, percorremos a AST
    # uma vez só para criar (sem preencher) todos os tipos de struct e todas
    # as assinaturas de função/método/construtor. Isso é o que permite:
    #   - chamadas recursivas (uma função/método chamar a si mesma);
    #   - chamar uma função definida mais adiante no arquivo-fonte;
    #   - duas classes referenciarem uma à outra como tipo de atributo.
    # Sem isso, `Node prox` dentro da própria classe `Node` (uma lista
    # encadeada) não teria como ser compilado, porque o tipo `struct.Node`
    # ainda não existiria no momento de processar seu próprio atributo.

    def _preprocess_declarations(self, ast):
        if not isinstance(ast, ProgramNode):
            return

        class_nodes = [s for s in ast.statements if isinstance(s, ClassDeclarationNode)]
        function_nodes = [s for s in ast.statements if isinstance(s, FunctionNode)]

        # 1) Criar os tipos de struct de cada classe, ainda "vazios" (sem campos).
        #    Um IdentifiedStructType pode ser referenciado antes de ter seu corpo
        #    definido - é exatamente esse mecanismo que resolve referências
        #    circulares entre classes.
        for stmt in class_nodes:
            struct_ty = self.context.get_identified_type(f"struct.{stmt.name}")
            self.classes[stmt.name] = {
                'attrs': [], 'attr_types': {}, 'attr_dims': {},
                'struct_type': struct_ty, 'methods': {}, 'constructor': None,
            }

        # 2) Agora que todo tipo de struct já existe (ainda que vazio), preencher
        #    os campos de cada um - inclusive os que apontam para outra classe.
        for stmt in class_nodes:
            info = self.classes[stmt.name]
            fields = []
            for attr in stmt.attributes:
                info['attrs'].append(attr.name)
                info['attr_types'][attr.name] = attr.var_type
                info['attr_dims'][attr.name] = attr.dimension
                fields.append(self.get_llvm_type(attr.var_type, attr.dimension))
            info['struct_type'].set_body(*fields)

        # 3) Pré-declarar a assinatura de cada função global.
        for stmt in function_nodes:
            self.user_functions[stmt.name] = self._declare_function_signature(stmt)

        # 4) Pré-declarar o construtor e os métodos de cada classe.
        for stmt in class_nodes:
            info = self.classes[stmt.name]
            if stmt.constructor:
                info['constructor'] = self._declare_constructor_signature(stmt.constructor, stmt.name)
            for m in stmt.methods:
                info['methods'][m.name] = self._declare_method_signature(m, stmt.name)

    def _param_llvm_types(self, params):
        """Converte a lista de parâmetros da AST (tipo, nome[, dimensão]) em tipos LLVM.

        Vetores são passados por referência (um ponteiro para o vetor), então
        seu tipo LLVM de parâmetro é sempre um ponteiro, mesmo que a variável
        local correspondente, dentro da função, seja um vetor "de verdade".
        """
        types = []
        for p in params:
            p_type = p[0]
            p_dim = p[2] if len(p) > 2 else None
            t = self.get_llvm_type(p_type, p_dim)
            if p_dim is not None:
                t = ir.PointerType(t)
            types.append(t)
        return types

    def _declare_function_signature(self, node):
        ret_type = self.get_llvm_type(node.return_type, node.return_dimension)
        param_types = self._param_llvm_types(node.params)
        fnty = ir.FunctionType(ret_type, param_types)
        # "main" do JSS não pode se chamar "main" no LLVM: esse nome é
        # reservado para o verdadeiro ponto de entrada do executável nativo,
        # construído em `generate()`.
        llvm_name = "_jss_main" if node.name == 'main' else node.name
        return ir.Function(self.module, fnty, name=llvm_name)

    def _declare_method_signature(self, node, class_name):
        ret_type = self.get_llvm_type(node.return_type, node.return_dimension)
        this_ptr_ty = ir.PointerType(self.classes[class_name]['struct_type'])
        param_types = [this_ptr_ty] + self._param_llvm_types(node.params)
        fnty = ir.FunctionType(ret_type, param_types)
        return ir.Function(self.module, fnty, name=f"{class_name}_{node.name}")

    def _declare_constructor_signature(self, node, class_name):
        this_ptr_ty = ir.PointerType(self.classes[class_name]['struct_type'])
        param_types = [this_ptr_ty] + self._param_llvm_types(node.params)
        fnty = ir.FunctionType(void, param_types)  # construtores não retornam valor
        return ir.Function(self.module, fnty, name=f"{class_name}_constructor")

    # ------------------------------------------------------------------
    # Tipos e valores auxiliares
    # ------------------------------------------------------------------

    def get_llvm_type(self, jss_type, dimension=None):
        """Traduz um tipo JSS (e sua dimensão de vetor, se houver) para um tipo `llvmlite.ir`."""
        if jss_type == 'int':
            base = i32
        elif jss_type == 'real':
            base = f64
        elif jss_type == 'bool':
            base = i1
        elif jss_type == 'str':
            base = i8p
        elif jss_type == 'void':
            base = void
        else:
            # Um tipo que não é primitivo só pode ser o nome de uma classe;
            # objetos do JSS são sempre manipulados por referência (ponteiro).
            base = ir.PointerType(self.classes[jss_type]['struct_type'])

        if dimension is not None:
            dims = dimension if isinstance(dimension, list) else [dimension]
            t = base
            for d in reversed(dims):
                t = ir.ArrayType(t, d)
            return t
        return base

    def get_default_value(self, llvm_type):
        """Valor "zerado" de um tipo LLVM: 0 para números, false para bool, ponteiro
        nulo para ponteiros e "zeroinitializer" (todos os elementos zerados) para
        vetores - tudo isso de uma vez, porque `ir.Constant(tipo, None)` já sabe
        gerar a constante zero correta para qualquer tipo LLVM.
        """
        return ir.Constant(llvm_type, None)

    def get_or_create_string_constant(self, s):
        """Devolve um ponteiro i8* constante para a string literal `s`.

        Strings literais idênticas compartilham a mesma constante global
        (cache em `self.strings`), assim como duas aparições do mesmo texto
        `"erro"` no código-fonte não geram duas cópias na seção de dados do
        executável final.
        """
        if s in self.strings:
            return self.strings[s]

        data = bytearray(s.encode('utf8') + b'\x00')
        arr_ty = ir.ArrayType(ir.IntType(8), len(data))
        gv = ir.GlobalVariable(self.module, arr_ty, name=f"str.{len(self.strings)}")
        gv.global_constant = True
        gv.linkage = 'private'
        gv.unnamed_addr = True
        gv.initializer = ir.Constant(arr_ty, data)

        ptr = gv.gep([_zero32(), _zero32()])
        self.strings[s] = ptr
        return ptr

    # ------------------------------------------------------------------
    # Ponto de entrada da geração de código
    # ------------------------------------------------------------------

    def generate(self, ast):
        """Compila a AST inteira e devolve o `llvmlite.ir.Module` resultante.

        A função `@main` do executável (a que o CRT do sistema chama para
        iniciar o programa) é criada aqui: qualquer instrução de nível
        superior do arquivo `.jss` (por exemplo, a inicialização de uma
        variável global) é compilada diretamente dentro dela. No final, se o
        usuário declarou sua própria `function void main() { ... }` no JSS,
        chamamos essa função (renomeada para `_jss_main`, ver
        `_declare_function_signature`) antes de retornar.
        """
        self._preprocess_declarations(ast)

        # O programa JSS inteiro é emitido dentro da `main` nativa do
        # executável; o `main` do usuário, se existir, é chamado daqui.
        main_fnty = ir.FunctionType(i32, [])
        self.current_function = ir.Function(self.module, main_fnty, name="main")
        self.builder = ir.IRBuilder(self.current_function.append_basic_block("entry"))
        self.current_function_ret_type = i32

        self.visit(ast)

        if 'main' in self.user_functions:
            self.builder.call(self.user_functions['main'], [])

        self.builder.ret(ir.Constant(i32, 0))

        return self.module

    def visit_ProgramNode(self, node):
        # O programa raiz é só a sequência de instruções globais na ordem do
        # fonte; cada uma delas é traduzida e emitida uma após a outra.
        for stmt in node.statements:
            self.visit(stmt)

    def visit(self, node):
        if node is None:
            return None
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name)
        return visitor(node)

    # ------------------------------------------------------------------
    # Visitantes de expressão (devolvem sempre um par (valor_llvm, tipo_llvm))
    # ------------------------------------------------------------------

    def visit_NumberNode(self, node):
        # Literais numéricos viram constantes LLVM imediatas do tipo correto.
        if node.is_real:
            return ir.Constant(f64, float(node.value)), f64
        return ir.Constant(i32, int(node.value)), i32

    def visit_StringNode(self, node):
        # String literal vira ponteiro para uma constante global compartilhada.
        return self.get_or_create_string_constant(node.value), i8p

    def visit_BooleanNode(self, node):
        # Booleanos são representados como `i1` no LLVM.
        return ir.Constant(i1, 1 if node.value else 0), i1

    def visit_NullNode(self, node):
        # `null` no JSS vira ponteiro nulo genérico no LLVM.
        return ir.Constant(i8p, None), i8p

    def visit_IdentifierNode(self, node):
        # Um identificador vira a leitura do valor armazenado no endereço
        # encontrado no escopo atual.
        ptr, llvm_type, jss_type, dimension = self.get_target_pointer(node)
        if dimension is not None:
            if isinstance(llvm_type, ir.PointerType):
                # Vetor recebido como parâmetro (passado por referência): o que está
                # guardado em `ptr` é um ponteiro-para-ponteiro, então precisamos de
                # um `load` para obter o ponteiro real do vetor.
                return self.builder.load(ptr), llvm_type
            # Vetor local/global: seu próprio endereço já É o ponteiro do vetor
            # (vetores "decaem" para ponteiro ao serem usados como valor).
            return ptr, ir.PointerType(llvm_type)
        return self.builder.load(ptr), llvm_type

    def get_target_pointer(self, node):
        """Calcula o *endereço* (não o valor) de um alvo atribuível: uma variável,
        um elemento de vetor (`v[i]`) ou um atributo de objeto (`obj.attr`).

        Devolve sempre `(ponteiro, tipo_llvm_do_conteudo, tipo_jss, dimensao)`.
        É o método central usado tanto para *ler* quanto para *escrever*
        (atribuição, `++`/`--`, `input(...)`) nesses três tipos de alvo.
        """
        if isinstance(node, IdentifierNode):
            res = self.current_scope.lookup(node.name)
            if res is None:
                # A análise semântica já deveria ter barrado identificadores não
                # declarados antes de chegarmos aqui - se isso disparar, é sinal
                # de um bug no gerador de código, não um erro do programa JSS.
                raise ValueError(f"Identificador '{node.name}' nao encontrado no escopo.")
            return res

        elif isinstance(node, ArrayAccessNode):
            # Para acessar um elemento, primeiro obtemos o vetor e depois
            # calculamos o endereço do índice com `getelementptr`.
            array_ptr, array_type = self.visit(node.array_expr)
            index_val, _ = self.visit(node.index_expr)
            # `array_type` é sempre um ponteiro para vetor (ex.: [3 x i32]* ou,
            # em vetores multidimensionais, [3 x [4 x i32]]*). O elemento é o
            # tipo interno do vetor apontado - o próprio sistema de tipos da
            # llvmlite responde isso, sem precisar recortar texto manualmente.
            elem_type = array_type.pointee.element
            ptr = self.builder.gep(array_ptr, [_zero32(), index_val], inbounds=True)
            return ptr, elem_type, "array_elem", None

        elif isinstance(node, AttributeAccessNode):
            # Atributos de classe são campos de `struct` no LLVM; o índice vem
            # da ordem em que os atributos foram declarados.
            obj_ptr, obj_type = self.visit(node.object_expr)
            class_name = obj_type.pointee.name.split(".", 1)[1]
            class_info = self.classes[class_name]

            attr_name = node.attribute_name
            attr_idx = class_info['attrs'].index(attr_name)
            attr_jss_type = class_info['attr_types'][attr_name]
            attr_dim = class_info['attr_dims'][attr_name]
            attr_llvm_type = self.get_llvm_type(attr_jss_type, attr_dim)

            ptr = self.builder.gep(obj_ptr, [_zero32(), ir.Constant(i32, attr_idx)], inbounds=True)
            return ptr, attr_llvm_type, attr_jss_type, attr_dim

        raise ValueError(f"No de destino invalido: {type(node).__name__}")

    def visit_ArrayAccessNode(self, node):
        # Se o acesso já aponta para um subvetor, devolvemos o endereço dele;
        # caso contrário, carregamos o valor do elemento.
        ptr, llvm_type, _, dimension = self.get_target_pointer(node)
        if dimension is not None or isinstance(llvm_type, ir.ArrayType):
            # O próprio elemento acessado ainda é um vetor (acesso parcial em uma
            # matriz, ex.: `m[0]` de um `int[2][3]`) - devolvemos seu endereço,
            # não um valor carregado, para permitir indexação encadeada `m[0][1]`.
            return ptr, ir.PointerType(llvm_type)
        return self.builder.load(ptr), llvm_type

    def visit_AttributeAccessNode(self, node):
        # Acesso a atributo funciona igual a um acesso a campo de struct.
        ptr, llvm_type, _, dimension = self.get_target_pointer(node)
        if dimension is not None or isinstance(llvm_type, ir.ArrayType):
            return ptr, ir.PointerType(llvm_type)
        return self.builder.load(ptr), llvm_type

    def visit_BinaryOpNode(self, node):
        # Operadores binários cobrem aritmética, comparação, concatenação e
        # curto-circuito lógico.
        op = node.op

        # `&&` e `||` têm avaliação de curto-circuito: o lado direito só pode
        # ser avaliado condicionalmente, então precisam de blocos e `phi`
        # próprios em vez de simplesmente calcular os dois lados e combinar.
        if op == '&&':
            return self._generate_short_circuit_and(node)
        elif op == '||':
            return self._generate_short_circuit_or(node)

        # Operadores normais avaliam os dois lados antes de aplicar coerção ou
        # escolher a instrução LLVM adequada.
        l_val, l_type = self.visit(node.left)
        r_val, r_type = self.visit(node.right)

        # Coerção implícita int -> real quando os dois lados não combinam
        if l_type == f64 and r_type == i32:
            r_val, r_type = self.builder.sitofp(r_val, f64), f64
        elif l_type == i32 and r_type == f64:
            l_val, l_type = self.builder.sitofp(l_val, f64), f64

        # Concatenação de string: `+` onde pelo menos um dos lados é `str`
        if op == '+' and (l_type == i8p or r_type == i8p):
            # `+` também faz concatenação quando um dos operandos é string.
            if l_type != i8p:
                l_val, l_type = self._cast_value_to_string(l_val, l_type)
            if r_type != i8p:
                r_val, r_type = self._cast_value_to_string(r_val, r_type)
            return self.builder.call(self.runtime['str_concat'], [l_val, r_val]), i8p

        # Operações aritméticas
        if l_type == f64:
            arith = {'+': self.builder.fadd, '-': self.builder.fsub,
                     '*': self.builder.fmul, '/': self.builder.fdiv}
            if op in arith:
                return arith[op](l_val, r_val), f64
        elif l_type == i32:
            if op == '**':
                return self.builder.call(self.runtime['ipow'], [l_val, r_val]), i32
            arith = {'+': self.builder.add, '-': self.builder.sub, '*': self.builder.mul,
                     '/': self.builder.sdiv, '%': self.builder.srem}
            if op in arith:
                return arith[op](l_val, r_val), i32

        # Comparações relacionais. Os operadores do JSS ('==', '<', '>=', ...)
        # já são exatamente os símbolos que `icmp_signed`/`fcmp_ordered` esperam,
        # então não precisamos de nenhuma tabela de tradução para mnemônicos LLVM.
        if l_type == f64:
            return self.builder.fcmp_ordered(op, l_val, r_val), i1
        elif l_type in (i32, i1):
            return self.builder.icmp_signed(op, l_val, r_val), i1
        elif isinstance(l_type, ir.PointerType) or isinstance(r_type, ir.PointerType):
            # Comparação de ponteiros (objetos, vetores por referência, strings):
            # normalizamos os dois lados para i8* antes de comparar, já que o
            # LLVM não permite `icmp` entre dois tipos de ponteiro diferentes.
            l_ptr = l_val if l_type == i8p else self.builder.bitcast(l_val, i8p)
            r_ptr = r_val if r_type == i8p else self.builder.bitcast(r_val, i8p)
            return self.builder.icmp_unsigned(op, l_ptr, r_ptr), i1

        return ir.Constant(i32, 0), void

    def _cast_value_to_string(self, val, from_type):
        if from_type == i32:
            return self.builder.call(self.runtime['int_to_str'], [val]), i8p
        elif from_type == f64:
            return self.builder.call(self.runtime['real_to_str'], [val]), i8p
        elif from_type == i1:
            return self.builder.call(self.runtime['bool_to_str'], [val]), i8p
        return val, from_type

    def _generate_short_circuit_and(self, node):
        """`esquerda && direita`: só avalia `direita` se `esquerda` for verdadeira.

        Gera três blocos: o bloco atual (que decide se pula ou não para a
        direita), um bloco `and.rhs` que avalia e só é alcançado quando
        `esquerda` é verdadeira, e um bloco `and.end` onde um `phi` junta o
        resultado - `false` se viemos direto do bloco atual, ou o valor de
        `direita` se passamos por `and.rhs`.
        """
        l_val, _ = self.visit(node.left)
        entry_block = self.builder.block

        rhs_block = self.current_function.append_basic_block("and.rhs")
        end_block = self.current_function.append_basic_block("and.end")
        self.builder.cbranch(l_val, rhs_block, end_block)

        self.builder = ir.IRBuilder(rhs_block)
        r_val, _ = self.visit(node.right)
        rhs_final_block = self.builder.block
        self.builder.branch(end_block)

        self.builder = ir.IRBuilder(end_block)
        phi = self.builder.phi(i1, name="and.result")
        phi.add_incoming(ir.Constant(i1, 0), entry_block)
        phi.add_incoming(r_val, rhs_final_block)
        return phi, i1

    def _generate_short_circuit_or(self, node):
        """`esquerda || direita`: só avalia `direita` se `esquerda` for falsa (espelho de `_generate_short_circuit_and`)."""
        l_val, _ = self.visit(node.left)
        entry_block = self.builder.block

        rhs_block = self.current_function.append_basic_block("or.rhs")
        end_block = self.current_function.append_basic_block("or.end")
        self.builder.cbranch(l_val, end_block, rhs_block)

        self.builder = ir.IRBuilder(rhs_block)
        r_val, _ = self.visit(node.right)
        rhs_final_block = self.builder.block
        self.builder.branch(end_block)

        self.builder = ir.IRBuilder(end_block)
        phi = self.builder.phi(i1, name="or.result")
        phi.add_incoming(ir.Constant(i1, 1), entry_block)
        phi.add_incoming(r_val, rhs_final_block)
        return phi, i1

    def visit_UnaryOpNode(self, node):
        # Operadores unários tratam prefixo, negação lógica e sinais.
        op = node.op

        if op in ('++', '--'):
            # Incremento/decremento prefixado: um alvo atribuível (L-value)
            ptr, llvm_type, _, _ = self.get_target_pointer(node.expression)
            old_val = self.builder.load(ptr)
            if llvm_type == i32:
                step = ir.Constant(i32, 1)
                new_val = self.builder.add(old_val, step) if op == '++' else self.builder.sub(old_val, step)
            else:  # real (double)
                step = ir.Constant(f64, 1.0)
                new_val = self.builder.fadd(old_val, step) if op == '++' else self.builder.fsub(old_val, step)
            self.builder.store(new_val, ptr)
            return new_val, llvm_type

        val, v_type = self.visit(node.expression)

        if op == '!':
            return self.builder.xor(val, ir.Constant(i1, 1)), i1
        elif op == '+':
            return val, v_type
        elif op == '-':
            if v_type == f64:
                return self.builder.fneg(val), v_type
            return self.builder.sub(ir.Constant(i32, 0), val), v_type

        return ir.Constant(i32, 0), void

    def visit_CastNode(self, node):
        # Casting explícito converte o valor para o tipo-alvo pedido na AST.
        val, from_type = self.visit(node.expression)
        target = node.target_type

        if target == 'int':
            if from_type == f64:
                return self.builder.fptosi(val, i32), i32
            elif from_type == i1:
                return self.builder.zext(val, i32), i32
            return val, i32

        elif target == 'real':
            if from_type == i32:
                return self.builder.sitofp(val, f64), f64
            elif from_type == i1:
                return self.builder.uitofp(val, f64), f64
            return val, f64

        elif target == 'bool':
            if from_type == i32:
                return self.builder.icmp_signed('!=', val, ir.Constant(i32, 0)), i1
            elif from_type == f64:
                return self.builder.fcmp_ordered('!=', val, ir.Constant(f64, 0.0)), i1
            return val, i1

        elif target == 'str':
            return self._cast_value_to_string(val, from_type)

        return ir.Constant(i32, 0), void

    def visit_NewObjectNode(self, node):
        # `new` aloca memória para a struct da classe e chama o construtor.
        class_name = node.class_name
        struct_ty = self.classes[class_name]['struct_type']
        struct_ptr_ty = ir.PointerType(struct_ty)

        # Tamanho (em bytes) de um `struct.ClassName`, calculado em tempo de
        # compilação: "até onde apontaria um struct.ClassName* que começasse em
        # NULL e avançasse 1 posição" é, por definição, o tamanho de 1 struct -
        # já considerando o padding/alinhamento que o LLVM aplicar aos campos.
        size_const = ir.Constant(struct_ptr_ty, None).gep([ir.Constant(i32, 1)]).ptrtoint(i64)

        raw_mem = self.builder.call(self.runtime['malloc'], [size_const])
        obj_ptr = self.builder.bitcast(raw_mem, struct_ptr_ty)

        constructor_fn = self.classes[class_name]['constructor']
        if constructor_fn is not None:
            args = self._prepare_call_args(constructor_fn, node.arguments, leading_args=[obj_ptr])
            self.builder.call(constructor_fn, args)

        return obj_ptr, struct_ptr_ty

    def _prepare_call_args(self, callee_fn, arg_nodes, leading_args=None):
        """Avalia os argumentos de uma chamada e ajusta cada um ao tipo exato
        esperado pelo parâmetro formal correspondente (a assinatura real de
        `callee_fn`, já conhecida porque toda função/método foi pré-declarada
        em `_preprocess_declarations`). Dois ajustes são necessários:
        - `int` passado onde se espera `real` precisa de conversão (`sitofp`);
        - `null` passado onde se espera uma referência de objeto precisa virar
          um ponteiro nulo *do tipo certo* (o literal `null` do JSS sempre nasce
          com tipo genérico i8*, mas cada classe tem seu próprio tipo de ponteiro).
        """
        args = list(leading_args) if leading_args else []
        param_types = callee_fn.function_type.args
        offset = len(args)
        for i, arg_node in enumerate(arg_nodes):
            val, v_type = self.visit(arg_node)
            expected = param_types[offset + i]
            if expected == f64 and v_type == i32:
                val = self.builder.sitofp(val, f64)
            elif isinstance(expected, ir.PointerType) and v_type != expected:
                val = ir.Constant(expected, None)
            args.append(val)
        return args

    def visit_CallNode(self, node):
        # Chamada pode ser função global ou método de objeto; ambas usam a
        # assinatura já pré-declarada antes da geração do corpo.
        if isinstance(node.callee, AttributeAccessNode):
            # Chamada de método: obj.metodo(args)
            obj_ptr, obj_type = self.visit(node.callee.object_expr)
            class_name = obj_type.pointee.name.split(".", 1)[1]
            method_name = node.callee.attribute_name
            fn = self.classes[class_name]['methods'][method_name]
        else:
            # Chamada de função global: foo(args)
            fn = self.user_functions[node.callee.name]

        leading = [obj_ptr] if isinstance(node.callee, AttributeAccessNode) else None
        args = self._prepare_call_args(fn, node.arguments, leading_args=leading)
        result = self.builder.call(fn, args)

        if fn.function_type.return_type == void:
            # Uma chamada void usada como expressão (ex.: dentro de outra
            # expressão) não tem valor real; devolvemos um 0 inofensivo.
            return ir.Constant(i32, 0), void
        return result, fn.function_type.return_type

    def visit_ArrayLiteralNode(self, node):
        # Literais de vetor não viram uma instrução sozinhos; retornam os
        # elementos avaliados para quem for fazer a inicialização.
        # Literais de vetor só aparecem em inicializações; devolvemos a lista de
        # valores avaliados para quem estiver processando a declaração/atribuição.
        return [self.visit(expr) for expr in node.expressions], "literal_array"

    # ------------------------------------------------------------------
    # Visitantes de declaração e controle de fluxo
    # ------------------------------------------------------------------

    def visit_VarDeclarationNode(self, node):
        # Declaração cria armazenamento e, se houver inicializador, grava o
        # valor inicial no endereço recém-criado.
        var_type = node.var_type
        dimension = node.dimension
        llvm_type = self.get_llvm_type(var_type, dimension)

        if self.current_scope.parent is None:
            # Variável global: vive na seção de dados do executável, não na pilha.
            # O `initializer` já cuida de zerar (int 0, real 0.0, vetor inteiro
            # zerado, ponteiro nulo, ...) mesmo sem nenhuma instrução em tempo de
            # execução - é por isso que não existe mais um laço manual "zerar
            # cada posição do vetor" como método separado.
            gv = ir.GlobalVariable(self.module, llvm_type, name=f"g_{node.name}")
            gv.initializer = self.get_default_value(llvm_type)
            self.current_scope.define(node.name, gv, llvm_type, var_type, dimension)
            target_ptr = gv
        else:
            target_ptr = self.builder.alloca(llvm_type, name=f"{node.name}.addr")
            self.current_scope.define(node.name, target_ptr, llvm_type, var_type, dimension)
            if not node.value:
                # Diferente de uma global, `alloca` não zera a memória sozinho -
                # por isso, sem inicializador explícito, gravamos o valor padrão
                # manualmente (um único `store`, mesmo para vetores inteiros).
                self.builder.store(self.get_default_value(llvm_type), target_ptr)

        if node.value:
            if isinstance(node.value, ArrayLiteralNode):
                evaluated, _ = self.visit(node.value)
                for idx, (elem_val, _) in enumerate(evaluated):
                    ptr = self.builder.gep(target_ptr, [_zero32(), ir.Constant(i32, idx)], inbounds=True)
                    self.builder.store(elem_val, ptr)
            else:
                val, v_type = self.visit(node.value)
                if llvm_type == f64 and v_type == i32:
                    val = self.builder.sitofp(val, f64)
                self.builder.store(val, target_ptr)

    def visit_AssignmentNode(self, node):
        # Atribuições simples e compostas reaproveitam a mesma lógica de
        # localizar o alvo e atualizar o valor armazenado.
        op = node.op

        if op in ('&&=', '||='):
            # `x &&= y` equivale a `x = x && y` (idem para `||=`): mesmo padrão de
            # curto-circuito com blocos e `phi` de `_generate_short_circuit_and/or`,
            # só que o resultado também é gravado de volta no alvo.
            ptr, llvm_type, _, _ = self.get_target_pointer(node.target)
            old_val = self.builder.load(ptr)

            entry_block = self.builder.block
            rhs_block = self.current_function.append_basic_block("assign.rhs")
            end_block = self.current_function.append_basic_block("assign.end")

            if op == '&&=':
                self.builder.cbranch(old_val, rhs_block, end_block)
            else:
                self.builder.cbranch(old_val, end_block, rhs_block)

            self.builder = ir.IRBuilder(rhs_block)
            r_val, _ = self.visit(node.value)
            rhs_final_block = self.builder.block
            self.builder.branch(end_block)

            self.builder = ir.IRBuilder(end_block)
            phi = self.builder.phi(i1, name="assign.result")
            phi.add_incoming(ir.Constant(i1, 1 if op == '||=' else 0), entry_block)
            phi.add_incoming(r_val, rhs_final_block)

            self.builder.store(phi, ptr)
            return phi, i1

        ptr, llvm_type, _, _ = self.get_target_pointer(node.target)

        if op == '=':
            # Atribuição simples só precisa ajustar o tipo quando o JSS permite
            # coerção implícita, como `int -> real` ou `null` para objetos.
            val, v_type = self.visit(node.value)
            if llvm_type == f64 and v_type == i32:
                val = self.builder.sitofp(val, f64)
            elif isinstance(llvm_type, ir.PointerType) and v_type != llvm_type:
                # Cobre `objeto = null;`: o literal `null` nasce com tipo i8*
                # genérico, mas o alvo espera um ponteiro do tipo da classe certa.
                val = ir.Constant(llvm_type, None)
            self.builder.store(val, ptr)
            return val, llvm_type

        # Atribuições compostas: +=, -=, *=, /=, %=
        arith_op = op[:-1]
        old_val = self.builder.load(ptr)
        val_rhs, r_type = self.visit(node.value)
        if llvm_type == f64 and r_type == i32:
            val_rhs = self.builder.sitofp(val_rhs, f64)

        if llvm_type == f64:
            fn = {'+': self.builder.fadd, '-': self.builder.fsub,
                  '*': self.builder.fmul, '/': self.builder.fdiv}[arith_op]
        else:
            fn = {'+': self.builder.add, '-': self.builder.sub, '*': self.builder.mul,
                  '/': self.builder.sdiv, '%': self.builder.srem}[arith_op]

        result = fn(old_val, val_rhs)
        self.builder.store(result, ptr)
        return result, llvm_type

    def visit_BlockNode(self, node):
        # Cada bloco abre um novo escopo léxico e fecha quando o fluxo termina.
        # Cada bloco abre um novo escopo léxico.
        old_scope = self.current_scope
        self.current_scope = Scope(parent=old_scope)
        for stmt in node.statements:
            self.visit(stmt)
            if self.builder.block.is_terminated:
                # `return`/`break` já encerrou o bloco atual (ele agora termina
                # com `ret`/`br`); qualquer instrução do JSS depois disso seria
                # código morto e inserir mais instruções aqui produziria IR
                # inválido (um bloco não pode ter nada depois do terminador).
                break
        self.current_scope = old_scope

    def visit_IfNode(self, node):
        # O `if` vira desvio condicional com blocos then/else/merge.
        # O `if` vira blocos explícitos de then/else/merge.
        cond_val, _ = self.visit(node.condition)

        then_block = self.current_function.append_basic_block("if.then")
        else_block = self.current_function.append_basic_block("if.else") if node.else_branch else None
        merge_block = self.current_function.append_basic_block("if.merge")

        self.builder.cbranch(cond_val, then_block, else_block if else_block else merge_block)

        self.builder = ir.IRBuilder(then_block)
        self.visit(node.then_branch)
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)

        if else_block:
            self.builder = ir.IRBuilder(else_block)
            self.visit(node.else_branch)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_block)

        self.builder = ir.IRBuilder(merge_block)

    def visit_WhileNode(self, node):
        # O `while` é montado como três blocos: condição, corpo e saída.
        # O `while` não vira uma instrução única no LLVM.
        # Ele é quebrado em blocos básicos: um para testar a condição,
        # outro para executar o corpo e um terceiro para sair do laço.
        cond_block = self.current_function.append_basic_block("while.cond")
        body_block = self.current_function.append_basic_block("while.body")
        end_block = self.current_function.append_basic_block("while.end")

        # O fluxo atual desvia primeiro para o bloco que avalia a condição.
        self.builder.branch(cond_block)

        # No bloco da condição, o compilador traduz a expressão do `while`
        # e cria um salto condicional: verdadeiro entra no corpo, falso sai.
        self.builder = ir.IRBuilder(cond_block)
        cond_val, _ = self.visit(node.condition)
        self.builder.cbranch(cond_val, body_block, end_block)

        # No corpo, empilhamos o bloco de saída para que `break` saiba para
        # onde saltar caso apareça dentro do laço.
        self.builder = ir.IRBuilder(body_block)
        self.loop_stack.append(end_block)
        self.visit(node.body)
        self.loop_stack.pop()

        # Se o corpo não terminou com `return` ou `break`, o fluxo volta para
        # reavaliar a condição e repetir o laço.
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)

        # Depois do laço, o builder continua emitindo código a partir daqui.
        self.builder = ir.IRBuilder(end_block)

    def visit_ForNode(self, node):
        # O `for` é desdobrado em init, teste, corpo, passo e retorno ao teste.
        # `for` é decomposto em init -> condição -> corpo -> passo -> repetição.
        cond_block = self.current_function.append_basic_block("for.cond")
        body_block = self.current_function.append_basic_block("for.body")
        step_block = self.current_function.append_basic_block("for.step")
        end_block = self.current_function.append_basic_block("for.end")

        old_scope = self.current_scope
        self.current_scope = Scope(parent=old_scope)

        if node.init:
            self.visit(node.init)
        self.builder.branch(cond_block)

        self.builder = ir.IRBuilder(cond_block)
        if node.condition:
            cond_val, _ = self.visit(node.condition)
            self.builder.cbranch(cond_val, body_block, end_block)
        else:
            self.builder.branch(body_block)

        self.builder = ir.IRBuilder(body_block)
        self.loop_stack.append(end_block)
        self.visit(node.body)
        self.loop_stack.pop()
        if not self.builder.block.is_terminated:
            self.builder.branch(step_block)

        self.builder = ir.IRBuilder(step_block)
        if node.update:
            self.visit(node.update)
        self.builder.branch(cond_block)

        self.builder = ir.IRBuilder(end_block)
        self.current_scope = old_scope

    def visit_BreakNode(self, node):
        # `break` apenas salta para o final do laço mais interno ativo.
        if self.loop_stack:
            self.builder.branch(self.loop_stack[-1])

    def _build_function_body(self, fn, jss_params, body, ret_llvm_type, this_class_name=None):
        """Preenche o corpo de uma função/método/construtor já pré-declarado.

        Compartilhada pelas três formas de "função" que o JSS tem (função
        global, método e construtor) porque a receita é sempre a mesma: abrir
        um escopo novo, alocar uma cópia local de cada parâmetro (e do `this`
        implícito, quando existe), compilar o corpo e, no final, garantir que
        o último bloco termine com um `ret`/`unreachable` válido.
        """
        old_builder = self.builder
        old_scope = self.current_scope
        old_function = self.current_function
        old_ret_type = self.current_function_ret_type

        self.current_function = fn
        self.current_scope = Scope(parent=old_scope)
        self.current_function_ret_type = ret_llvm_type
        self.builder = ir.IRBuilder(fn.append_basic_block("entry"))

        arg_index = 0
        if this_class_name is not None:
            this_arg = fn.args[0]
            this_arg.name = "this"
            this_addr = self.builder.alloca(this_arg.type, name="this.addr")
            self.builder.store(this_arg, this_addr)
            self.current_scope.define("this", this_addr, this_arg.type, this_class_name, None)
            arg_index = 1

        for p, arg in zip(jss_params, fn.args[arg_index:]):
            p_type, p_name = p[0], p[1]
            p_dim = p[2] if len(p) > 2 else None
            arg.name = f"_in_{p_name}"
            addr = self.builder.alloca(arg.type, name=f"{p_name}.addr")
            self.builder.store(arg, addr)
            self.current_scope.define(p_name, addr, arg.type, p_type, p_dim)

        self.visit(body)

        if not self.builder.block.is_terminated:
            if ret_llvm_type == void:
                self.builder.ret_void()
            else:
                # Só alcançável se restar um bloco vazio "pendurado" (ex.: o
                # merge de um if/else onde os dois ramos já deram `return`) -
                # a análise semântica já garante que todo caminho de uma função
                # não-void termina em `return`, então este bloco é inatingível.
                self.builder.unreachable()

        self.builder = old_builder
        self.current_scope = old_scope
        self.current_function = old_function
        self.current_function_ret_type = old_ret_type

    def visit_FunctionNode(self, node):
        # Função global vira um corpo LLVM separado, usando a assinatura já
        # pré-declarada no pré-processamento.
        fn = self.user_functions[node.name]
        ret_llvm_type = self.get_llvm_type(node.return_type, node.return_dimension)
        self._build_function_body(fn, node.params, node.body, ret_llvm_type)

    def visit_ReturnNode(self, node):
        # `return` encerra o bloco atual com o valor convertido para o tipo da
        # função, quando necessário.
        if node.expression:
            val, v_type = self.visit(node.expression)
            if self.current_function_ret_type == f64 and v_type == i32:
                val = self.builder.sitofp(val, f64)
            elif isinstance(self.current_function_ret_type, ir.PointerType) and v_type != self.current_function_ret_type:
                val = ir.Constant(self.current_function_ret_type, None)  # `return null;`
            self.builder.ret(val)
        else:
            self.builder.ret_void()

    def visit_ClassDeclarationNode(self, node):
        # Classe já teve tipo e assinaturas declarados; aqui só compilamos os
        # corpos do construtor e dos métodos.
        # Os tipos de struct e as assinaturas de construtor/métodos já foram
        # pré-declarados em `_preprocess_declarations`; aqui só compilamos os corpos.
        class_name = node.name

        if node.constructor:
            self.visit(node.constructor)

        for m in node.methods:
            fn = self.classes[class_name]['methods'][m.name]
            ret_llvm_type = self.get_llvm_type(m.return_type, m.return_dimension)
            self._build_function_body(fn, m.params, m.body, ret_llvm_type, this_class_name=class_name)

    def visit_ClassConstructorNode(self, node):
        # Construtor é compilado como uma função void que recebe `this`.
        fn = self.classes[node.class_name]['constructor']
        self._build_function_body(fn, node.params, node.body, void, this_class_name=node.class_name)

    def visit_ConsoleLogNode(self, node):
        # `console.log` é expandido em chamadas do runtime para cada argumento.
        # `console.log` vira uma sequência de chamadas do runtime, uma por
        # expressão, com espaço entre elas e newline no final.
        for idx, expr in enumerate(node.expressions):
            val, v_type = self.visit(expr)
            if idx > 0:
                self.builder.call(self.runtime['print_space'], [])
            if v_type == i32:
                self.builder.call(self.runtime['print_int'], [val])
            elif v_type == f64:
                self.builder.call(self.runtime['print_real'], [val])
            elif v_type == i8p:
                self.builder.call(self.runtime['print_str'], [val])
            elif v_type == i1:
                self.builder.call(self.runtime['print_bool'], [val])
        self.builder.call(self.runtime['print_newline'], [])

    def visit_InputNode(self, node):
        # `input` lê do runtime e grava o resultado diretamente nos alvos.
        for target in node.targets:
            ptr, llvm_type, _, _ = self.get_target_pointer(target)
            if llvm_type == i32:
                val = self.builder.call(self.runtime['read_int'], [])
            elif llvm_type == f64:
                val = self.builder.call(self.runtime['read_real'], [])
            elif llvm_type == i8p:
                val = self.builder.call(self.runtime['read_str'], [])
            else:
                continue
            self.builder.store(val, ptr)
