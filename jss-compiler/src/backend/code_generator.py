"""Gerador de código LLVM IR para a linguagem JSS.

Responsável por percorrer a AST e traduzir suas estruturas para o formato textual .ll.
"""

from frontend.ast_nodes import (
    ProgramNode, VarDeclarationNode, AssignmentNode, BlockNode,
    IfNode, WhileNode, ForNode, BreakNode, FunctionNode, ReturnNode,
    CallNode, BinaryOpNode, UnaryOpNode, ArrayAccessNode, ArrayLiteralNode,
    ClassDeclarationNode, ClassConstructorNode, AttributeAccessNode,
    NewObjectNode, ConsoleLogNode, InputNode, CastNode, NumberNode,
    StringNode, BooleanNode, NullNode, IdentifierNode
)

class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.vars = {}  # nome_jss -> (llvm_ptr, llvm_type, jss_type, dimension)

    def define(self, name, llvm_ptr, llvm_type, jss_type, dimension=None):
        self.vars[name] = (llvm_ptr, llvm_type, jss_type, dimension)

    def lookup(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.lookup(name)
        return None


class CodeGenerator:
    def __init__(self):
        self.reg_count = 0
        self.label_count = 0
        self.string_count = 0
        self.strings = {}
        
        # Estrutura de partições do arquivo de saída .ll
        self.runtime_decls = []
        self.struct_decls = []
        self.global_decls = []
        self.const_decls = []
        self.func_decls = []
        self.main_code = []
        
        self.current_buffer = self.main_code
        self.current_scope = Scope()
        self.loop_stack = []
        self.block_terminated = False
        
        # Mapeamento de classes: nome -> { 'attrs': [nomes], 'attr_types': {nome: jss_type}, 'attr_dims': {nome: dim} }
        self.classes = {}
        
        # Mapeamento de assinaturas de funções globais: nome -> (jss_return_type, return_dim, [jss_param_types])
        self.functions_sig = {}
        
        self._setup_runtime_declarations()

    def _setup_runtime_declarations(self):
        self.runtime_decls.extend([
            "declare void @print_int(i32)",
            "declare void @print_real(double)",
            "declare void @print_str(i8*)",
            "declare void @print_bool(i1)",
            "declare void @print_space()",
            "declare void @print_newline()",
            "declare i32 @read_int()",
            "declare double @read_real()",
            "declare i8* @read_str()",
            "declare i8* @str_concat(i8*, i8*)",
            "declare i8* @int_to_str(i32)",
            "declare i8* @real_to_str(double)",
            "declare i8* @bool_to_str(i1)",
            "declare i32 @ipow(i32, i32)",
            "declare i8* @malloc(i64)"
        ])

    def emit(self, instruction):
        if not self.block_terminated:
            self.current_buffer.append(instruction)

    def new_reg(self):
        self.reg_count += 1
        return f"%r.{self.reg_count}"

    def new_label(self, prefix="label"):
        self.label_count += 1
        return f"{prefix}.{self.label_count}"

    def get_llvm_type(self, jss_type, dimension=None):
        base = ""
        if jss_type == 'int':
            base = 'i32'
        elif jss_type == 'real':
            base = 'double'
        elif jss_type == 'bool':
            base = 'i1'
        elif jss_type == 'str':
            base = 'i8*'
        elif jss_type == 'void':
            base = 'void'
        else:
            # Classes são ponteiros para structs
            base = f"%struct.{jss_type}*"

        if dimension is not None:
            if isinstance(dimension, list):
                dims = dimension
            else:
                dims = [dimension]
            t = base
            for d in reversed(dims):
                t = f"[{d} x {t}]"
            return t
        return base

    def get_default_value(self, llvm_type):
        if llvm_type == 'i32':
            return '0'
        elif llvm_type == 'double':
            return '0.000000e+00'
        elif llvm_type == 'i1':
            return 'false'
        elif llvm_type == 'i8*':
            return 'null'
        elif llvm_type.endswith('*'):
            return 'null'
        elif llvm_type.startswith('['):
            return 'zeroinitializer'
        return 'null'

    def to_llvm_escaped_string(self, s):
        res = []
        i = 0
        while i < len(s):
            c = s[i]
            if c == '"':
                res.append("\\22")
            elif c == '\\':
                res.append("\\5C")
            elif ord(c) < 32 or ord(c) > 126:
                res.append(f"\\{ord(c):02X}")
            else:
                res.append(c)
            i += 1
        return "".join(res)

    def get_or_create_string_constant(self, s):
        if s in self.strings:
            return self.strings[s]
        
        self.string_count += 1
        name = f"@.str.{self.string_count}"
        escaped = self.to_llvm_escaped_string(s)
        # LLVM precisa do terminador nulo \00
        length = len(s) + 1
        
        # Calcular o comprimento real considerando os caracteres especiais
        # A string original decodificada em Python tem len(s) caracteres + 1 nulo.
        self.const_decls.append(f"{name} = private unnamed_addr constant [{length} x i8] c\"{escaped}\\00\"")
        self.strings[s] = (name, length)
        return name, length

    def generate(self, ast):
        # 1. Primeira passada para coletar declarações globais de funções e classes
        self._preprocess_declarations(ast)
        
        # 2. Segunda passada para gerar código
        self.visit(ast)
        
        # 3. Concatenar todo o código gerado em uma única string textual
        lines = []
        lines.append("; --- DECLARAÇÕES RUNTIME ---")
        lines.extend(self.runtime_decls)
        lines.append("")
        
        if self.struct_decls:
            lines.append("; --- DECLARAÇÕES DE CLASSES ---")
            lines.extend(self.struct_decls)
            lines.append("")
            
        if self.const_decls:
            lines.append("; --- CONSTANTES DE STRING ---")
            lines.extend(self.const_decls)
            lines.append("")
            
        if self.global_decls:
            lines.append("; --- VARIÁVEIS GLOBAIS ---")
            lines.extend(self.global_decls)
            lines.append("")
            
        if self.func_decls:
            lines.append("; --- FUNÇÕES DO USUÁRIO ---")
            lines.extend(self.func_decls)
            lines.append("")
            
        # Adicionar o entrypoint principal @main do LLVM
        lines.append("; --- ENTRY POINT ---")
        lines.append("define i32 @main() {")
        lines.append("entry:")
        for code_line in self.main_code:
            lines.append("    " + code_line)
            
        # Verificar se o usuário definiu uma função main global
        if 'main' in self.functions_sig:
            lines.append("    call void @_jss_main()")
            
        lines.append("    ret i32 0")
        lines.append("}")
        
        return "\n".join(lines)

    def _preprocess_declarations(self, ast):
        if not isinstance(ast, ProgramNode):
            return
        
        for stmt in ast.statements:
            if isinstance(stmt, ClassDeclarationNode):
                # Registrar a classe e coletar seus atributos
                class_name = stmt.name
                attrs = []
                attr_types = {}
                attr_dims = {}
                for attr in stmt.attributes:
                    attrs.append(attr.name)
                    attr_types[attr.name] = attr.var_type
                    attr_dims[attr.name] = attr.dimension
                
                self.classes[class_name] = {
                    'attrs': attrs,
                    'attr_types': attr_types,
                    'attr_dims': attr_dims
                }
                
                # Gerar a declaração de struct no LLVM
                fields_llvm = []
                for attr_name in attrs:
                    llvm_t = self.get_llvm_type(attr_types[attr_name], attr_dims[attr_name])
                    fields_llvm.append(llvm_t)
                fields_str = ", ".join(fields_llvm)
                self.struct_decls.append(f"%struct.{class_name} = type {{ {fields_str} }}")
                
            elif isinstance(stmt, FunctionNode):
                param_types = [p[0] for p in stmt.params]
                self.functions_sig[stmt.name] = (stmt.return_type, stmt.return_dimension, param_types)

    def visit_ProgramNode(self, node):
        for stmt in node.statements:
            self.visit(stmt)

    def visit(self, node):
        if node is None:
            return None
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name)
        return visitor(node)

    # --- VISITORES DE EXPRESSÃO (Retornam (llvm_val, llvm_type)) ---

    def visit_NumberNode(self, node):
        if node.is_real:
            # Exibir real com formatação científica padrão do LLVM
            return f"{float(node.value):e}", "double"
        else:
            return str(node.value), "i32"

    def visit_StringNode(self, node):
        name, length = self.get_or_create_string_constant(node.value)
        reg = self.new_reg()
        self.emit(f"{reg} = getelementptr inbounds [{length} x i8], [{length} x i8]* {name}, i32 0, i32 0")
        return reg, "i8*"

    def visit_BooleanNode(self, node):
        return "true" if node.value else "false", "i1"

    def visit_NullNode(self, node):
        return "null", "i8*"

    def visit_IdentifierNode(self, node):
        ptr, llvm_type, jss_type, dimension = self.get_target_pointer(node)
        if dimension is not None:
            if llvm_type.endswith('*'):
                # Vetor parâmetro (passado por referência, ou seja, tipo* já é o ponteiro).
                # O ptr na tabela é tipo**, precisamos dar load para obter tipo*
                reg = self.new_reg()
                self.emit(f"{reg} = load {llvm_type}, {llvm_type}* {ptr}")
                return reg, llvm_type
            else:
                # Vetor local ou global (alocado como tipo direto, ou seja, seu endereço ptr já é tipo*)
                return ptr, llvm_type + "*"
        
        reg = self.new_reg()
        self.emit(f"{reg} = load {llvm_type}, {llvm_type}* {ptr}")
        return reg, llvm_type

    def get_target_pointer(self, node):
        if isinstance(node, IdentifierNode):
            res = self.current_scope.lookup(node.name)
            if res:
                return res  # (llvm_ptr, llvm_type, jss_type, dimension)
            # Se for global
            llvm_gname = f"@g_{node.name}"
            # Precisamos inferir o tipo global
            # Por segurança, deve estar mapeado se foi declarado
            return llvm_gname, "i8*", "invalid", None
            
        elif isinstance(node, ArrayAccessNode):
            array_ptr, array_type = self.visit(node.array_expr)
            index_val, index_type = self.visit(node.index_expr)
            
            # array_type é tipo de array apontado, ex: [3 x i32]* ou [3 x [4 x i32]]*
            # precisamos obter a parte interna do array
            # Ex: se array_type é [3 x i32]*, o tipo base é [3 x i32]
            base_type = array_type[:-1] # Remove o '*'
            
            # Determinar o tipo do elemento
            # Se base_type é [3 x i32], elemento é i32. Se for [3 x [4 x i32]], elemento é [4 x i32]
            # O formato é sempre "[N x Resto]"
            parts = base_type.split(" x ", 1)
            elem_type = parts[1][:-1] if parts[1].endswith(']') else parts[1]
            
            reg = self.new_reg()
            self.emit(f"{reg} = getelementptr {base_type}, {array_type} {array_ptr}, i32 0, i32 {index_val}")
            
            # O retorno é o ponteiro para o elemento (ex: i32*) e o tipo de elemento (i32)
            # Mas o dimension do elemento resultante reduz em 1
            return reg, elem_type, "array_elem", None
            
        elif isinstance(node, AttributeAccessNode):
            obj_reg, obj_type = self.visit(node.object_expr)
            # obj_type deve ser %struct.ClassName*
            class_name = obj_type[8:-1] # Remove %struct. e *
            class_info = self.classes[class_name]
            
            attr_name = node.attribute_name
            attr_idx = class_info['attrs'].index(attr_name)
            attr_jss_type = class_info['attr_types'][attr_name]
            attr_dim = class_info['attr_dims'][attr_name]
            attr_llvm_type = self.get_llvm_type(attr_jss_type, attr_dim)
            
            reg = self.new_reg()
            self.emit(f"{reg} = getelementptr %struct.{class_name}, %struct.{class_name}* {obj_reg}, i32 0, i32 {attr_idx}")
            return reg, attr_llvm_type, attr_jss_type, attr_dim
            
        raise ValueError(f"Nó de destino inválido: {type(node).__name__}")

    def visit_ArrayAccessNode(self, node):
        ptr, llvm_type, jss_type, dimension = self.get_target_pointer(node)
        if dimension is not None or llvm_type.startswith('['):
            return ptr, llvm_type + "*"
        
        reg = self.new_reg()
        self.emit(f"{reg} = load {llvm_type}, {llvm_type}* {ptr}")
        return reg, llvm_type

    def visit_AttributeAccessNode(self, node):
        ptr, llvm_type, jss_type, dimension = self.get_target_pointer(node)
        if dimension is not None or llvm_type.startswith('['):
            return ptr, llvm_type + "*"
            
        reg = self.new_reg()
        self.emit(f"{reg} = load {llvm_type}, {llvm_type}* {ptr}")
        return reg, llvm_type

    def visit_BinaryOpNode(self, node):
        op = node.op
        
        # Tratamento de Curto-Circuito
        if op == '&&':
            return self._generate_short_circuit_and(node)
        elif op == '||':
            return self._generate_short_circuit_or(node)
            
        l_val, l_type = self.visit(node.left)
        r_val, r_type = self.visit(node.right)
        
        # Coerção de int para real em expressões aritméticas/relacionais
        if l_type == 'double' and r_type == 'i32':
            reg = self.new_reg()
            self.emit(f"{reg} = sitofp i32 {r_val} to double")
            r_val, r_type = reg, 'double'
        elif l_type == 'i32' and r_type == 'double':
            reg = self.new_reg()
            self.emit(f"{reg} = sitofp i32 {l_val} to double")
            l_val, l_type = reg, 'double'
            
        # Concatenação de string com coercão implícita
        if op == '+' and (l_type == 'i8*' or r_type == 'i8*'):
            # Converter operando esquerdo se não for string
            if l_type != 'i8*':
                l_val, l_type = self._cast_value_to_string(l_val, l_type)
            # Converter operando direito se não for string
            if r_type != 'i8*':
                r_val, r_type = self._cast_value_to_string(r_val, r_type)
                
            reg = self.new_reg()
            self.emit(f"{reg} = call i8* @str_concat(i8* {l_val}, i8* {r_val})")
            return reg, 'i8*'

        # Operações Aritméticas
        if l_type == 'double':
            if op == '+':
                reg = self.new_reg()
                self.emit(f"{reg} = fadd double {l_val}, {r_val}")
                return reg, 'double'
            elif op == '-':
                reg = self.new_reg()
                self.emit(f"{reg} = fsub double {l_val}, {r_val}")
                return reg, 'double'
            elif op == '*':
                reg = self.new_reg()
                self.emit(f"{reg} = fmul double {l_val}, {r_val}")
                return reg, 'double'
            elif op == '/':
                reg = self.new_reg()
                self.emit(f"{reg} = fdiv double {l_val}, {r_val}")
                return reg, 'double'
        elif l_type == 'i32':
            if op == '+':
                reg = self.new_reg()
                self.emit(f"{reg} = add i32 {l_val}, {r_val}")
                return reg, 'i32'
            elif op == '-':
                reg = self.new_reg()
                self.emit(f"{reg} = sub i32 {l_val}, {r_val}")
                return reg, 'i32'
            elif op == '*':
                reg = self.new_reg()
                self.emit(f"{reg} = mul i32 {l_val}, {r_val}")
                return reg, 'i32'
            elif op == '/':
                reg = self.new_reg()
                self.emit(f"{reg} = sdiv i32 {l_val}, {r_val}")
                return reg, 'i32'
            elif op == '%':
                reg = self.new_reg()
                self.emit(f"{reg} = srem i32 {l_val}, {r_val}")
                return reg, 'i32'
            elif op == '**':
                reg = self.new_reg()
                self.emit(f"{reg} = call i32 @ipow(i32 {l_val}, i32 {r_val})")
                return reg, 'i32'

        # Comparações Relacionais
        if l_type == 'double':
            llvm_op = {
                '==': 'oeq', '!=': 'one',
                '>': 'ogt', '>=': 'oge',
                '<': 'olt', '<=': 'ole'
            }[op]
            reg = self.new_reg()
            self.emit(f"{reg} = fcmp {llvm_op} double {l_val}, {r_val}")
            return reg, 'i1'
        elif l_type in ('i32', 'i1'):
            # Permite comparar i32 ou booleano i1
            llvm_op = {
                '==': 'eq', '!=': 'ne',
                '>': 'sgt', '>=': 'sge',
                '<': 'slt', '<=': 'sle'
            }[op]
            reg = self.new_reg()
            self.emit(f"{reg} = icmp {llvm_op} {l_type} {l_val}, {r_val}")
            return reg, 'i1'
        elif l_type.endswith('*') or r_type.endswith('*') or l_type == 'i8*' or r_type == 'i8*':
            # Comparação de ponteiros (objetos, arrays, strings)
            llvm_op = {'==': 'eq', '!=': 'ne'}[op]
            reg = self.new_reg()
            
            # Fazer bitcast de ambos para i8* para garantir comparação de ponteiros uniforme no LLVM
            l_ptr_val = l_val
            if l_type != 'i8*':
                reg_l = self.new_reg()
                self.emit(f"{reg_l} = bitcast {l_type} {l_val} to i8*")
                l_ptr_val = reg_l
                
            r_ptr_val = r_val
            if r_type != 'i8*':
                reg_r = self.new_reg()
                self.emit(f"{reg_r} = bitcast {r_type} {r_val} to i8*")
                r_ptr_val = reg_r
                
            self.emit(f"{reg} = icmp {llvm_op} i8* {l_ptr_val}, {r_ptr_val}")
            return reg, 'i1'

        return "0", "void"

    def _cast_value_to_string(self, val, from_type):
        reg = self.new_reg()
        if from_type == 'i32':
            self.emit(f"{reg} = call i8* @int_to_str(i32 {val})")
            return reg, 'i8*'
        elif from_type == 'double':
            self.emit(f"{reg} = call i8* @real_to_str(double {val})")
            return reg, 'i8*'
        elif from_type == 'i1':
            self.emit(f"{reg} = call i8* @bool_to_str(i1 {val})")
            return reg, 'i8*'
        return val, from_type

    def _generate_short_circuit_and(self, node):
        l_val, _ = self.visit(node.left)
        
        rhs_label = self.new_label("and.rhs")
        end_label = self.new_label("and.end")
        
        entry_block = self.get_current_block_name()
        
        self.emit(f"br i1 {l_val}, label %{rhs_label}, label %{end_label}")
        
        # Bloco da direita
        self.block_terminated = False
        self.emit(f"\n{rhs_label}:")
        r_val, _ = self.visit(node.right)
        rhs_final_block = self.get_current_block_name()
        self.emit(f"br label %{end_label}")
        
        # Bloco final
        self.block_terminated = False
        self.emit(f"\n{end_label}:")
        reg = self.new_reg()
        self.emit(f"{reg} = phi i1 [ false, %{entry_block} ], [ {r_val}, %{rhs_final_block} ]")
        return reg, 'i1'

    def _generate_short_circuit_or(self, node):
        l_val, _ = self.visit(node.left)
        
        rhs_label = self.new_label("or.rhs")
        end_label = self.new_label("or.end")
        
        entry_block = self.get_current_block_name()
        
        self.emit(f"br i1 {l_val}, label %{end_label}, label %{rhs_label}")
        
        # Bloco da direita
        self.block_terminated = False
        self.emit(f"\n{rhs_label}:")
        r_val, _ = self.visit(node.right)
        rhs_final_block = self.get_current_block_name()
        self.emit(f"br label %{end_label}")
        
        # Bloco final
        self.block_terminated = False
        self.emit(f"\n{end_label}:")
        reg = self.new_reg()
        self.emit(f"{reg} = phi i1 [ true, %{entry_block} ], [ {r_val}, %{rhs_final_block} ]")
        return reg, 'i1'

    def get_current_block_name(self):
        # Percorre o buffer atual de trás para frente para achar a última etiqueta (label) de bloco
        for line in reversed(self.current_buffer):
            line_s = line.strip()
            if line_s.endswith(":") and not line_s.startswith(";"):
                return line_s[:-1]
        return "entry"

    def visit_UnaryOpNode(self, node):
        op = node.op
        
        if op in ('++', '--'):
            # Incremento/Decremento prefixado (L-Value)
            ptr, llvm_type, _, _ = self.get_target_pointer(node.expression)
            
            # Carregar o valor atual
            reg_old = self.new_reg()
            self.emit(f"{reg_old} = load {llvm_type}, {llvm_type}* {ptr}")
            
            # Calcular novo valor
            reg_new = self.new_reg()
            if llvm_type == 'i32':
                inc_val = "1"
                self.emit(f"{reg_new} = add i32 {reg_old}, {inc_val}" if op == '++' else f"{reg_new} = sub i32 {reg_old}, {inc_val}")
            else: # double
                inc_val = "1.000000e+00"
                self.emit(f"{reg_new} = fadd double {reg_old}, {inc_val}" if op == '++' else f"{reg_new} = fsub double {reg_old}, {inc_val}")
                
            # Salvar de volta
            self.emit(f"store {llvm_type} {reg_new}, {llvm_type}* {ptr}")
            return reg_new, llvm_type
            
        val, v_type = self.visit(node.expression)
        
        if op == '!':
            reg = self.new_reg()
            self.emit(f"{reg} = xor i1 {val}, true")
            return reg, 'i1'
        elif op == '+':
            return val, v_type
        elif op == '-':
            reg = self.new_reg()
            if v_type == 'double':
                self.emit(f"{reg} = fneg double {val}")
            else:
                self.emit(f"{reg} = sub i32 0, {val}")
            return reg, v_type
            
        return "0", "void"

    def visit_CastNode(self, node):
        val, from_type = self.visit(node.expression)
        target = node.target_type
        
        if target == 'int':
            if from_type == 'double':
                reg = self.new_reg()
                self.emit(f"{reg} = fptosi double {val} to i32")
                return reg, 'i32'
            elif from_type == 'i1':
                reg = self.new_reg()
                self.emit(f"{reg} = zext i1 {val} to i32")
                return reg, 'i32'
            return val, 'i32'
            
        elif target == 'real':
            if from_type == 'i32':
                reg = self.new_reg()
                self.emit(f"{reg} = sitofp i32 {val} to double")
                return reg, 'double'
            elif from_type == 'i1':
                reg = self.new_reg()
                self.emit(f"{reg} = uitofp i1 {val} to double")
                return reg, 'double'
            return val, 'double'
            
        elif target == 'bool':
            if from_type == 'i32':
                reg = self.new_reg()
                self.emit(f"{reg} = icmp ne i32 {val}, 0")
                return reg, 'i1'
            elif from_type == 'double':
                reg = self.new_reg()
                self.emit(f"{reg} = fcmp one double {val}, 0.0")
                return reg, 'i1'
            return val, 'i1'
            
        elif target == 'str':
            val_str, _ = self._cast_value_to_string(val, from_type)
            return val_str, 'i8*'
            
        return "0", "void"

    def visit_NewObjectNode(self, node):
        class_name = node.class_name
        class_info = self.classes[class_name]
        
        # Calcular o tamanho em bytes do struct da classe no LLVM de forma dinâmica e portável
        size_reg = self.new_reg()
        self.emit(f"{size_reg} = ptrtoint %struct.{class_name}* getelementptr (%struct.{class_name}, %struct.{class_name}* null, i32 1) to i64")
        
        # Chamar malloc
        malloc_reg = self.new_reg()
        self.emit(f"{malloc_reg} = call i8* @malloc(i64 {size_reg})")
        
        # Fazer cast de i8* para o ponteiro do struct
        cast_reg = self.new_reg()
        self.emit(f"{cast_reg} = bitcast i8* {malloc_reg} to %struct.{class_name}*")
        
        # Chamar o construtor da classe
        arg_list = []
        # O construtor recebe 'this' como primeiro argumento
        arg_list.append(f"%struct.{class_name}* {cast_reg}")
        
        for arg_node in node.arguments:
            a_val, a_type = self.visit(arg_node)
            arg_list.append(f"{a_type} {a_val}")
            
        args_str = ", ".join(arg_list)
        self.emit(f"call void @{class_name}_constructor({args_str})")
        
        # Retorna o ponteiro do objeto recém-criado
        return cast_reg, f"%struct.{class_name}*"

    def visit_CallNode(self, node):
        if isinstance(node.callee, AttributeAccessNode):
            # Chamada de método: obj.metodo(args)
            obj_reg, obj_type = self.visit(node.callee.object_expr)
            class_name = obj_type[8:-1] # Extrai nome da classe
            method_name = node.callee.attribute_name
            
            # Carregar a assinatura
            class_info = self.classes[class_name]
            # O LLVM mapeia métodos como @NomeClasse_NomeMetodo
            llvm_func_name = f"@{class_name}_{method_name}"
            
            # Precisamos do tipo de retorno do método
            # Como a AST não anota tipos nos nós de forma persistente, 
            # podemos procurar a declaração do método correspondente na AST ou no mapeamento
            # JSS simplificado: vamos obter os tipos de argumentos e retorno
            # Buscando a assinatura no preprocessador
            ret_jss = "void"
            ret_dim = None
            
            # Procurar classe na AST global ou salvar na tabela
            # Vamos assumir i32 por default se não acharmos (mas quase sempre acharemos em classes preprocessadas)
            # Para métodos, vamos buscar o tipo do método real:
            # Vamos descobrir o método correto nos métodos preprocessados da classe
            method_llvm_ret = "void"
            
            # Vamos buscar se o método retorna algo
            # Faremos busca simples na nossa tabela global de métodos da classe
            # Como JSS é simples, podemos descobrir dinamicamente baseado nas assinaturas
            # Para fins de simplificação: se retornar void é void, se não é o tipo correspondente.
            # Vamos registrar a assinatura do método também no preprocessamento.
            # (Adicionado no _preprocess_declarations mais tarde)
            sig_key = f"{class_name}_{method_name}"
            if sig_key in self.functions_sig:
                r_jss, r_dim, _ = self.functions_sig[sig_key]
                method_llvm_ret = self.get_llvm_type(r_jss, r_dim)
            else:
                method_llvm_ret = "i32" # Fallback seguro
                
            arg_list = []
            arg_list.append(f"%struct.{class_name}* {obj_reg}") # implicit 'this'
            
            for arg_node in node.arguments:
                a_val, a_type = self.visit(arg_node)
                arg_list.append(f"{a_type} {a_val}")
                
            args_str = ", ".join(arg_list)
            
            if method_llvm_ret == 'void':
                self.emit(f"call void {llvm_func_name}({args_str})")
                return "0", "void"
            else:
                reg = self.new_reg()
                self.emit(f"{reg} = call {method_llvm_ret} {llvm_func_name}({args_str})")
                return reg, method_llvm_ret
                
        else:
            # Chamada de função global: foo(args)
            func_name = node.callee.name
            llvm_func_name = f"@{func_name}"
            if func_name == 'main':
                llvm_func_name = "@_jss_main"
                
            r_jss, r_dim, _ = self.functions_sig[func_name]
            ret_llvm_type = self.get_llvm_type(r_jss, r_dim)
            
            arg_list = []
            for arg_node in node.arguments:
                a_val, a_type = self.visit(arg_node)
                arg_list.append(f"{a_type} {a_val}")
            args_str = ", ".join(arg_list)
            
            if ret_llvm_type == 'void':
                self.emit(f"call void {llvm_func_name}({args_str})")
                return "0", "void"
            else:
                reg = self.new_reg()
                self.emit(f"{reg} = call {ret_llvm_type} {llvm_func_name}({args_str})")
                return reg, ret_llvm_type

    def visit_ArrayLiteralNode(self, node):
        # Literais de vetores no JSS são usados apenas em inicializações.
        # Retornamos uma lista de seus valores avaliados
        evaluated = []
        for expr in node.expressions:
            val, v_type = self.visit(expr)
            evaluated.append((val, v_type))
        return evaluated, "literal_array"

    # --- VISITORES DE DECLARAÇÃO E CONTROLE DE FLUXO ---

    def visit_VarDeclarationNode(self, node):
        var_type = node.var_type
        dimension = node.dimension
        llvm_type = self.get_llvm_type(var_type, dimension)
        
        if self.current_buffer == self.main_code and self.current_scope.parent is None:
            # Variável Global
            llvm_name = f"@g_{node.name}"
            default_init = self.get_default_value(llvm_type)
            self.global_decls.append(f"{llvm_name} = global {llvm_type} {default_init}")
            self.current_scope.define(node.name, llvm_name, llvm_type, var_type, dimension)
            
            # Se houver valor inicializador, executá-lo no entrypoint principal
            if node.value:
                if isinstance(node.value, ArrayLiteralNode):
                    # Inicialização de vetor global
                    evaluated, _ = self.visit(node.value)
                    for idx, (elem_val, elem_type) in enumerate(evaluated):
                        reg_ptr = self.new_reg()
                        self.emit(f"{reg_ptr} = getelementptr {llvm_type}, {llvm_type}* {llvm_name}, i32 0, i32 {idx}")
                        self.emit(f"store {elem_type} {elem_val}, {elem_type}* {reg_ptr}")
                else:
                    val, v_type = self.visit(node.value)
                    if llvm_type == 'double' and v_type == 'i32':
                        reg = self.new_reg()
                        self.emit(f"{reg} = sitofp i32 {val} to double")
                        val = reg
                    self.emit(f"store {llvm_type} {val}, {llvm_type}* {llvm_name}")
            else:
                # Inicialização padrão para vetores globais não inicializados
                if dimension is not None:
                    self._initialize_array_with_defaults(llvm_name, llvm_type, var_type, dimension)
        else:
            # Variável Local
            llvm_name = f"%{node.name}.addr"
            self.emit(f"{llvm_name} = alloca {llvm_type}")
            self.current_scope.define(node.name, llvm_name, llvm_type, var_type, dimension)
            
            # Inicializar com valores padrões do tipo
            default_val = self.get_default_value(llvm_type)
            if default_val != 'zeroinitializer':
                self.emit(f"store {llvm_type} {default_val}, {llvm_type}* {llvm_name}")
                
            if node.value:
                if isinstance(node.value, ArrayLiteralNode):
                    evaluated, _ = self.visit(node.value)
                    for idx, (elem_val, elem_type) in enumerate(evaluated):
                        reg_ptr = self.new_reg()
                        self.emit(f"{reg_ptr} = getelementptr {llvm_type}, {llvm_type}* {llvm_name}, i32 0, i32 {idx}")
                        self.emit(f"store {elem_type} {elem_val}, {elem_type}* {reg_ptr}")
                else:
                    val, v_type = self.visit(node.value)
                    if llvm_type == 'double' and v_type == 'i32':
                        reg = self.new_reg()
                        self.emit(f"{reg} = sitofp i32 {val} to double")
                        val = reg
                    self.emit(f"store {llvm_type} {val}, {llvm_type}* {llvm_name}")
            else:
                if dimension is not None:
                    self._initialize_array_with_defaults(llvm_name, llvm_type, var_type, dimension)

    def _initialize_array_with_defaults(self, array_ptr, array_llvm_type, elem_jss_type, dimension):
        # Inicializa um vetor estático recursivamente com zeros/nulos padrões
        elem_llvm_type = self.get_llvm_type(elem_jss_type)
        default_val = self.get_default_value(elem_llvm_type)
        
        # Achatar dimensões
        if isinstance(dimension, list):
            dims = dimension
        else:
            dims = [dimension]
            
        total_elements = 1
        for d in dims:
            total_elements *= d
            
        # Fazer bitcast do ponteiro do array para o ponteiro do elemento base
        flat_ptr = self.new_reg()
        self.emit(f"{flat_ptr} = bitcast {array_llvm_type}* {array_ptr} to {elem_llvm_type}*")
        
        # Inicializar linearmente
        for idx in range(total_elements):
            reg_ptr = self.new_reg()
            self.emit(f"{reg_ptr} = getelementptr {elem_llvm_type}, {elem_llvm_type}* {flat_ptr}, i32 {idx}")
            self.emit(f"store {elem_llvm_type} {default_val}, {elem_llvm_type}* {reg_ptr}")

    def visit_AssignmentNode(self, node):
        op = node.op
        
        # Caso de curto-circuito em atribuições compostas &&= e ||=
        if op in ('&&=', '||='):
            # x &&= y  ===>  x = x && y
            ptr, llvm_type, jss_type, dimension = self.get_target_pointer(node.target)
            
            # Carregar o valor atual (lado esquerdo)
            reg_old = self.new_reg()
            self.emit(f"{reg_old} = load {llvm_type}, {llvm_type}* {ptr}")
            
            # Realizar a lógica de curto circuito correspondente
            rhs_label = self.new_label("assign.rhs")
            end_label = self.new_label("assign.end")
            entry_block = self.get_current_block_name()
            
            if op == '&&=':
                self.emit(f"br i1 {reg_old}, label %{rhs_label}, label %{end_label}")
            else: # ||=
                self.emit(f"br i1 {reg_old}, label %{end_label}, label %{rhs_label}")
                
            # Avaliar o valor direito
            self.emit(f"\n{rhs_label}:")
            self.block_terminated = False
            r_val, _ = self.visit(node.value)
            rhs_final_block = self.get_current_block_name()
            self.emit(f"br label %{end_label}")
            
            # Bloco de junção
            self.emit(f"\n{end_label}:")
            self.block_terminated = False
            reg_phi = self.new_reg()
            if op == '&&=':
                self.emit(f"{reg_phi} = phi i1 [ false, %{entry_block} ], [ {r_val}, %{rhs_final_block} ]")
            else: # ||=
                self.emit(f"{reg_phi} = phi i1 [ true, %{entry_block} ], [ {r_val}, %{rhs_final_block} ]")
                
            # Salvar na variável
            self.emit(f"store i1 {reg_phi}, i1* {ptr}")
            return reg_phi, 'i1'

        ptr, llvm_type, _, _ = self.get_target_pointer(node.target)
        
        if op == '=':
            val, v_type = self.visit(node.value)
            if llvm_type == 'double' and v_type == 'i32':
                reg = self.new_reg()
                self.emit(f"{reg} = sitofp i32 {val} to double")
                val, v_type = reg, 'double'
            elif llvm_type == 'i8*' and v_type != 'i8*':
                # Objeto de classe atribuído como null
                val = "null"
            self.emit(f"store {llvm_type} {val}, {llvm_type}* {ptr}")
            return val, llvm_type
        else:
            # Atribuições compostas: +=, -=, *=, /=, %=
            arith_op = op[:-1] # Remove o '='
            
            # Carregar valor antigo
            reg_old = self.new_reg()
            self.emit(f"{reg_old} = load {llvm_type}, {llvm_type}* {ptr}")
            
            # Avaliar o novo termo
            val_rhs, r_type = self.visit(node.value)
            
            # Coerção se necessário
            if llvm_type == 'double' and r_type == 'i32':
                reg = self.new_reg()
                self.emit(f"{reg} = sitofp i32 {val_rhs} to double")
                val_rhs = reg
                
            # Computar nova operação
            reg_res = self.new_reg()
            if llvm_type == 'double':
                llvm_inst = {'+': 'fadd', '-': 'fsub', '*': 'fmul', '/': 'fdiv'}[arith_op]
                self.emit(f"{reg_res} = {llvm_inst} double {reg_old}, {val_rhs}")
            else: # i32
                llvm_inst = {'+': 'add', '-': 'sub', '*': 'mul', '/': 'sdiv', '%': 'srem'}[arith_op]
                self.emit(f"{reg_res} = {llvm_inst} i32 {reg_old}, {val_rhs}")
                
            # Salvar resultado
            self.emit(f"store {llvm_type} {reg_res}, {llvm_type}* {ptr}")
            return reg_res, llvm_type

    def visit_BlockNode(self, node):
        for stmt in node.statements:
            self.visit(stmt)

    def visit_IfNode(self, node):
        cond_val, _ = self.visit(node.condition)
        
        then_label = self.new_label("if.then")
        else_label = self.new_label("if.else") if node.else_branch else None
        merge_label = self.new_label("if.merge")
        
        if else_label:
            self.emit(f"br i1 {cond_val}, label %{then_label}, label %{else_label}")
        else:
            self.emit(f"br i1 {cond_val}, label %{then_label}, label %{merge_label}")
            
        # Ramo Then
        self.block_terminated = False
        self.emit(f"\n{then_label}:")
        self.visit(node.then_branch)
        if not self.block_terminated:
            self.emit(f"br label %{merge_label}")
            
        # Ramo Else
        if else_label:
            self.block_terminated = False
            self.emit(f"\n{else_label}:")
            self.visit(node.else_branch)
            if not self.block_terminated:
                self.emit(f"br label %{merge_label}")
                
        # Ramo Merge
        self.block_terminated = False
        self.emit(f"\n{merge_label}:")

    def visit_WhileNode(self, node):
        cond_label = self.new_label("while.cond")
        body_label = self.new_label("while.body")
        end_label = self.new_label("while.end")
        
        self.emit(f"br label %{cond_label}")
        
        # Bloco de condição
        self.block_terminated = False
        self.emit(f"\n{cond_label}:")
        cond_val, _ = self.visit(node.condition)
        self.emit(f"br i1 {cond_val}, label %{body_label}, label %{end_label}")
        
        # Bloco de corpo
        self.block_terminated = False
        self.emit(f"\n{body_label}:")
        self.loop_stack.append(end_label)
        self.visit(node.body)
        self.loop_stack.pop()
        if not self.block_terminated:
            self.emit(f"br label %{cond_label}")
            
        # Bloco de fim
        self.block_terminated = False
        self.emit(f"\n{end_label}:")

    def visit_ForNode(self, node):
        cond_label = self.new_label("for.cond")
        body_label = self.new_label("for.body")
        step_label = self.new_label("for.step")
        end_label = self.new_label("for.end")
        
        # Inicialização do loop
        if node.init:
            self.visit(node.init)
            
        self.emit(f"br label %{cond_label}")
        
        # Bloco de condição
        self.block_terminated = False
        self.emit(f"\n{cond_label}:")
        if node.condition:
            cond_val, _ = self.visit(node.condition)
            self.emit(f"br i1 {cond_val}, label %{body_label}, label %{end_label}")
        else:
            self.emit(f"br label %{body_label}")
            
        # Bloco de corpo
        self.block_terminated = False
        self.emit(f"\n{body_label}:")
        self.loop_stack.append(end_label)
        self.visit(node.body)
        self.loop_stack.pop()
        if not self.block_terminated:
            self.emit(f"br label %{step_label}")
            
        # Bloco de passo/incremento
        self.block_terminated = False
        self.emit(f"\n{step_label}:")
        if node.update:
            self.visit(node.update)
        self.emit(f"br label %{cond_label}")
        
        # Bloco de fim
        self.block_terminated = False
        self.emit(f"\n{end_label}:")

    def visit_BreakNode(self, node):
        if self.loop_stack:
            target = self.loop_stack[-1]
            self.emit(f"br label %{target}")
            self.block_terminated = True

    def visit_FunctionNode(self, node):
        # Salvar o buffer principal e escopo para compilação local de função
        old_buf = self.current_buffer
        old_scope = self.current_scope
        
        self.current_buffer = []
        self.current_scope = Scope(parent=old_scope)
        self.reg_count = 0
        self.label_count = 0
        self.block_terminated = False
        
        func_name = node.name
        llvm_func_name = f"@{func_name}"
        if func_name == 'main':
            llvm_func_name = "@_jss_main"
            
        ret_type = self.get_llvm_type(node.return_type, node.return_dimension)
        self.current_function_ret_type = ret_type
        
        # Gerar parâmetros do LLVM
        params_llvm = []
        params_allocations = []
        for p in node.params:
            p_type, p_name = p[0], p[1]
            p_dim = p[2] if len(p) > 2 else None
            
            p_llvm_type = self.get_llvm_type(p_type, p_dim)
            if p_dim is not None:
                # Vetores são passados por referência
                p_llvm_type += "*"
                
            reg_in = f"%_in_{p_name}"
            params_llvm.append(f"{p_llvm_type} {reg_in}")
            params_allocations.append((p_name, reg_in, p_llvm_type, p_type, p_dim))
            
        params_str = ", ".join(params_llvm)
        
        self.emit(f"define {ret_type} {llvm_func_name}({params_str}) {{")
        self.emit("entry:")
        
        # Alocar espaço local para cada parâmetro e copiar valor de entrada
        for name, reg_in, llvm_type, jss_type, dimension in params_allocations:
            addr_name = f"%{name}.addr"
            self.emit(f"{addr_name} = alloca {llvm_type}")
            self.emit(f"store {llvm_type} {reg_in}, {llvm_type}* {addr_name}")
            self.current_scope.define(name, addr_name, llvm_type, jss_type, dimension)
            
        # Compilar o corpo da função
        self.visit(node.body)
        
        # Garante retorno caso seja uma função void sem comando return explícito
        if ret_type == 'void' and not self.block_terminated:
            self.emit("ret void")
            
        # Se o último item no buffer for um label, insere unreachable para evitar blocos vazios
        if self.current_buffer and self.current_buffer[-1].strip().endswith(":"):
            self.block_terminated = False
            self.emit("unreachable")
            
        self.current_buffer.append("}")
        
        # Salva o código gerado no buffer de funções globais
        self.func_decls.extend(self.current_buffer)
        
        # Restaurar estado
        self.current_buffer = old_buf
        self.current_scope = old_scope
        self.current_function_ret_type = None

    def visit_ReturnNode(self, node):
        if node.expression:
            val, v_type = self.visit(node.expression)
            # Tratar coercão implícita para o tipo esperado de retorno da função
            if self.current_function_ret_type == 'double' and v_type == 'i32':
                reg = self.new_reg()
                self.emit(f"{reg} = sitofp i32 {val} to double")
                val, v_type = reg, 'double'
            self.emit(f"ret {self.current_function_ret_type} {val}")
        else:
            self.emit("ret void")
        self.block_terminated = True

    def visit_ClassDeclarationNode(self, node):
        # As structs de classes já foram processadas na primeira passada
        # Agora geramos construtores e métodos
        class_name = node.name
        
        # Registrar a assinatura de todos os métodos da classe no preprocessador
        for m in node.methods:
            sig_key = f"{class_name}_{m.name}"
            self.functions_sig[sig_key] = (m.return_type, m.return_dimension, [p[0] for p in m.params])
            
        # 1. Compilar Construtor
        if node.constructor:
            self.visit(node.constructor)
            
        # 2. Compilar Métodos
        for m in node.methods:
            # Salvar buffer e escopo
            old_buf = self.current_buffer
            old_scope = self.current_scope
            
            self.current_buffer = []
            self.current_scope = Scope(parent=old_scope)
            self.reg_count = 0
            self.label_count = 0
            self.block_terminated = False
            
            ret_type = self.get_llvm_type(m.return_type, m.return_dimension)
            self.current_function_ret_type = ret_type
            
            # Parâmetros: 'this' é sempre o primeiro
            params_llvm = [f"%struct.{class_name}* %this"]
            params_allocations = []
            
            for p in m.params:
                p_type, p_name = p[0], p[1]
                p_dim = p[2] if len(p) > 2 else None
                p_llvm_type = self.get_llvm_type(p_type, p_dim)
                if p_dim is not None:
                    p_llvm_type += "*"
                reg_in = f"%_in_{p_name}"
                params_llvm.append(f"{p_llvm_type} {reg_in}")
                params_allocations.append((p_name, reg_in, p_llvm_type, p_type, p_dim))
                
            params_str = ", ".join(params_llvm)
            
            self.emit(f"define {ret_type} @{class_name}_{m.name}({params_str}) {{")
            self.emit("entry:")
            
            # Alocar e salvar o 'this' no escopo local
            this_addr = "%this.addr"
            self.emit(f"{this_addr} = alloca %struct.{class_name}*")
            self.emit(f"store %struct.{class_name}* %this, %struct.{class_name}** {this_addr}")
            self.current_scope.define("this", this_addr, f"%struct.{class_name}*", class_name, None)
            
            # Alocar parâmetros locais
            for name, reg_in, llvm_type, jss_type, dimension in params_allocations:
                addr_name = f"%{name}.addr"
                self.emit(f"{addr_name} = alloca {llvm_type}")
                self.emit(f"store {llvm_type} {reg_in}, {llvm_type}* {addr_name}")
                self.current_scope.define(name, addr_name, llvm_type, jss_type, dimension)
                
            self.visit(m.body)
            
            if ret_type == 'void' and not self.block_terminated:
                self.emit("ret void")
                
            if self.current_buffer and self.current_buffer[-1].strip().endswith(":"):
                self.block_terminated = False
                self.emit("unreachable")
                
            self.current_buffer.append("}")
            
            self.func_decls.extend(self.current_buffer)
            
            # Restaurar
            self.current_buffer = old_buf
            self.current_scope = old_scope
            self.current_function_ret_type = None

    def visit_ClassConstructorNode(self, node):
        class_name = node.class_name
        
        old_buf = self.current_buffer
        old_scope = self.current_scope
        
        self.current_buffer = []
        self.current_scope = Scope(parent=old_scope)
        self.reg_count = 0
        self.label_count = 0
        self.block_terminated = False
        
        # Construtores sempre retornam void no nosso design
        ret_type = "void"
        self.current_function_ret_type = ret_type
        
        params_llvm = [f"%struct.{class_name}* %this"]
        params_allocations = []
        for p in node.params:
            p_type, p_name = p[0], p[1]
            p_dim = p[2] if len(p) > 2 else None
            p_llvm_type = self.get_llvm_type(p_type, p_dim)
            if p_dim is not None:
                p_llvm_type += "*"
            reg_in = f"%_in_{p_name}"
            params_llvm.append(f"{p_llvm_type} {reg_in}")
            params_allocations.append((p_name, reg_in, p_llvm_type, p_type, p_dim))
            
        params_str = ", ".join(params_llvm)
        
        self.emit(f"define void @{class_name}_constructor({params_str}) {{")
        self.emit("entry:")
        
        # Salvar o 'this'
        this_addr = "%this.addr"
        self.emit(f"{this_addr} = alloca %struct.{class_name}*")
        self.emit(f"store %struct.{class_name}* %this, %struct.{class_name}** {this_addr}")
        self.current_scope.define("this", this_addr, f"%struct.{class_name}*", class_name, None)
        
        # Alocar parâmetros locais
        for name, reg_in, llvm_type, jss_type, dimension in params_allocations:
            addr_name = f"%{name}.addr"
            self.emit(f"{addr_name} = alloca {llvm_type}")
            self.emit(f"store {llvm_type} {reg_in}, {llvm_type}* {addr_name}")
            self.current_scope.define(name, addr_name, llvm_type, jss_type, dimension)
            
        self.visit(node.body)
        
        if not self.block_terminated:
            self.emit("ret void")
            
        if self.current_buffer and self.current_buffer[-1].strip().endswith(":"):
            self.block_terminated = False
            self.emit("unreachable")
            
        self.current_buffer.append("}")
        
        self.func_decls.extend(self.current_buffer)
        
        # Restaurar
        self.current_buffer = old_buf
        self.current_scope = old_scope
        self.current_function_ret_type = None

    def visit_ConsoleLogNode(self, node):
        for idx, expr in enumerate(node.expressions):
            val, v_type = self.visit(expr)
            
            # Espaço entre argumentos
            if idx > 0:
                self.emit("call void @print_space()")
                
            if v_type == 'i32':
                self.emit(f"call void @print_int(i32 {val})")
            elif v_type == 'double':
                self.emit(f"call void @print_real(double {val})")
            elif v_type == 'i8*':
                self.emit(f"call void @print_str(i8* {val})")
            elif v_type == 'i1':
                self.emit(f"call void @print_bool(i1 {val})")
                
        self.emit("call void @print_newline()")

    def visit_InputNode(self, node):
        for target in node.targets:
            ptr, llvm_type, _, _ = self.get_target_pointer(target)
            
            reg = self.new_reg()
            if llvm_type == 'i32':
                self.emit(f"{reg} = call i32 @read_int()")
            elif llvm_type == 'double':
                self.emit(f"{reg} = call double @read_real()")
            elif llvm_type == 'i8*':
                self.emit(f"{reg} = call i8* @read_str()")
                
            self.emit(f"store {llvm_type} {reg}, {llvm_type}* {ptr}")
