"""Nos da AST da linguagem JSS.

Responsavel por representar a estrutura abstrata do programa apos o parsing.
"""

class ASTNode:
    """Classe base para todos os nos da AST."""
    def print_tree(self, indent=0):
        raise NotImplementedError()

    def get_indent(self, indent):
        return "| " * indent


class ProgramNode(ASTNode):
    """No raiz que contem a lista de instrucoes do programa."""
    def __init__(self, statements):
        self.statements = statements

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + "ProgramNode:\n"
        for stmt in self.statements:
            result += stmt.print_tree(indent + 1)
        return result


class VarDeclarationNode(ASTNode):
    """Declaracao de variavel tipada (let int x = ... ou const str [3] nomes = ...)."""
    def __init__(self, var_type, name, value=None, is_const=False, dimension=None):
        self.var_type = var_type
        self.name = name
        self.value = value
        self.is_const = is_const
        self.dimension = dimension  # None ou int/ASTNode para a dimensão do vetor

    def print_tree(self, indent=0):
        type_str = "CONST" if self.is_const else "LET"
        if isinstance(self.dimension, list):
            dim_str = "".join([f"[{d}]" for d in self.dimension])
        elif self.dimension is not None:
            dim_str = f"[{self.dimension}]"
        else:
            dim_str = ""
        result = self.get_indent(indent) + f"VarDeclarationNode ({type_str} {self.var_type}{dim_str} {self.name}):\n"
        if self.value:
            result += self.value.print_tree(indent + 1)
        else:
            result += self.get_indent(indent + 1) + "None\n"
        return result


class AssignmentNode(ASTNode):
    """Atribuicao simples ou composta (x = ..., x += ...)."""
    def __init__(self, target, value, op='='):
        self.target = target  # ASTNode (IdentifierNode, ArrayAccessNode ou AttributeAccessNode)
        self.value = value    # ASTNode
        self.op = op          # '=', '+=', '-=', '*=', '/=', '%='

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + f"AssignmentNode (Operator: '{self.op}'):\n"
        result += self.get_indent(indent + 1) + "Target:\n"
        result += self.target.print_tree(indent + 2)
        result += self.get_indent(indent + 1) + "Value:\n"
        result += self.value.print_tree(indent + 2)
        return result


class BlockNode(ASTNode):
    """Bloco de instrucoes delimitado por chaves { ... }."""
    def __init__(self, statements):
        self.statements = statements

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + "BlockNode:\n"
        for stmt in self.statements:
            result += stmt.print_tree(indent + 1)
        return result


class IfNode(ASTNode):
    """Estrutura condicional (if / else if / else)."""
    def __init__(self, condition, then_branch, else_branch=None):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + "IfNode:\n"
        result += self.get_indent(indent + 1) + "Condition:\n"
        result += self.condition.print_tree(indent + 2)
        result += self.get_indent(indent + 1) + "Then:\n"
        result += self.then_branch.print_tree(indent + 2)
        if self.else_branch:
            result += self.get_indent(indent + 1) + "Else:\n"
            result += self.else_branch.print_tree(indent + 2)
        return result


class WhileNode(ASTNode):
    """Estrutura de repeticao (while)."""
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + "WhileNode:\n"
        result += self.get_indent(indent + 1) + "Condition:\n"
        result += self.condition.print_tree(indent + 2)
        result += self.get_indent(indent + 1) + "Body:\n"
        result += self.body.print_tree(indent + 2)
        return result


class ForNode(ASTNode):
    """Estrutura de repeticao (for)."""
    def __init__(self, init, condition, update, body):
        self.init = init            # ASTNode ou None
        self.condition = condition  # ASTNode ou None
        self.update = update        # ASTNode ou None
        self.body = body            # ASTNode

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + "ForNode:\n"
        if self.init:
            result += self.get_indent(indent + 1) + "Init:\n"
            result += self.init.print_tree(indent + 2)
        if self.condition:
            result += self.get_indent(indent + 1) + "Condition:\n"
            result += self.condition.print_tree(indent + 2)
        if self.update:
            result += self.get_indent(indent + 1) + "Update:\n"
            result += self.update.print_tree(indent + 2)
        result += self.get_indent(indent + 1) + "Body:\n"
        result += self.body.print_tree(indent + 2)
        return result


class BreakNode(ASTNode):
    """Comando break para interrupcao de laços."""
    def print_tree(self, indent=0):
        return self.get_indent(indent) + "BreakNode\n"


class FunctionNode(ASTNode):
    """Declaracao de funcao (function <tipo> nome(params) { ... })."""
    def __init__(self, return_type, name, params, body):
        self.return_type = return_type
        self.name = name
        self.params = params  # Lista de tuplas (tipo, nome)
        self.body = body

    def print_tree(self, indent=0):
        params_str = ", ".join([f"{p[0]} {p[1]}" for p in self.params])
        result = self.get_indent(indent) + f"FunctionNode ({self.return_type} {self.name}({params_str})):\n"
        result += self.body.print_tree(indent + 1)
        return result


class ReturnNode(ASTNode):
    """Instrucao de retorno (return ...)."""
    def __init__(self, expression=None):
        self.expression = expression

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + "ReturnNode:\n"
        if self.expression:
            result += self.expression.print_tree(indent + 1)
        else:
            result += self.get_indent(indent + 1) + "None\n"
        return result


class CallNode(ASTNode):
    """Chamada de funcao ou metodo."""
    def __init__(self, callee, arguments):
        self.callee = callee        # ASTNode (IdentifierNode ou AttributeAccessNode)
        self.arguments = arguments  # Lista de ASTNodes

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + "CallNode:\n"
        result += self.callee.print_tree(indent + 1)
        result += self.get_indent(indent + 1) + "Arguments:\n"
        for arg in self.arguments:
            result += arg.print_tree(indent + 2)
        return result


class BinaryOpNode(ASTNode):
    """Operacao binaria (+, -, *, /, &&, ||, ==, etc)."""
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + f"BinaryOpNode ({self.op}):\n"
        result += self.left.print_tree(indent + 1)
        result += self.right.print_tree(indent + 1)
        return result


class UnaryOpNode(ASTNode):
    """Operacao unaria (!, unario +, unario -, prefix ++, prefix --)."""
    def __init__(self, op, expression):
        self.op = op
        self.expression = expression

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + f"UnaryOpNode ({self.op}):\n"
        result += self.expression.print_tree(indent + 1)
        return result


class ArrayAccessNode(ASTNode):
    """Acesso a elemento de vetor (l2[0])."""
    def __init__(self, array_expr, index_expr):
        self.array_expr = array_expr
        self.index_expr = index_expr

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + "ArrayAccessNode:\n"
        result += self.get_indent(indent + 1) + "Array:\n"
        result += self.array_expr.print_tree(indent + 2)
        result += self.get_indent(indent + 1) + "Index:\n"
        result += self.index_expr.print_tree(indent + 2)
        return result


class ArrayLiteralNode(ASTNode):
    """Literal de vetor ([1, 2, 3])."""
    def __init__(self, expressions):
        self.expressions = expressions

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + "ArrayLiteralNode:\n"
        for expr in self.expressions:
            result += expr.print_tree(indent + 1)
        return result


class ClassDeclarationNode(ASTNode):
    """Declaracao de classe (class Ponto { ... })."""
    def __init__(self, name, attributes, constructor, methods):
        self.name = name
        self.attributes = attributes  # Lista de VarDeclarationNodes
        self.constructor = constructor  # ClassConstructorNode
        self.methods = methods          # Lista de FunctionNodes

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + f"ClassDeclarationNode ({self.name}):\n"
        result += self.get_indent(indent + 1) + "Attributes:\n"
        for attr in self.attributes:
            result += attr.print_tree(indent + 2)
        if self.constructor:
            result += self.get_indent(indent + 1) + "Constructor:\n"
            result += self.constructor.print_tree(indent + 2)
        result += self.get_indent(indent + 1) + "Methods:\n"
        for m in self.methods:
            result += m.print_tree(indent + 2)
        return result


class ClassConstructorNode(ASTNode):
    """Construtor da classe."""
    def __init__(self, class_name, params, body):
        self.class_name = class_name
        self.params = params  # Lista de tuplas (tipo, nome)
        self.body = body

    def print_tree(self, indent=0):
        params_str = ", ".join([f"{p[0]} {p[1]}" for p in self.params])
        result = self.get_indent(indent) + f"ClassConstructorNode ({self.class_name} constructor({params_str})):\n"
        result += self.body.print_tree(indent + 1)
        return result


class AttributeAccessNode(ASTNode):
    """Acesso a atributo de objeto (this.x ou p1.x)."""
    def __init__(self, object_expr, attribute_name):
        self.object_expr = object_expr
        self.attribute_name = attribute_name

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + f"AttributeAccessNode (.{self.attribute_name}):\n"
        result += self.object_expr.print_tree(indent + 1)
        return result


class NewObjectNode(ASTNode):
    """Instanciacao de classe (new Ponto(1, 2))."""
    def __init__(self, class_name, arguments):
        self.class_name = class_name
        self.arguments = arguments  # Lista de ASTNodes

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + f"NewObjectNode ({self.class_name}):\n"
        for arg in self.arguments:
            result += arg.print_tree(indent + 1)
        return result


class ConsoleLogNode(ASTNode):
    """Funcao nativa console.log(expr1, expr2, ...)."""
    def __init__(self, expressions):
        self.expressions = expressions

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + "ConsoleLogNode:\n"
        for expr in self.expressions:
            result += expr.print_tree(indent + 1)
        return result


class InputNode(ASTNode):
    """Funcao nativa input(var1, var2, ...)."""
    def __init__(self, targets):
        self.targets = targets  # Lista de ASTNodes (Identificadores, vetores, etc)

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + "InputNode:\n"
        for t in self.targets:
            result += t.print_tree(indent + 1)
        return result


class CastNode(ASTNode):
    """Conversao explicita de tipos (int(expr), real(expr), etc)."""
    def __init__(self, target_type, expression):
        self.target_type = target_type
        self.expression = expression

    def print_tree(self, indent=0):
        result = self.get_indent(indent) + f"CastNode ({self.target_type}):\n"
        result += self.expression.print_tree(indent + 1)
        return result


# Nós Folha / Terminais
class NumberNode(ASTNode):
    """Literal numerico (inteiro ou real)."""
    def __init__(self, value, is_real=False):
        self.value = value
        self.is_real = is_real

    def print_tree(self, indent=0):
        type_str = "Real" if self.is_real else "Int"
        return self.get_indent(indent) + f"NumberNode ({type_str}: {self.value})\n"


class StringNode(ASTNode):
    """Literal de texto."""
    def __init__(self, value):
        self.value = value

    def print_tree(self, indent=0):
        return self.get_indent(indent) + f"StringNode (\"{self.value}\")\n"


class BooleanNode(ASTNode):
    """Literal booleano (true ou false)."""
    def __init__(self, value):
        self.value = value  # True ou False (bool)

    def print_tree(self, indent=0):
        return self.get_indent(indent) + f"BooleanNode ({self.value})\n"


class NullNode(ASTNode):
    """Valor null."""
    def print_tree(self, indent=0):
        return self.get_indent(indent) + "NullNode (null)\n"


class IdentifierNode(ASTNode):
    """Identificador (nome de variavel, funcao, classe, etc)."""
    def __init__(self, name):
        self.name = name

    def print_tree(self, indent=0):
        return self.get_indent(indent) + f"IdentifierNode ({self.name})\n"
