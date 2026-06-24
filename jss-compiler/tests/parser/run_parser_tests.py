"""Testes isolados do parser JSS."""

from pathlib import Path
import sys

# Garante o import correto do diretorio src/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from frontend.lexer import build_lexer
from frontend.parser import parser
from frontend.errors import SyntacticError

VALID_DIR = Path(__file__).resolve().parent / "valid"
INVALID_DIR = Path(__file__).resolve().parent / "invalid"


def parse_code(source):
    lexer = build_lexer()
    lexer.lineno = 1
    return parser.parse(source, lexer=lexer)


def assert_valid_file(path):
    source = path.read_text(encoding="utf-8")
    try:
        ast = parse_code(source)
    except Exception as exc:
        raise AssertionError(f"{path.name} deveria ser valido, mas falhou: {exc}") from exc

    if not ast:
        raise AssertionError(f"{path.name} nao gerou AST")

    return ast


def assert_invalid_file(path):
    source = path.read_text(encoding="utf-8")
    try:
        parse_code(source)
    except SyntacticError as exc:
        message = str(exc)
        if "linha" not in message:
            raise AssertionError(f"{path.name} nao informou linha no erro: {message}") from exc
        return

    raise AssertionError(f"{path.name} deveria gerar erro sintatico")


def test_multiple_syntax_errors():
    source = """
    let int x = 10 y;
    let str s = 10 z;
    function void main() {
        int a;
    }
    """
    try:
        parse_code(source)
    except SyntacticError as exc:
        message = str(exc)
        errors_count = message.lower().count("erro sin")
        if errors_count != 3:
            raise AssertionError(f"Esperava exatamente 3 erros sintaticos, mas obteve {errors_count}:\n{message}")
        
        if "token inesperado 'y'" not in message.lower():
            raise AssertionError(f"Falta erro de 'y' inesperado:\n{message}")
        if "token inesperado 'z'" not in message.lower():
            raise AssertionError(f"Falta erro de 'z' inesperado:\n{message}")
        if "utilize a palavra-chave 'let' ou 'const'" not in message.lower():
            raise AssertionError(f"Falta erro de declaracao C-style:\n{message}")
        return
    raise AssertionError("Deveria ter gerado erro sintatico")


def main():
    valid_files = sorted(VALID_DIR.glob("*.jss"))
    invalid_files = sorted(INVALID_DIR.glob("*.jss"))

    if not valid_files:
        raise AssertionError("Nenhum teste valido encontrado")
    if not invalid_files:
        raise AssertionError("Nenhum teste invalido encontrado")

    for path in valid_files:
        assert_valid_file(path)

    for path in invalid_files:
        assert_invalid_file(path)

    # Executar teste específico de múltiplos erros sintáticos
    test_multiple_syntax_errors()

    print("OK: testes do parser passaram.")


if __name__ == "__main__":
    main()
