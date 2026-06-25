"""Testes integrados do analisador semantico JSS."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from frontend.lexer import build_lexer
from frontend.parser import parser
from frontend.semantic import SemanticAnalyzer
from frontend.errors import SemanticError, SyntacticError

VALID_DIR = PROJECT_ROOT / "tests" / "parser" / "valid"
INVALID_DIR = PROJECT_ROOT / "tests" / "semantic_errors"


def analyze_code(source):
    lexer = build_lexer()
    lexer.lineno = 1
    ast = parser.parse(source, lexer=lexer)
    if not ast:
        raise SyntacticError("Falha na geracao da AST")
    analyzer = SemanticAnalyzer()
    analyzer.source_code = source
    analyzer.analyze(ast)
    return ast


def assert_valid_file(path):
    source = path.read_text(encoding="utf-8")
    try:
        analyze_code(source)
    except Exception as exc:
        raise AssertionError(f"{path.name} deveria ser valido semanticamente, mas falhou: {exc}") from exc


def assert_invalid_file(path):
    source = path.read_text(encoding="utf-8")
    try:
        analyze_code(source)
    except SemanticError as exc:
        message = str(exc)
        if "linha" not in message:
            raise AssertionError(f"{path.name} nao informou linha no erro: {message}") from exc
        return
    except Exception as exc:
        raise AssertionError(f"{path.name} deveria gerar erro semantico, mas gerou outro erro: {exc}") from exc

    raise AssertionError(f"{path.name} deveria gerar erro semantico")


def test_multiple_errors_cascade_suppression():
    source = """
    function void main() {
        let int a = b + c;
        let str s = 10;
    }
    """
    try:
        analyze_code(source)
    except SemanticError as exc:
        message = str(exc)
        errors_count = message.lower().count("erro sem")
        if errors_count != 3:
            raise AssertionError(f"Esperava exatamente 3 erros semanticos (com supressao de cascata), mas obteve {errors_count}:\n{message}")

        if "identificador 'b' nao declarado" not in message:
            raise AssertionError(f"Falta erro de 'b' nao declarado:\n{message}")
        if "identificador 'c' nao declarado" not in message:
            raise AssertionError(f"Falta erro de 'c' nao declarado:\n{message}")
        if "tipos incompativeis: esperava 'str', mas obteve 'int'" not in message:
            raise AssertionError(f"Falta erro de tipo incompativel para 's':\n{message}")
        return
    raise AssertionError("Deveria ter gerado erro semantico")


def main():
    valid_files = sorted(VALID_DIR.glob("*.jss"))
    invalid_files = sorted(INVALID_DIR.glob("*.jss"))

    if not valid_files:
        raise AssertionError("Nenhum teste valido encontrado")
    if not invalid_files:
        raise AssertionError("Nenhum teste invalido encontrado")

    print(f"Executando {len(valid_files)} testes semanticos de sucesso...")
    for path in valid_files:
        assert_valid_file(path)

    print(f"Executando {len(invalid_files)} testes semanticos de falha...")
    for path in invalid_files:
        assert_invalid_file(path)

    print("Executando teste especifico de multiplos erros e supressao de cascata...")
    test_multiple_errors_cascade_suppression()

    print("OK: todos os testes semanticos passaram com sucesso.")


if __name__ == "__main__":
    main()
