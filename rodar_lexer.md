# Comandos para Rodar o Lexer

## Executar em um arquivo específico (válido ou com erro)
```bash
python jss-compiler/src/frontend/lexer.py <caminho_do_arquivo.jss>
```

**Exemplos:**
```bash
python jss-compiler/src/frontend/lexer.py jss-compiler/tests/lexer/valid/basic_program.jss
python jss-compiler/src/frontend/lexer.py jss-compiler/tests/lexer/invalid/invalid_identifier.jss
```

---

## Executar todos os testes do Lexer
```bash
python jss-compiler/tests/lexer/run_lexer_tests.py
```
