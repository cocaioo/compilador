"""Testes isolados do lexer JSS."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from frontend.lexer import LexicalError, build_lexer, tokens  # noqa: E402


VALID_DIR = Path(__file__).resolve().parent / "valid"
INVALID_DIR = Path(__file__).resolve().parent / "invalid"


def tokenize(source):
    lexer = build_lexer()
    lexer.input(source)
    return list(lexer)


def assert_valid_file(path):
    source = path.read_text(encoding="utf-8")
    try:
        tokens = tokenize(source)
    except LexicalError as exc:
        raise AssertionError(f"{path} deveria ser valido, mas falhou: {exc}") from exc

    if not tokens:
        raise AssertionError(f"{path} nao gerou tokens")

    return tokens


def assert_invalid_file(path):
    source = path.read_text(encoding="utf-8")
    try:
        tokenize(source)
    except LexicalError as exc:
        message = str(exc)
        if "linha" not in message:
            raise AssertionError(f"{path} nao informou linha: {message}") from exc
        return

    raise AssertionError(f"{path} deveria gerar erro lexico")


def assert_windows_newlines_are_counted():
    source = 'let int a;\r\nlet str b = "ok";\r\n@'
    try:
        tokenize(source)
    except LexicalError as exc:
        expected = "linha 3"
        if expected not in str(exc):
            raise AssertionError(
                f"CRLF deveria reportar {expected}, mas reportou: {exc}"
            ) from exc
        return

    raise AssertionError("CRLF com caractere invalido deveria gerar erro lexico")


def main():
    valid_files = sorted(VALID_DIR.glob("*.jss"))
    invalid_files = sorted(INVALID_DIR.glob("*.jss"))
    valid_token_types = set()

    if not valid_files:
        raise AssertionError("Nenhum teste valido encontrado")
    if not invalid_files:
        raise AssertionError("Nenhum teste invalido encontrado")

    for path in valid_files:
        valid_token_types.update(token.type for token in assert_valid_file(path))

    for path in invalid_files:
        assert_invalid_file(path)

    assert_windows_newlines_are_counted()
    missing_token_types = set(tokens) - valid_token_types
    if missing_token_types:
        missing = ", ".join(sorted(missing_token_types))
        raise AssertionError(f"Exemplos validos nao cobrem tokens: {missing}")

    print("OK: testes do lexer passaram.")


if __name__ == "__main__":
    main()
