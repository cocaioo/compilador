"""Lexer da linguagem JSS (JavaScript Simplificado).

Responsável por realizar a análise léxica: ler o código-fonte caractere por
caractere, agrupá-los em lexemas e associá-los aos seus respectivos tokens,
além de capturar e reportar erros léxicos apontando a linha e posição exatas.
"""

import ply.lex as lex
from frontend.errors import format_visual_error


# Dicionário de palavras reservadas da linguagem JSS.
# Mapeia a string literal encontrada no código para o tipo de Token correspondente.
# Isso evita que palavras-chave como 'let' ou 'if' sejam confundidas com identificadores normais.
reserved = {
    "let": "LET",
    "const": "CONST",
    "function": "FUNCTION",
    "if": "IF",
    "else": "ELSE",
    "while": "WHILE",
    "for": "FOR",
    "break": "BREAK",
    "return": "RETURN",
    "class": "CLASS",
    "constructor": "CONSTRUCTOR",
    "new": "NEW",
    "this": "THIS",
    "null": "NULL",
    "true": "TRUE",
    "false": "FALSE",
    "int": "INT_TYPE",
    "real": "REAL_TYPE",
    "str": "STR_TYPE",
    "bool": "BOOL_TYPE",
    "void": "VOID_TYPE",
    "input": "INPUT",
}


tokens = [
    "ID",
    "INT_LITERAL",
    "REAL_LITERAL",
    "STRING_LITERAL",
    "CONSOLE_LOG",
    "NOT",
    "PLUS",
    "MINUS",
    "TIMES",
    "DIVIDE",
    "MOD",
    "POWER",
    "EQ",
    "NE",
    "GT",
    "GE",
    "LT",
    "LE",
    "AND",
    "OR",
    "INCREMENT",
    "DECREMENT",
    "ASSIGN",
    "PLUS_ASSIGN",
    "MINUS_ASSIGN",
    "TIMES_ASSIGN",
    "DIVIDE_ASSIGN",
    "MOD_ASSIGN",
    "AND_ASSIGN",
    "OR_ASSIGN",
    "LPAREN",
    "RPAREN",
    "LBRACE",
    "RBRACE",
    "LBRACKET",
    "RBRACKET",
    "SEMICOLON",
    "COMMA",
    "DOT",
] + list(set(reserved.values()))

# Caracteres que devem ser ignorados silenciosamente pelo lexer (espaços e tabulações).
# Nota: Quebras de linha (\n ou \r) NÃO estão aqui, pois precisamos contá-las
# no token t_newline para manter o rastreamento correto do número da linha.
t_ignore = " \t"


class LexicalError(Exception):
    """Exceção levantada quando um caractere ou padrão inválido é encontrado."""


ALLOWED_STRING_ESCAPES = {
    "n": "\n",
    '"': '"',
    "\\": "\\",
}

t_POWER = r"\*\*"
t_EQ = r"=="
t_NE = r"!="
t_GE = r">="
t_LE = r"<="
t_AND_ASSIGN = r"&&="
t_OR_ASSIGN = r"\|\|="
t_AND = r"&&"
t_OR = r"\|\|"
t_INCREMENT = r"\+\+"
t_DECREMENT = r"--"
t_PLUS_ASSIGN = r"\+="
t_MINUS_ASSIGN = r"-="
t_TIMES_ASSIGN = r"\*="
t_DIVIDE_ASSIGN = r"/="
t_MOD_ASSIGN = r"%="
t_NOT = r"!"
t_PLUS = r"\+"
t_MINUS = r"-"
t_TIMES = r"\*"
t_DIVIDE = r"/"
t_MOD = r"%"
t_GT = r">"
t_LT = r"<"
t_ASSIGN = r"="
t_LPAREN = r"\("
t_RPAREN = r"\)"
t_LBRACE = r"\{"
t_RBRACE = r"\}"
t_LBRACKET = r"\["
t_RBRACKET = r"\]"
t_SEMICOLON = r";"
t_COMMA = r","
t_DOT = r"\."


# Regra para comentários de linha simples (//).
# São ignorados fazendo "pass" (retornando None, o que avança o lexer sem gerar token).
def t_COMMENT(t):
    r"//[^\r\n]*"
    pass


def _collect_or_raise(t, formatted):
    """Auxiliar para relatar erros léxicos.
    
    Se 'collect_errors' for True (ativado pelo wrapper do Parser para acumular erros),
    salva a string formatada em uma lista interna no lexer e retorna True para o token
    ser pulado. Caso contrário, lança a exceção imediatamente (modo padrão).
    """
    if getattr(t.lexer, 'collect_errors', False):
        if not hasattr(t.lexer, 'errors'):
            t.lexer.errors = []
        t.lexer.errors.append(formatted)
        return True
    raise LexicalError(formatted)


# Regra para capturar tentativas de usar comentários multilinha (/* ... */).
# Como JSS não os suporta, nós os interceptamos aqui explicitamente para gerar
# um erro léxico informativo em vez de falhar silenciosamente ou quebrar a sintaxe.
def t_MULTILINE_COMMENT(t):
    r"/\*"
    formatted = format_visual_error(
        t.lexer.lexdata,
        "Erro Léxico",
        "comentarios multilinha '/* ... */' nao sao permitidos; use comentarios de linha '//'",
        t.lineno,
        t.lexpos
    )
    if _collect_or_raise(t, formatted):
        return None


def t_CONSOLE_LOG(t):
    r"console\.log(?![A-Za-z0-9_])"
    return t


def t_REAL_LITERAL(t):
    r"((\d+\.\d*)|(\d*\.\d+))([eE][+-]?\d+)?|\d+[eE][+-]?\d+"
    t.value = float(t.value)
    return t


def t_INVALID_ID(t):
    r"\d+[A-Za-z_][A-Za-z0-9_]*"
    formatted = format_visual_error(
        t.lexer.lexdata,
        "Erro Léxico",
        f"identificador invalido '{t.value}'. Identificadores nao podem comecar com digito",
        t.lineno,
        t.lexpos
    )
    if _collect_or_raise(t, formatted):
        return None


def t_INT_LITERAL(t):
    r"\d+"
    t.value = int(t.value)
    return t


def t_INVALID_STRING_ESCAPE(t):
    r'"([^\\\r\n"]|\\[n"\\])*\\[^n"\\\r\n]([^\\\r\n"]|\\.)*"'
    invalid_escape = _find_invalid_escape(t.value)
    formatted = format_visual_error(
        t.lexer.lexdata,
        "Erro Léxico",
        f"escape invalido '\\{invalid_escape}' em string",
        t.lineno,
        t.lexpos
    )
    if _collect_or_raise(t, formatted):
        return None


def t_UNTERMINATED_STRING(t):
    r'"([^\\\r\n"]|\\.)*(\r\n|\r|\n|$)'
    formatted = format_visual_error(
        t.lexer.lexdata,
        "Erro Léxico",
        "string nao finalizada",
        t.lineno,
        t.lexpos
    )
    if _collect_or_raise(t, formatted):
        # Contabilizar a quebra de linha consumida pelo regex
        newlines = t.value.count('\n') + t.value.count('\r') - t.value.count('\r\n')
        t.lexer.lineno += newlines
        return None


def t_STRING_LITERAL(t):
    r'"([^\\\r\n"]|\\[n"\\])*"'
    t.value = _decode_string_literal(t.value)
    return t


# Regra para Identificadores e Palavras Reservadas.
# Captura qualquer nome iniciado com letra ou sublinhado (_).
# Antes de retornar o token como ID, verificamos se o texto corresponde a uma
# das chaves do dicionário 'reserved'. Em caso positivo, redefinimos o tipo do
# token para a palavra-chave correspondente (ex: 'let' vira token LET).
def t_ID(t):
    r"[A-Za-z_][A-Za-z0-9_]*"
    t.type = reserved.get(t.value, "ID")
    return t


# Regra para contar Quebras de Linha.
# Necessário para rastrear o número da linha corrente do código fonte para
# exibição de mensagens de erro detalhadas e visualmente amigáveis.
def t_newline(t):
    r"(\r\n|\r|\n)+"
    normalized = t.value.replace("\r\n", "\n").replace("\r", "\n")
    t.lexer.lineno += normalized.count("\n")


# Tratamento padrão do PLY para caracteres desconhecidos/inválidos.
# Disparado quando nenhum padrão regex das regras anteriores casa com a entrada.
def t_error(t):
    formatted = format_visual_error(
        t.lexer.lexdata,
        "Erro Léxico",
        f"caractere invalido '{t.value[0]}'",
        t.lineno,
        t.lexpos
    )
    if getattr(t.lexer, 'collect_errors', False):
        if not hasattr(t.lexer, 'errors'):
            t.lexer.errors = []
        t.lexer.errors.append(formatted)
        t.lexer.skip(1)
        return
    raise LexicalError(formatted)


def _decode_string_literal(raw_value):
    """Decodifica escapes validos de string sem aceitar escapes de Python."""
    decoded = []
    index = 1
    last_index = len(raw_value) - 1

    while index < last_index:
        current = raw_value[index]
        if current == "\\":
            escape = raw_value[index + 1]
            decoded.append(ALLOWED_STRING_ESCAPES[escape])
            index += 2
        else:
            decoded.append(current)
            index += 1

    return "".join(decoded)



def _find_invalid_escape(raw_value):
    index = 0
    last_index = len(raw_value) - 1

    while index < last_index:
        if raw_value[index] == "\\":
            escape = raw_value[index + 1]
            if escape not in ALLOWED_STRING_ESCAPES:
                return escape
            index += 2
        else:
            index += 1

    return ""


def build_lexer():
    """Constroi e retorna um lexer PLY pronto para uso."""
    return lex.lex()


def test_lexer(source_code):
    """Imprime todos os tokens reconhecidos no codigo-fonte informado."""
    lexer = build_lexer()
    lexer.input(source_code)

    for token in lexer:
        print(token)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python src/frontend/lexer.py <caminho_do_arquivo.jss>")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"--- Tokens de: {file_path} ---")
        test_lexer(content)
    except LexicalError as e:
        print(f"Erro Lexico: {e}")
    except FileNotFoundError:
        print(f"Erro: Arquivo '{file_path}' nao encontrado.")

