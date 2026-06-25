# Compilador JSS (Java Script Simplificado) - Front-End

Este repositório contém a implementação completa da etapa de **Front-End** do compilador para a linguagem **JSS (Java Script Simplificado)**, desenvolvida para a disciplina de Compiladores da Universidade Federal do Piauí (UFPI).

O compilador integra:
1. **Análise Léxica (`lexer.py`):** Reconhecimento de tokens e detecção de caracteres/padrões inválidos.
2. **Análise Sintática (`parser.py`):** Validação gramatical e construção da Árvore de Sintaxe Abstrata (AST) com recuperação de erros sintáticos (sincronização de chaves).
3. **Análise Semântica (`semantic.py`):** Validação de escopos, tipos, constantes e propagação segura de tipos inválidos para evitar o efeito cascata.

---

## 1. Instalação e Configuração

O compilador exige **Python 3.10** ou superior.

1. Navegue até o diretório do projeto e instale a dependência do PLY (Python Lex-Yacc):
   ```bash
   pip install -r jss-compiler/requirements.txt
   ```
   *(Caso utilize ambiente virtual `.venv`, lembre-se de ativá-lo antes de instalar.)*

---

## 2. Como Executar o Compilador

A execução é centralizada no arquivo `jss-compiler/src/main.py`.

### A. Executando um Arquivo de Exemplo
Forneça o caminho do arquivo `.jss` como argumento.
* **Exemplo de sucesso (código válido completo):**
  ```bash
  python jss-compiler/src/main.py jss-compiler/examples/teste_completo.jss
  ```
* **Exemplo com erros semânticos acumulados:**
  ```bash
  python jss-compiler/src/main.py jss-compiler/tests/semantic_errors/multiple_undeclared_mismatch_const.jss
  ```

### B. Modo Interativo (Digitando Código no Terminal)
Use a flag `-` para digitar ou colar código diretamente na linha de comando:
```bash
python jss-compiler/src/main.py -
```
* **Para processar o código digitado:**
  * No **Windows**: Pressione `Ctrl + Z` e depois `Enter`.
  * No **Linux/macOS**: Pressione `Ctrl + D`.


## 3. Como Executar as Suítes de Testes

Temos testes unitários e testes de integração com verificação de acúmulo de erros e supressão de cascatas.

### A. Rodar todos os testes de uma vez (Recomendado)
Para rodar toda a suíte pesada (Léxico, Sintático, Semântico e testes de integração End-to-End):
```bash
python jss-compiler/tests/run_all_tests.py
```

### B. Rodar testes isolados por Fase
* **Apenas Testes do Lexer (Léxico):**
  ```bash
  python jss-compiler/tests/lexer/run_lexer_tests.py
  ```
* **Apenas Testes do Parser (Sintático):**
  ```bash
  python jss-compiler/tests/parser/run_parser_tests.py
  ```
* **Apenas Testes do Semantic (Semântico):**
  ```bash
  python jss-compiler/tests/run_semantic_tests.py
  ```

---

