"""Análise semântica da linguagem JSS.

Responsável por validações de tipos, escopos e uso de identificadores.
"""

from frontend.symbol_table import Symbol, SymbolTable
from frontend.errors import SemanticError, format_visual_error
from frontend.ast_nodes import (
    ProgramNode, VarDeclarationNode, AssignmentNode, BlockNode,
    IfNode, WhileNode, ForNode, BreakNode, FunctionNode, ReturnNode,
    CallNode, BinaryOpNode, UnaryOpNode, ArrayAccessNode, ArrayLiteralNode,
    ClassDeclarationNode, ClassConstructorNode, AttributeAccessNode,
    NewObjectNode, ConsoleLogNode, InputNode, CastNode, NumberNode,
    StringNode, BooleanNode, NullNode, IdentifierNode
)


class SemanticAnalyzer:
    def __init__(self):
        self.global_scope = SymbolTable()
        self.current_scope = self.global_scope
        self.errors = []
        self.source_code = ""
        self.current_function = None
        self.current_class = None
        self.in_loop = 0

    INVALID = 'invalid'

    def error(self, node, msg):
        """Formata e acumula um erro semântico para relatório posterior."""
        line = getattr(node, 'lineno', 1) or 1
        lexpos = getattr(node, 'lexpos', 0) or 0
        formatted = format_visual_error(self.source_code, "Erro Semântico", msg, line, lexpos)
        self.errors.append(formatted)

    def analyze(self, node):
        """Método de despacho de visita baseado no tipo do nó."""
        if node is None:
            return None
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Visita genérica que percorre os filhos de um nó."""
        if hasattr(node, '__dict__'):
            for value in node.__dict__.values():
                if isinstance(value, list):
                    for item in value:
                        self.analyze(item)
                else:
                    self.analyze(value)
        return None

    def check_type_compatibility(self, node, expected, got, is_assignment=False):
        """Verifica a compatibilidade de tipos, permitindo coerção de int para real."""
        if expected == self.INVALID or got == self.INVALID:
            return
        if expected == got:
            return
        if expected == 'real' and got == 'int':
            return
        # Objetos de classe podem ser null
        if expected not in ('int', 'real', 'str', 'bool', 'void') and got == 'null':
            return
        self.error(node, f"tipos incompativeis: esperava '{expected}', mas obteve '{got}'.")

    def is_constant_target(self, node):
        """Verifica se o alvo de uma atribuição é constante (L-value)."""
        if isinstance(node, IdentifierNode):
            sym = self.current_scope.lookup(node.name)
            if sym and sym.is_const:
                return True
        elif isinstance(node, ArrayAccessNode):
            return self.is_constant_target(node.array_expr)
        elif isinstance(node, AttributeAccessNode):
            return self.is_constant_target(node.object_expr)
        return False

    # --- Visitores de Declaração e Controle de Fluxo ---

    def visit_ProgramNode(self, node):
        for stmt in node.statements:
            self.analyze(stmt)
        if self.errors:
            raise SemanticError("\n" + "\n\n".join(self.errors))
        return None

    def visit_VarDeclarationNode(self, node):
        # 1. Verificar se já existe no escopo local atual (redeclaracao)
        if self.current_class and not self.current_function:
            if node.name in self.current_class.attributes:
                self.error(node, f"redeclaracao do atributo '{node.name}' na classe '{self.current_class.name}'.")
        else:
            if self.current_scope.lookup_local(node.name):
                self.error(node, f"redeclaracao do identificador '{node.name}' no mesmo escopo.")

        # 2. Validar o tipo
        var_type = node.var_type
        type_valid = True
        if var_type not in ('int', 'real', 'str', 'bool', 'void'):
            class_sym = self.global_scope.lookup(var_type)
            if not class_sym or not class_sym.is_class:
                self.error(node, f"tipo '{var_type}' nao definido.")
                var_type = self.INVALID
                type_valid = False

        # 3. Validar atribuição de valor inicial se houver
        if node.value:
            value_type = self.analyze(node.value)
            if type_valid and value_type != self.INVALID:
                if node.dimension is not None:
                    num_dims = len(node.dimension) if isinstance(node.dimension, list) else 1
                    expected_type = node.var_type + ("[]" * num_dims)
                else:
                    expected_type = var_type
                self.check_type_compatibility(node.value, expected_type, value_type, is_assignment=True)

        # 4. Validar dimensões de vetores
        dimension = node.dimension
        if dimension is not None:
            if node.value and not isinstance(node.value, (ArrayLiteralNode, CallNode)):
                self.error(node, f"atribuicao invalida para vetor '{node.name}'. Vetores devem ser inicializados com literais de vetor.")
            if node.value and isinstance(node.value, ArrayLiteralNode):
                # Verificar se o tamanho do literal confere com a dimensão declarada
                if isinstance(dimension, int):
                    expected_size = dimension
                elif isinstance(dimension, str) and dimension.isdigit():
                    expected_size = int(dimension)
                else:
                    expected_size = None

                if expected_size is not None and len(node.value.expressions) != expected_size:
                    self.error(node, f"tamanho do literal de vetor ({len(node.value.expressions)}) nao condiz com a dimensao declarada ({expected_size}).")

                if type_valid:
                    for expr in node.value.expressions:
                        elem_type = self.analyze(expr)
                        self.check_type_compatibility(expr, node.var_type, elem_type)

        # 5. Registrar o símbolo (com tipo original ou invalid para suprimir cascata)
        sym = Symbol(
            name=node.name,
            type_name=var_type,
            is_const=node.is_const,
            dimension=dimension
        )

        if self.current_class and not self.current_function:
            sym.is_attribute = True
            self.current_class.attributes[node.name] = sym
        else:
            self.current_scope.define(node.name, sym)

        return None

    def visit_AssignmentNode(self, node):
        if self.is_constant_target(node.target):
            self.error(node, f"atribuicao para alvo constante '{getattr(node.target, 'name', '')}' nao e permitida.")

        target_type = self.analyze(node.target)
        value_type = self.analyze(node.value)

        if target_type == self.INVALID or value_type == self.INVALID:
            return self.INVALID

        if target_type.endswith('[]'):
            self.error(node, f"atribuicao direta para vetor nao e permitida. Vetores so podem ser modificados elemento a elemento.")
            return self.INVALID

        if node.op != '=':
            if node.op in ('&&=', '||='):
                if target_type != 'bool' or value_type != 'bool':
                    self.error(node, f"operador composto '{node.op}' requer operandos booleanos.")
            else:
                if target_type not in ('int', 'real') or value_type not in ('int', 'real'):
                    self.error(node, f"operador composto '{node.op}' requer operandos numericos.")

        self.check_type_compatibility(node.value, target_type, value_type, is_assignment=True)
        return target_type

    def visit_BlockNode(self, node):
        self.current_scope = SymbolTable(parent=self.current_scope)
        for stmt in node.statements:
            self.analyze(stmt)
        self.current_scope = self.current_scope.parent
        return None

    def visit_IfNode(self, node):
        cond_type = self.analyze(node.condition)
        if cond_type != 'bool' and cond_type != self.INVALID:
            self.error(node.condition, f"a condicao do 'if' deve ser do tipo 'bool', mas obteve '{cond_type}'.")
        self.analyze(node.then_branch)
        if node.else_branch:
            self.analyze(node.else_branch)
        return None

    def visit_WhileNode(self, node):
        cond_type = self.analyze(node.condition)
        if cond_type != 'bool' and cond_type != self.INVALID:
            self.error(node.condition, f"a condicao do 'while' deve ser do tipo 'bool', mas obteve '{cond_type}'.")
        self.in_loop += 1
        self.analyze(node.body)
        self.in_loop -= 1
        return None

    def visit_ForNode(self, node):
        self.current_scope = SymbolTable(parent=self.current_scope)
        if node.init:
            self.analyze(node.init)
        if node.condition:
            cond_type = self.analyze(node.condition)
            if cond_type != 'bool' and cond_type != self.INVALID:
                self.error(node.condition, f"a condicao do 'for' deve ser do tipo 'bool', mas obteve '{cond_type}'.")
        if node.update:
            self.analyze(node.update)

        self.in_loop += 1
        self.analyze(node.body)
        self.in_loop -= 1
        self.current_scope = self.current_scope.parent
        return None

    def visit_BreakNode(self, node):
        if self.in_loop <= 0:
            self.error(node, "comando 'break' deve ser utilizado apenas dentro de laços de repeticao ('while' ou 'for').")
        return None

    def has_return_node(self, node):
        """Varre recursivamente o nó/bloco da AST para verificar se existe algum ReturnNode."""
        if isinstance(node, ReturnNode):
            return True
        if isinstance(node, list):
            return any(self.has_return_node(item) for item in node)
        if hasattr(node, '__dict__'):
            for value in node.__dict__.values():
                if isinstance(value, list):
                    if any(self.has_return_node(item) for item in value):
                        return True
                elif self.has_return_node(value):
                    return True
        return False

    def visit_FunctionNode(self, node):
        if self.current_scope != self.global_scope:
            self.error(node, "declaracao de funcoes aninhadas nao e permitida.")
            return None  # Evita corrupção de escopo

        # Validar assinatura da função main se for global
        if node.name == 'main' and not self.current_class:
            if node.return_type != 'void':
                self.error(node, "a funcao 'main' deve ser do tipo 'void'.")
            if len(node.params) > 0:
                self.error(node, "a funcao 'main' nao deve possuir parametros.")

        ret_dim = getattr(node, 'return_dimension', None)
        if ret_dim is not None:
            self.error(node, f"funcao '{node.name}' nao pode retornar vetor. O tipo de retorno de funcoes ou metodos nao pode ser vetor.")

        # Registrar símbolo da função/método
        ret_dim = getattr(node, 'return_dimension', None)
        effective_return = node.return_type
        if ret_dim is not None:
            num_ret_dims = len(ret_dim) if isinstance(ret_dim, list) else 1
            effective_return = node.return_type + ("[]" * num_ret_dims)
        func_sym = Symbol(
            name=node.name,
            type_name=node.return_type,
            is_function=True,
            params=node.params,
            return_type=effective_return,
            dimension=ret_dim
        )

        if self.current_class:
            func_sym.is_method = True
            if node.name in self.current_class.methods:
                self.error(node, f"redeclaracao do metodo '{node.name}' na classe '{self.current_class.name}'.")
            self.current_class.methods[node.name] = func_sym
        else:
            if self.global_scope.lookup_local(node.name):
                self.error(node, f"redeclaracao da funcao '{node.name}'.")
            self.global_scope.define(node.name, func_sym)

        self.current_function = func_sym
        self.current_scope = SymbolTable(parent=self.global_scope)

        # Tratar 'this' implicito se for método de classe
        if self.current_class:
            self.current_scope.define('this', Symbol(name='this', type_name=self.current_class.name))

        # Registrar parâmetros
        for param in node.params:
            p_type, p_name = param[0], param[1]
            p_dim = param[2] if len(param) > 2 else None
            if self.current_scope.lookup_local(p_name):
                self.error(node, f"parametro '{p_name}' duplicado na funcao '{node.name}'.")
            if p_type not in ('int', 'real', 'str', 'bool'):
                class_sym = self.global_scope.lookup(p_type)
                if not class_sym or not class_sym.is_class:
                    self.error(node, f"tipo de parametro '{p_type}' nao definido.")
            self.current_scope.define(p_name, Symbol(name=p_name, type_name=p_type, dimension=p_dim))

        self.analyze(node.body)

        # Verificar se a função não-void possui algum retorno no corpo
        if node.return_type != 'void' and not self.has_return_node(node.body):
            self.error(node, f"funcao '{node.name}' espera retornar '{node.return_type}', mas nao possui comando 'return'.")

        self.current_scope = self.global_scope
        self.current_function = None
        return None

    def visit_ReturnNode(self, node):
        if not self.current_function:
            self.error(node, "comando 'return' deve ser utilizado apenas dentro de funcoes ou metodos.")
            if node.expression:
                self.analyze(node.expression)
            return None

        expected_type = self.current_function.return_type

        if node.expression:
            if expected_type == 'void':
                self.error(node, "funcoes do tipo 'void' nao devem retornar expressoes.")
                self.analyze(node.expression)
                return None
            got_type = self.analyze(node.expression)
            if got_type != self.INVALID:
                self.check_type_compatibility(node.expression, expected_type, got_type)
        else:
            if expected_type != 'void':
                self.error(node, f"retorno vazio invalido. Funcao espera retornar '{expected_type}'.")
        return None

    # --- Visitores de Classes ---

    def visit_ClassDeclarationNode(self, node):
        if self.current_scope != self.global_scope:
            self.error(node, "declaracao de classes aninhadas nao e permitida.")
            return None  # Evita corrupção de escopo

        if self.global_scope.lookup_local(node.name):
            self.error(node, f"redeclaracao da classe '{node.name}'.")

        class_sym = Symbol(
            name=node.name,
            type_name=node.name,
            is_class=True
        )
        self.global_scope.define(node.name, class_sym)
        self.current_class = class_sym

        # 1. Atributos da Classe
        for attr in node.attributes:
            self.analyze(attr)

        # 2. Construtor da Classe
        if not node.constructor:
            self.error(node, f"a classe '{node.name}' deve obrigatoriamente definir um construtor.")
            # Sem construtor, pula para métodos
            for method in node.methods:
                self.analyze(method)
            self.current_class = None
            return None

        if node.constructor.class_name != node.name:
            self.error(node.constructor, f"nome do construtor '{node.constructor.class_name}' deve coincidir com o nome da classe '{node.name}'.")

        constructor_sym = Symbol(
            name="constructor",
            type_name="void",
            is_function=True,
            params=node.constructor.params,
            return_type="void"
        )
        class_sym.constructor = constructor_sym

        self.current_function = constructor_sym
        self.current_scope = SymbolTable(parent=self.global_scope)
        self.current_scope.define('this', Symbol(name='this', type_name=node.name))

        for param in node.constructor.params:
            p_type, p_name = param[0], param[1]
            p_dim = param[2] if len(param) > 2 else None
            if self.current_scope.lookup_local(p_name):
                self.error(node.constructor, f"parametro '{p_name}' duplicado no construtor.")
            self.current_scope.define(p_name, Symbol(name=p_name, type_name=p_type, dimension=p_dim))

        self.analyze(node.constructor.body)

        self.current_scope = self.global_scope
        self.current_function = None

        # 3. Métodos da Classe
        for method in node.methods:
            self.analyze(method)

        self.current_class = None
        return None

    def visit_ClassConstructorNode(self, node):
        pass

    # --- Visitores de Expressões (Retornam Tipos) ---

    def visit_CallNode(self, node):
        func_sym = None

        if isinstance(node.callee, IdentifierNode):
            sym = self.current_scope.lookup(node.callee.name)
            if not sym or not sym.is_function:
                self.error(node, f"funcao '{node.callee.name}' nao declarada.")
            else:
                func_sym = sym
        elif isinstance(node.callee, AttributeAccessNode):
            obj_type = self.analyze(node.callee.object_expr)
            if obj_type == self.INVALID:
                pass  # Não emitir erros em cascata
            else:
                class_sym = self.global_scope.lookup(obj_type)
                if not class_sym or not class_sym.is_class:
                    self.error(node.callee.object_expr, f"alvo de chamada de metodo deve ser um objeto de classe, mas obteve '{obj_type}'.")
                else:
                    method_name = node.callee.attribute_name
                    func_sym = class_sym.methods.get(method_name)
                    if not func_sym:
                        self.error(node.callee, f"metodo '{method_name}' nao encontrado na classe '{obj_type}'.")
        else:
            self.error(node, "alvo de chamada invalido.")

        # Se não conseguiu resolver a função, analisa os argumentos mas retorna invalid
        if not func_sym:
            for arg in node.arguments:
                self.analyze(arg)
            return self.INVALID

        if len(node.arguments) != len(func_sym.params):
            self.error(node, f"numero incorreto de argumentos para a chamada de '{func_sym.name}'. Esperava {len(func_sym.params)}, mas obteve {len(node.arguments)}.")
            for arg in node.arguments:
                self.analyze(arg)
            return func_sym.return_type if func_sym.return_type else self.INVALID

        for i, arg in enumerate(node.arguments):
            param = func_sym.params[i]
            expected_type = param[0]
            if len(param) > 2 and param[2] is not None:
                p_dim = param[2]
                nd = len(p_dim) if isinstance(p_dim, list) else 1
                expected_type = expected_type + ("[]" * nd)
            got_type = self.analyze(arg)
            self.check_type_compatibility(arg, expected_type, got_type)

            if len(param) > 2 and param[2] is not None and got_type != self.INVALID:
                expected_dim = param[2]
                got_dim = self.get_expression_dimension(arg)
                if got_dim != expected_dim:
                    self.error(arg, f"tamanho do vetor incompativel: esperado '{expected_dim}', mas obteve '{got_dim}'.")

        return func_sym.return_type

    def visit_BinaryOpNode(self, node):
        left_type = self.analyze(node.left)
        right_type = self.analyze(node.right)
        op = node.op

        if left_type == self.INVALID or right_type == self.INVALID:
            return self.INVALID

        if left_type.endswith('[]') or right_type.endswith('[]'):
            self.error(node, f"operador '{op}' nao e suportado para vetores.")
            return self.INVALID

        if op in ('&&', '||'):
            if left_type != 'bool' or right_type != 'bool':
                self.error(node, f"operando do operador '{op}' deve ser do tipo 'bool'.")
            return 'bool'

        if op in ('==', '!='):
            if left_type in ('int', 'real') and right_type in ('int', 'real'):
                return 'bool'
            if left_type == right_type:
                return 'bool'
            # Validação com null
            if (left_type not in ('int', 'real', 'str', 'bool', 'void') and right_type == 'null') or \
               (right_type not in ('int', 'real', 'str', 'bool', 'void') and left_type == 'null'):
                return 'bool'
            self.error(node, f"comparacao invalida entre tipos '{left_type}' e '{right_type}'.")
            return self.INVALID

        if op in ('>', '>=', '<', '<='):
            if left_type in ('int', 'real') and right_type in ('int', 'real'):
                return 'bool'
            if left_type == 'str' and right_type == 'str':
                return 'bool'
            if left_type == 'bool' and right_type == 'bool':
                return 'bool'
            self.error(node, f"operador '{op}' invalido para tipos '{left_type}' e '{right_type}'.")
            return self.INVALID

        if op in ('+', '-', '*', '/', '%', '**'):
            if op in ('%', '**'):
                if left_type != 'int' or right_type != 'int':
                    self.error(node, f"operador '{op}' requer operandos do tipo 'int'.")
                return 'int'

            if op == '+':
                if left_type == 'str' or right_type == 'str':
                    simple_types = ('int', 'real', 'bool', 'str')
                    if left_type not in simple_types or right_type not in simple_types:
                        self.error(node, "operador '+' de concatenacao nao suporta tipos complexos.")
                    return 'str'

            if left_type in ('int', 'real') and right_type in ('int', 'real'):
                if left_type == 'real' or right_type == 'real':
                    return 'real'
                return 'int'

            self.error(node, f"operador '{op}' invalido para tipos '{left_type}' e '{right_type}'.")
            return self.INVALID

        return self.INVALID

    def visit_UnaryOpNode(self, node):
        expr_type = self.analyze(node.expression)
        op = node.op

        if expr_type == self.INVALID:
            return self.INVALID

        if expr_type.endswith('[]'):
            self.error(node, f"operador '{op}' nao e suportado para vetores.")
            return self.INVALID

        if op == '!':
            if expr_type != 'bool':
                self.error(node, "operador '!' requer operando do tipo 'bool'.")
            return 'bool'

        if op in ('+', '-'):
            if expr_type not in ('int', 'real'):
                self.error(node, f"operador '{op}' unario requer operando numerico.")
                return self.INVALID
            return expr_type

        if op in ('++', '--'):
            if expr_type not in ('int', 'real'):
                self.error(node, f"operador '{op}' requer operando numerico.")
                return self.INVALID
            if self.is_constant_target(node.expression):
                self.error(node, f"operador '{op}' nao pode ser aplicado a um alvo constante.")
            return expr_type

        return self.INVALID

    def visit_ArrayAccessNode(self, node):
        array_type = self.analyze(node.array_expr)
        index_type = self.analyze(node.index_expr)

        if array_type == self.INVALID or index_type == self.INVALID:
            return self.INVALID

        if index_type != 'int':
            self.error(node.index_expr, f"indice do vetor deve ser do tipo 'int', mas obteve '{index_type}'.")

        if not array_type.endswith('[]'):
            self.error(node.index_expr, f"tentativa de indexar um valor do tipo '{array_type}' que nao e um vetor.")
            return self.INVALID

        # Validação estática de limites do vetor (out of bounds)
        if isinstance(node.index_expr, NumberNode) and not node.index_expr.is_real:
            index_value = node.index_expr.value
            array_dim = self.get_expression_dimension(node.array_expr)
            if array_dim is not None:
                size = array_dim[0] if isinstance(array_dim, list) else array_dim
                if isinstance(size, int):
                    if index_value < 0 or index_value >= size:
                        self.error(node.index_expr, f"indice {index_value} fora dos limites para vetor de tamanho {size}.")

        return array_type[:-2]

    def visit_ArrayLiteralNode(self, node):
        if not node.expressions:
            return 'void[]'
        elem_types = [self.analyze(expr) for expr in node.expressions]
        # Se qualquer elemento é invalid, o literal inteiro é invalid
        if any(t == self.INVALID for t in elem_types):
            return self.INVALID
        base_type = elem_types[0]
        for i, t in enumerate(elem_types):
            if t != base_type:
                if base_type == 'int' and t == 'real':
                    base_type = 'real'
                elif base_type == 'real' and t == 'int':
                    pass
                else:
                    self.error(node.expressions[i], f"tipos incompativeis no literal de vetor: '{t}' e '{base_type}'.")
        return f"{base_type}[]"

    def visit_AttributeAccessNode(self, node):
        obj_type = self.analyze(node.object_expr)
        if obj_type == self.INVALID:
            return self.INVALID

        class_sym = self.global_scope.lookup(obj_type)
        if not class_sym or not class_sym.is_class:
            self.error(node.object_expr, f"alvo de acesso de atributo deve ser um objeto de classe, mas obteve '{obj_type}'.")
            return self.INVALID

        attr_name = node.attribute_name
        attr_sym = class_sym.attributes.get(attr_name)
        if not attr_sym:
            self.error(node, f"atributo '{attr_name}' nao encontrado na classe '{obj_type}'.")
            return self.INVALID

        if attr_sym.dimension is not None:
            num_dims = len(attr_sym.dimension) if isinstance(attr_sym.dimension, list) else 1
            return attr_sym.type + ("[]" * num_dims)
        return attr_sym.type

    def visit_NewObjectNode(self, node):
        class_sym = self.global_scope.lookup(node.class_name)
        if not class_sym or not class_sym.is_class:
            self.error(node, f"classe '{node.class_name}' nao declarada.")
            for arg in node.arguments:
                self.analyze(arg)
            return self.INVALID

        constructor = class_sym.constructor
        if not constructor:
            self.error(node, f"classe '{node.class_name}' nao possui construtor definido.")
            for arg in node.arguments:
                self.analyze(arg)
            return node.class_name

        if len(node.arguments) != len(constructor.params):
            self.error(node, f"numero incorreto de argumentos para construtor de '{node.class_name}'. Esperava {len(constructor.params)}, mas obteve {len(node.arguments)}.")
            for arg in node.arguments:
                self.analyze(arg)
            return node.class_name

        for i, arg in enumerate(node.arguments):
            param = constructor.params[i]
            expected_type = param[0]
            if len(param) > 2 and param[2] is not None:
                p_dim = param[2]
                nd = len(p_dim) if isinstance(p_dim, list) else 1
                expected_type = expected_type + ("[]" * nd)
            got_type = self.analyze(arg)
            self.check_type_compatibility(arg, expected_type, got_type)

            if len(param) > 2 and param[2] is not None and got_type != self.INVALID:
                expected_dim = param[2]
                got_dim = self.get_expression_dimension(arg)
                if got_dim != expected_dim:
                    self.error(arg, f"tamanho do vetor incompativel: esperado '{expected_dim}', mas obteve '{got_dim}'.")

        return node.class_name

    def visit_ConsoleLogNode(self, node):
        for expr in node.expressions:
            t = self.analyze(expr)
            if t != self.INVALID and t not in ('int', 'real', 'bool', 'str'):
                self.error(expr, f"console.log nao pode exibir tipo complexo '{t}'.")
        return None

    def visit_InputNode(self, node):
        for target in node.targets:
            if self.is_constant_target(target):
                self.error(target, "input nao pode gravar em alvo constante.")
            t = self.analyze(target)
            if t != self.INVALID and t not in ('int', 'real', 'str'):
                self.error(target, f"input nao pode ler para tipo '{t}'. Apenas inteiros, reais e strings sao permitidos.")
        return None

    def visit_CastNode(self, node):
        expr_type = self.analyze(node.expression)
        target = node.target_type

        if expr_type == self.INVALID:
            return target

        if target == 'str':
            if expr_type not in ('int', 'real', 'bool', 'str'):
                self.error(node, f"tipo '{expr_type}' nao pode ser convertido para string.")
        elif target in ('int', 'real', 'bool'):
            if expr_type not in ('int', 'real', 'bool'):
                self.error(node, f"conversao invalida de '{expr_type}' para '{target}'.")

        return target

    # --- Visitores de Nós Folha ---

    def visit_IdentifierNode(self, node):
        sym = self.current_scope.lookup(node.name)
        if not sym:
            self.error(node, f"identificador '{node.name}' nao declarado.")
            return self.INVALID
        if sym.dimension is not None:
            num_dims = len(sym.dimension) if isinstance(sym.dimension, list) else 1
            return sym.type + ("[]" * num_dims)
        return sym.type

    def visit_NumberNode(self, node):
        return 'real' if node.is_real else 'int'

    def visit_StringNode(self, node):
        return 'str'

    def visit_BooleanNode(self, node):
        return 'bool'

    def visit_NullNode(self, node):
        return 'null'

    def get_expression_dimension(self, node):
        if isinstance(node, IdentifierNode):
            sym = self.current_scope.lookup(node.name)
            if sym:
                return sym.dimension
        elif isinstance(node, ArrayLiteralNode):
            outer_size = len(node.expressions)
            if outer_size > 0:
                inner_dim = self.get_expression_dimension(node.expressions[0])
                if inner_dim is not None:
                    if isinstance(inner_dim, list):
                        return [outer_size] + inner_dim
                    else:
                        return [outer_size, inner_dim]
            return outer_size
        elif isinstance(node, AttributeAccessNode):
            obj_type = self.analyze(node.object_expr)
            if obj_type != self.INVALID:
                class_sym = self.global_scope.lookup(obj_type)
                if class_sym and class_sym.is_class:
                    attr_sym = class_sym.attributes.get(node.attribute_name)
                    if attr_sym:
                        return attr_sym.dimension
        elif isinstance(node, ArrayAccessNode):
            parent_dim = self.get_expression_dimension(node.array_expr)
            if parent_dim is not None:
                if isinstance(parent_dim, list):
                    if len(parent_dim) > 1:
                        remaining = parent_dim[1:]
                        return remaining[0] if len(remaining) == 1 else remaining
                    else:
                        return None
                else:
                    return None
        return None
