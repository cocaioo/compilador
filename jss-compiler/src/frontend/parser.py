"""Parser da linguagem JSS.

Responsavel por validar a gramatica, construir a AST e reportar erros sintaticos.
"""

import ply.yacc as yacc
from frontend.lexer import tokens
from frontend.errors import SyntacticError
from frontend.ast_nodes import (
    ProgramNode, VarDeclarationNode, AssignmentNode, BlockNode,
    IfNode, WhileNode, ForNode, BreakNode, FunctionNode, ReturnNode,
    CallNode, BinaryOpNode, UnaryOpNode, ArrayAccessNode, ArrayLiteralNode,
    ClassDeclarationNode, ClassConstructorNode, AttributeAccessNode,
    NewObjectNode, ConsoleLogNode, InputNode, CastNode, NumberNode,
    StringNode, BooleanNode, NullNode, IdentifierNode
)

# Definição de precedência baseada na tabela da especificação
precedence = (
    ('right', 'ASSIGN', 'PLUS_ASSIGN', 'MINUS_ASSIGN', 'TIMES_ASSIGN', 'DIVIDE_ASSIGN', 'MOD_ASSIGN'),
    ('left', 'OR'),
    ('left', 'AND'),
    ('left', 'EQ', 'NE'),
    ('left', 'GT', 'GE', 'LT', 'LE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE', 'MOD'),
    ('right', 'POWER'),
    ('right', 'NOT', 'UPLUS', 'UMINUS', 'INCREMENT', 'DECREMENT'),
    ('left', 'LBRACKET', 'RBRACKET', 'LPAREN', 'RPAREN', 'DOT'),
    ('nonassoc', 'IFX'),
    ('nonassoc', 'ELSE'),
)

# Regra inicial do compilador
def p_program(p):
    'program : statement_list'
    p[0] = ProgramNode(p[1])

def p_statement_list(p):
    '''statement_list : statement
                      | statement_list statement'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

# Comandos válidos na linguagem
def p_statement(p):
    '''statement : var_declaration
                 | if_statement
                 | while_statement
                 | for_statement
                 | break_statement
                 | block
                 | function_declaration
                 | return_statement
                 | class_declaration
                 | console_log_statement
                 | input_statement
                 | expression_statement'''
    p[0] = p[1]

# Tipos primitivos e derivados
def p_type(p):
    '''type : INT_TYPE
            | REAL_TYPE
            | STR_TYPE
            | BOOL_TYPE
            | ID'''
    p[0] = p[1]

# Tipo de retorno de função (pode ser void)
def p_return_type(p):
    '''return_type : type
                   | VOID_TYPE'''
    p[0] = p[1]

# Declaração de variáveis e vetores
def p_var_declaration(p):
    '''var_declaration : LET type ID SEMICOLON
                       | LET type ID ASSIGN expression SEMICOLON
                       | CONST type ID ASSIGN expression SEMICOLON
                       | LET type LBRACKET INT_LITERAL RBRACKET ID SEMICOLON
                       | LET type LBRACKET INT_LITERAL RBRACKET ID ASSIGN expression SEMICOLON
                       | CONST type LBRACKET INT_LITERAL RBRACKET ID ASSIGN expression SEMICOLON'''
    is_const = (p[1] == 'const')
    if len(p) == 5:
        # LET type ID SEMICOLON
        p[0] = VarDeclarationNode(var_type=p[2], name=p[3], value=None, is_const=is_const, dimension=None)
    elif len(p) == 7:
        # LET/CONST type ID ASSIGN expression SEMICOLON
        p[0] = VarDeclarationNode(var_type=p[2], name=p[3], value=p[5], is_const=is_const, dimension=None)
    elif len(p) == 8:
        # LET type LBRACKET INT_LITERAL RBRACKET ID SEMICOLON
        p[0] = VarDeclarationNode(var_type=p[2], name=p[6], value=None, is_const=is_const, dimension=p[4])
    elif len(p) == 10:
        # LET/CONST type LBRACKET INT_LITERAL RBRACKET ID ASSIGN expression SEMICOLON
        p[0] = VarDeclarationNode(var_type=p[2], name=p[6], value=p[8], is_const=is_const, dimension=p[4])

# Alvos de atribuição (IDs, vetores, atributos de classes)
# Operadores de atribuição
def p_assignment_op(p):
    '''assignment_op : ASSIGN
                     | PLUS_ASSIGN
                     | MINUS_ASSIGN
                     | TIMES_ASSIGN
                     | DIVIDE_ASSIGN
                     | MOD_ASSIGN'''
    p[0] = p[1]

# Expressões
def p_expression_assignment(p):
    'expression : expression assignment_op expression'
    if not isinstance(p[1], (IdentifierNode, ArrayAccessNode, AttributeAccessNode)):
        raise SyntacticError(f"Erro sintatico na linha {p.lineno(1)}: atribuicao para alvo invalido.")
    p[0] = AssignmentNode(target=p[1], value=p[3], op=p[2])

def p_expression_binop(p):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression
                  | expression MOD expression
                  | expression POWER expression
                  | expression EQ expression
                  | expression NE expression
                  | expression GT expression
                  | expression GE expression
                  | expression LT expression
                  | expression LE expression
                  | expression AND expression
                  | expression OR expression'''
    p[0] = BinaryOpNode(left=p[1], op=p[2], right=p[3])

def p_expression_unary(p):
    '''expression : NOT expression
                  | PLUS expression %prec UPLUS
                  | MINUS expression %prec UMINUS
                  | INCREMENT expression
                  | DECREMENT expression'''
    if p[1] in ('++', '--'):
        if not isinstance(p[2], (IdentifierNode, ArrayAccessNode, AttributeAccessNode)):
            raise SyntacticError(f"Erro sintatico na linha {p.lineno(1)}: operador {p[1]} requer um alvo valido.")
    p[0] = UnaryOpNode(op=p[1], expression=p[2])

def p_expression_array_access(p):
    'expression : expression LBRACKET expression RBRACKET'
    p[0] = ArrayAccessNode(array_expr=p[1], index_expr=p[3])

def p_expression_attribute_access(p):
    '''expression : expression DOT ID
                  | THIS DOT ID'''
    obj = IdentifierNode("this") if p[1] == 'this' else p[1]
    p[0] = AttributeAccessNode(object_expr=obj, attribute_name=p[3])

def p_expression_id(p):
    'expression : ID'
    p[0] = IdentifierNode(p[1])

def p_expression_number(p):
    '''expression : INT_LITERAL
                  | REAL_LITERAL'''
    is_real = isinstance(p[1], float)
    p[0] = NumberNode(p[1], is_real=is_real)

def p_expression_string(p):
    'expression : STRING_LITERAL'
    p[0] = StringNode(p[1])

def p_expression_boolean(p):
    '''expression : TRUE
                  | FALSE'''
    val = True if p[1] == 'true' else False
    p[0] = BooleanNode(val)

def p_expression_null(p):
    'expression : NULL'
    p[0] = NullNode()

def p_expression_group(p):
    'expression : LPAREN expression RPAREN'
    p[0] = p[2]

def p_expression_new(p):
    'expression : NEW ID LPAREN argument_list RPAREN'
    p[0] = NewObjectNode(class_name=p[2], arguments=p[4])

def p_expression_call(p):
    'expression : expression LPAREN argument_list RPAREN'
    p[0] = CallNode(callee=p[1], arguments=p[3])

def p_expression_array_literal(p):
    'expression : LBRACKET argument_list RBRACKET'
    p[0] = ArrayLiteralNode(p[2])

# Conversões (Casting)
def p_expression_cast(p):
    '''expression : INT_TYPE LPAREN expression RPAREN
                  | REAL_TYPE LPAREN expression RPAREN
                  | BOOL_TYPE LPAREN expression RPAREN
                  | STR_TYPE LPAREN expression RPAREN'''
    p[0] = CastNode(target_type=p[1], expression=p[3])

# Listas de argumentos para chamadas
def p_argument_list(p):
    '''argument_list : empty
                     | argument_list_nonempty'''
    p[0] = p[1] if p[1] is not None else []

def p_argument_list_nonempty(p):
    '''argument_list_nonempty : expression
                              | argument_list_nonempty COMMA expression'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]

# Estruturas de controle de fluxo
def p_if_statement(p):
    '''if_statement : IF LPAREN expression RPAREN statement %prec IFX
                    | IF LPAREN expression RPAREN statement ELSE statement'''
    if len(p) == 6:
        p[0] = IfNode(condition=p[3], then_branch=p[5])
    else:
        p[0] = IfNode(condition=p[3], then_branch=p[5], else_branch=p[7])

def p_while_statement(p):
    'while_statement : WHILE LPAREN expression RPAREN statement'
    p[0] = WhileNode(condition=p[3], body=p[5])

def p_expression_opt(p):
    '''expression_opt : empty
                      | expression'''
    p[0] = p[1]

def p_for_statement(p):
    'for_statement : FOR LPAREN expression_opt SEMICOLON expression_opt SEMICOLON expression_opt RPAREN statement'
    p[0] = ForNode(init=p[3], condition=p[5], update=p[7], body=p[9])

def p_break_statement(p):
    'break_statement : BREAK SEMICOLON'
    p[0] = BreakNode()

def p_block(p):
    '''block : LBRACE statement_list RBRACE
             | LBRACE RBRACE'''
    if len(p) == 4:
        p[0] = BlockNode(p[2])
    else:
        p[0] = BlockNode([])

# Declaração de funções
def p_function_declaration(p):
    'function_declaration : FUNCTION return_type ID LPAREN param_list RPAREN block'
    p[0] = FunctionNode(return_type=p[2], name=p[3], params=p[5], body=p[7])

def p_param_list(p):
    '''param_list : empty
                  | param_list_nonempty'''
    p[0] = p[1] if p[1] is not None else []

def p_param_list_nonempty(p):
    '''param_list_nonempty : param
                           | param_list_nonempty COMMA param'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]

def p_param(p):
    'param : type ID'
    p[0] = (p[1], p[2])

def p_return_statement(p):
    '''return_statement : RETURN expression SEMICOLON
                        | RETURN SEMICOLON'''
    if len(p) == 4:
        p[0] = ReturnNode(expression=p[2])
    else:
        p[0] = ReturnNode(expression=None)

# Declaração de Classes
def p_class_declaration(p):
    'class_declaration : CLASS ID LBRACE class_attribute_list class_constructor class_method_list RBRACE'
    p[0] = ClassDeclarationNode(name=p[2], attributes=p[4], constructor=p[5], methods=p[6])

def p_class_attribute_list(p):
    '''class_attribute_list : empty
                            | class_attribute_list class_attribute'''
    if len(p) == 2:
        p[0] = []
    else:
        p[0] = p[1] + [p[2]]

def p_class_attribute(p):
    'class_attribute : type ID SEMICOLON'
    p[0] = VarDeclarationNode(var_type=p[1], name=p[2], value=None, is_const=False)

def p_class_constructor(p):
    'class_constructor : ID CONSTRUCTOR LPAREN param_list RPAREN LBRACE constructor_body RBRACE'
    p[0] = ClassConstructorNode(class_name=p[1], params=p[4], body=BlockNode(p[7]))

def p_constructor_body(p):
    '''constructor_body : empty
                        | constructor_body constructor_assignment'''
    if len(p) == 2:
        p[0] = []
    else:
        p[0] = p[1] + [p[2]]

def p_constructor_assignment(p):
    'constructor_assignment : THIS DOT ID ASSIGN expression SEMICOLON'
    target = AttributeAccessNode(object_expr=IdentifierNode("this"), attribute_name=p[3])
    p[0] = AssignmentNode(target=target, value=p[5])

def p_class_method_list(p):
    '''class_method_list : empty
                         | class_method_list class_method'''
    if len(p) == 2:
        p[0] = []
    else:
        p[0] = p[1] + [p[2]]

def p_class_method(p):
    'class_method : return_type ID LPAREN param_list RPAREN block'
    p[0] = FunctionNode(return_type=p[1], name=p[2], params=p[4], body=p[6])

# Comandos de Funções Nativas
def p_console_log_statement(p):
    'console_log_statement : CONSOLE_LOG LPAREN argument_list RPAREN SEMICOLON'
    p[0] = ConsoleLogNode(expressions=p[3])

def p_input_statement(p):
    'input_statement : INPUT LPAREN argument_list RPAREN SEMICOLON'
    for arg in p[3]:
        if not isinstance(arg, (IdentifierNode, ArrayAccessNode, AttributeAccessNode)):
            raise SyntacticError(f"Erro sintatico na linha {p.lineno(1)}: input requer alvos validos.")
    p[0] = InputNode(targets=p[3])

def p_expression_statement(p):
    'expression_statement : expression SEMICOLON'
    p[0] = p[1]

# Regras auxiliares
def p_empty(p):
    'empty :'
    pass

# Tratamento de erro sintático
def p_error(p):
    if p:
        raise SyntacticError(f"Erro sintatico na linha {p.lineno}: token inesperado '{p.value}'.")
    else:
        raise SyntacticError("Erro sintatico na linha final: fim de arquivo inesperado.")

# Inicialização do parser do PLY
parser = yacc.yacc()
