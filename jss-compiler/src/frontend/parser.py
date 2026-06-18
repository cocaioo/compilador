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
def p_var_declaration_no_semicolon(p):
    '''var_declaration_no_semicolon : LET type ID
                                     | LET type ID ASSIGN expression
                                     | CONST type ID ASSIGN expression
                                     | LET type LBRACKET INT_LITERAL RBRACKET ID
                                     | LET type LBRACKET INT_LITERAL RBRACKET ID ASSIGN expression
                                     | CONST type LBRACKET INT_LITERAL RBRACKET ID ASSIGN expression'''
    is_const = (p[1] == 'const')
    if len(p) == 4:
        # LET type ID
        p[0] = VarDeclarationNode(var_type=p[2], name=p[3], value=None, is_const=is_const, dimension=None)
    elif len(p) == 6:
        # LET/CONST type ID ASSIGN expression
        p[0] = VarDeclarationNode(var_type=p[2], name=p[3], value=p[5], is_const=is_const, dimension=None)
    elif len(p) == 7:
        # LET type LBRACKET INT_LITERAL RBRACKET ID
        p[0] = VarDeclarationNode(var_type=p[2], name=p[6], value=None, is_const=is_const, dimension=p[4])
    elif len(p) == 9:
        # LET/CONST type LBRACKET INT_LITERAL RBRACKET ID ASSIGN expression
        p[0] = VarDeclarationNode(var_type=p[2], name=p[6], value=p[8], is_const=is_const, dimension=p[4])

def p_var_declaration(p):
    'var_declaration : var_declaration_no_semicolon SEMICOLON'
    p[0] = p[1]

# Expressões e atribuições
def p_expression_assignment(p):
    '''expression : expression ASSIGN expression
                  | expression PLUS_ASSIGN expression
                  | expression MINUS_ASSIGN expression
                  | expression TIMES_ASSIGN expression
                  | expression DIVIDE_ASSIGN expression
                  | expression MOD_ASSIGN expression'''
    if not isinstance(p[1], (IdentifierNode, ArrayAccessNode, AttributeAccessNode)):
        raise SyntacticError(f"Erro sintatico na linha {p.lineno(2)}: atribuicao para alvo invalido.")
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

def p_for_init(p):
    '''for_init : empty
                | var_declaration_no_semicolon
                | expression'''
    p[0] = p[1]

def p_for_statement(p):
    'for_statement : FOR LPAREN for_init SEMICOLON expression_opt SEMICOLON expression_opt RPAREN statement'
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

# Mapeamento de tokens para termos amigáveis em português
TOKEN_TRANSLATIONS = {
    'SEMICOLON': "';' (ponto e vírgula)",
    'LPAREN': "'(' (abrir parêntese)",
    'RPAREN': "')' (fechar parêntese)",
    'LBRACKET': "'[' (abrir colchete)",
    'RBRACKET': "']' (fechar colchete)",
    'LBRACE': "'{' (abrir chave)",
    'RBRACE': "'}' (fechar chave)",
    'COMMA': "',' (vírgula)",
    'DOT': "'.' (ponto)",
    'ASSIGN': "'=' (atribuição)",
    'PLUS': "'+' (soma)",
    'MINUS': "'-' (subtração)",
    'TIMES': "'*' (multiplicação)",
    'DIVIDE': "'/' (divisão)",
    'MOD': "'%' (resto)",
    'POWER': "'**' (potência)",
    'EQ': "'==' (igualdade)",
    'NE': "'!=' (diferente de)",
    'GT': "'>' (maior que)",
    'GE': "'>=' (maior ou igual a)",
    'LT': "'<' (menor que)",
    'LE': "'<=' (menor ou igual a)",
    'AND': "'&&' (E lógico)",
    'OR': "'||' (OU lógico)",
    'NOT': "'!' (negação)",
    'LET': "a palavra-chave 'let'",
    'CONST': "a palavra-chave 'const'",
    'IF': "a palavra-chave 'if'",
    'ELSE': "a palavra-chave 'else'",
    'WHILE': "a palavra-chave 'while'",
    'FOR': "a palavra-chave 'for'",
    'BREAK': "a palavra-chave 'break'",
    'FUNCTION': "a palavra-chave 'function'",
    'RETURN': "a palavra-chave 'return'",
    'CLASS': "a palavra-chave 'class'",
    'CONSTRUCTOR': "a palavra-chave 'constructor'",
    'NEW': "a palavra-chave 'new'",
    'THIS': "a palavra-chave 'this'",
    'CONSOLE_LOG': "o comando 'console.log'",
    'INPUT': "o comando 'input'",
    'INT_TYPE': "o tipo 'int'",
    'REAL_TYPE': "o tipo 'real'",
    'BOOL_TYPE': "o tipo 'bool'",
    'STR_TYPE': "o tipo 'string'",
    'VOID_TYPE': "o tipo 'void'",
    'ID': "um identificador (nome de variável, função ou classe)",
    'INT_LITERAL': "um número inteiro",
    'REAL_LITERAL': "um número real",
    'STRING_LITERAL': "um texto (string)",
    'TRUE': "o valor 'true'",
    'FALSE': "o valor 'false'",
    'NULL': "o valor 'null'",
}

# Tratamento de erro sintático
def p_error(p):
    # Obtém o estado atual da máquina de estados do yacc
    try:
        state = parser.statestack[-1]
        raw_expected = list(parser.action[state].keys())
    except (NameError, AttributeError, IndexError):
        raw_expected = []

    # Determinar a linha
    if p:
        line_num = p.lineno
    else:
        # Se for fim do arquivo, tenta resgatar a última linha válida do lexer ou da pilha
        line_num = "final"
        try:
            if len(parser.symstack) > 1:
                last_sym = parser.symstack[-1]
                if hasattr(last_sym, 'lineno'):
                    line_num = last_sym.lineno
                elif hasattr(last_sym, 'lexer') and hasattr(last_sym.lexer, 'lineno'):
                    line_num = last_sym.lexer.lineno
        except Exception:
            pass

    if p:
        unexpected = f"'{p.value}'"
        token_type = p.type
    else:
        unexpected = "fim de arquivo inesperado"
        token_type = "EOF"

    # Verificações de contexto avançadas para mensagens extremamente precisas
    try:
        sym_types = [getattr(sym, 'type', sym) for sym in parser.symstack] if hasattr(parser, 'symstack') else []
    except Exception:
        sym_types = []

    # 1. Declaração de variável estilo C/Java sem let/const (ex: int x = 10;)
    if token_type == 'ID' and len(sym_types) >= 2 and 'CLASS' not in sym_types:
        last_sym_type = sym_types[-1]
        if last_sym_type in ('INT_TYPE', 'REAL_TYPE', 'STR_TYPE', 'BOOL_TYPE', 'ID'):
            try:
                last_sym_val = parser.symstack[-1].value if last_sym_type == 'ID' else last_sym_type.lower().replace('_type', '')
            except Exception:
                last_sym_val = last_sym_type
            raise SyntacticError(
                f"Erro sintatico na linha {line_num}: token inesperado '{p.value}'. "
                f"Para declarar uma variável, utilize a palavra-chave 'let' ou 'const' (ex: 'let {last_sym_val} {p.value};')."
            )



    # 3. Vetor declarado com colchetes no lugar errado (ex: let int x[10];)
    if token_type == 'LBRACKET' and len(sym_types) >= 4:
        if sym_types[-3:] == ['LET', 'type', 'ID']:
            try:
                type_name = getattr(parser.symstack[-2], 'value', 'int')
                id_name = getattr(parser.symstack[-1], 'value', 'vetor')
            except Exception:
                type_name = "int"
                id_name = "vetor"
            raise SyntacticError(
                f"Erro sintatico na linha {line_num}: token inesperado '['. "
                f"Em JSS, os colchetes de declaração de vetores devem vir antes do nome da variável (ex: 'let {type_name}[10] {id_name};')."
            )

    # 4. Método/função declarado antes do construtor na classe
    if 'CLASS' in sym_types and 'class_constructor' not in sym_types:
        # Caso A: Falha ao encontrar '(' após 'tipo nome' (ex: class A { int area() ... })
        is_method_signature = (
            token_type == 'LPAREN' and 
            len(sym_types) >= 2 and 
            (sym_types[-2:] == ['type', 'ID'] or sym_types[-2:] == ['ID', 'ID'])
        )
        # Caso B: Falha ao encontrar tipo de retorno inválido para atributo mas válido para método (ex: class A { void area() ... })
        is_void_method = (
            token_type in ('VOID_TYPE', 'FUNCTION') and
            len(sym_types) >= 1 and
            sym_types[-1] in ('class_attribute_list', 'LBRACE')
        )
        if is_method_signature or is_void_method:
            raise SyntacticError(
                f"Erro sintatico na linha {line_num}: token inesperado {unexpected}. "
                "Toda classe em JSS deve obrigatoriamente definir um construtor antes de declarar seus métodos."
            )

    # 5. Falta de tipo na declaração de variável (ex: let x = 10; ou let x;)
    if token_type in ('ASSIGN', 'SEMICOLON', 'PLUS_ASSIGN', 'MINUS_ASSIGN', 'TIMES_ASSIGN', 'DIVIDE_ASSIGN', 'MOD_ASSIGN') and len(sym_types) >= 2:
        if sym_types[-2:] in (['LET', 'ID'], ['CONST', 'ID']):
            var_name = getattr(parser.symstack[-1], 'value', 'x')
            keyword = sym_types[-2].lower()
            raise SyntacticError(
                f"Erro sintatico na linha {line_num}: token inesperado '{p.value}'. "
                f"Ausência de tipo na declaração da variável. Em JSS, o tipo deve ser explicitado (ex: '{keyword} int {var_name} = ...' ou '{keyword} int {var_name};')."
            )

    # 6. Ordem de declaração invertida (ex: int let x = 10;)
    if token_type in ('LET', 'CONST') and len(sym_types) >= 1 and 'CLASS' not in sym_types:
        last_sym_type = sym_types[-1]
        if last_sym_type in ('INT_TYPE', 'REAL_TYPE', 'STR_TYPE', 'BOOL_TYPE', 'ID'):
            try:
                last_sym_val = parser.symstack[-1].value if last_sym_type == 'ID' else last_sym_type.lower().replace('_type', '')
            except Exception:
                last_sym_val = last_sym_type
            raise SyntacticError(
                f"Erro sintatico na linha {line_num}: token inesperado '{p.value}'. "
                f"A ordem de declaração de variáveis em JSS exige a palavra-chave antes do tipo (ex: '{p.value} {last_sym_val} variavel;' em vez de '{last_sym_val} {p.value} variavel;')."
            )

    # Se tivermos a lista de tokens esperados do yacc, monta a orientação
    if raw_expected:
        clean_expected = [t for t in raw_expected if t != '$end' and not t.startswith('error')]
        
        # Tratamento especial de EOF (fim de arquivo)
        if token_type == "EOF":
            if 'SEMICOLON' in clean_expected and len(clean_expected) > 10:
                raise SyntacticError(f"Erro sintatico na linha {line_num}: fim de arquivo inesperado. Talvez esteja faltando um ';'.")
            elif 'RBRACE' in clean_expected:
                raise SyntacticError(f"Erro sintatico na linha {line_num}: fim de arquivo inesperado. Talvez esteja faltando fechar uma chave '}}'.")
            elif 'RPAREN' in clean_expected:
                raise SyntacticError(f"Erro sintatico na linha {line_num}: fim de arquivo inesperado. Talvez esteja faltando fechar um parêntese ')'.")
            elif 'RBRACKET' in clean_expected:
                raise SyntacticError(f"Erro sintatico na linha {line_num}: fim de arquivo inesperado. Talvez esteja faltando fechar um colchete ']'.")

        # Traduz os tokens esperados
        translated = []
        for t in clean_expected:
            if t == 'ID':
                # Refina a descrição de ID conforme o contexto
                if 'LET' in sym_types or 'CONST' in sym_types or (len(sym_types) >= 1 and sym_types[-1] in ('type', 'RBRACKET')):
                    translated.append("um nome de variável")
                elif 'FUNCTION' in sym_types:
                    translated.append("um nome de função")
                elif 'CLASS' in sym_types:
                    if token_type == 'CONSTRUCTOR':
                        translated.append("o nome da classe (para o construtor)")
                    else:
                        translated.append("um identificador (nome de atributo, método ou classe)")
                elif len(sym_types) >= 1 and sym_types[-1] == 'CLASS':
                    translated.append("um nome de classe")
                else:
                    translated.append("um identificador")
            elif t in TOKEN_TRANSLATIONS:
                translated.append(TOKEN_TRANSLATIONS[t])
            else:
                translated.append(f"'{t.lower()}'")

        # Remove duplicatas mantendo ordem
        unique_translated = []
        for item in translated:
            if item not in unique_translated:
                unique_translated.append(item)

        if len(unique_translated) > 0 and len(unique_translated) <= 5:
            if len(unique_translated) == 1:
                expected_str = f" Esperava-se {unique_translated[0]}."
            else:
                expected_str = f" Esperava-se um dos seguintes: {', '.join(unique_translated[:-1])} ou {unique_translated[-1]}."
        elif len(unique_translated) > 5:
            # Conjunto de tokens que iniciam novos comandos
            STATEMENT_STARTERS = {'LET', 'CONST', 'IF', 'WHILE', 'FOR', 'BREAK', 'FUNCTION', 'RETURN', 'CLASS', 'CONSOLE_LOG', 'INPUT'}
            # Conjunto de tokens que estendem expressões
            OPERATORS = {'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD', 'POWER', 'EQ', 'NE', 'GT', 'GE', 'LT', 'LE', 'AND', 'OR', 'DOT', 'ASSIGN', 'PLUS_ASSIGN', 'MINUS_ASSIGN', 'TIMES_ASSIGN', 'DIVIDE_ASSIGN', 'MOD_ASSIGN', 'INCREMENT', 'DECREMENT', 'LBRACKET', 'LPAREN'}

            has_statement_starters = any(tok in clean_expected for tok in STATEMENT_STARTERS)
            has_operators = any(tok in clean_expected for tok in OPERATORS)

            # Mostra apenas sugestões de pontuação/delimitadores ou ID se fizerem sentido
            suggestions = []
            if 'SEMICOLON' in clean_expected:
                suggestions.append("';'")
            if 'RBRACE' in clean_expected:
                suggestions.append("'}'")
            if 'RPAREN' in clean_expected:
                suggestions.append("')'")
            if 'RBRACKET' in clean_expected:
                suggestions.append("']'")
            if 'ID' in clean_expected:
                suggestions.append("um identificador")
            
            if suggestions:
                if len(suggestions) == 1:
                    base_str = suggestions[0]
                else:
                    base_str = f"{', '.join(suggestions[:-1])} ou {suggestions[-1]}"

                if has_statement_starters and not has_operators:
                    expected_str = f" Esperava-se {base_str} (ou o início de uma nova instrução)."
                elif has_operators and not has_statement_starters:
                    expected_str = f" Esperava-se {base_str} (ou a continuação da expressão)."
                elif has_operators and has_statement_starters:
                    expected_str = f" Esperava-se {base_str} (ou a continuação da expressão / início de uma nova instrução)."
                else:
                    expected_str = f" Esperava-se {base_str}."
            else:
                if has_statement_starters and not has_operators:
                    expected_str = " Esperava-se um novo comando ou instrução válida."
                elif has_operators and not has_statement_starters:
                    expected_str = " Esperava-se a continuação da expressão."
                else:
                    expected_str = " Esperava-se uma expressão ou comando válido."
        else:
            expected_str = ""
    else:
        expected_str = ""

    raise SyntacticError(f"Erro sintatico na linha {line_num}: token inesperado {unexpected}.{expected_str}")

# Inicialização do parser do PLY
parser = yacc.yacc()
