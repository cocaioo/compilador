# Compilador JSS (Java Script Simplificado) - Front-End & Back-End

Este repositório contém a implementação completa do compilador para a linguagem **JSS (Java Script Simplificado)**, desenvolvida para a disciplina de Compiladores da Universidade Federal do Piauí (UFPI).

O compilador integra:
1. **Análise Léxica (`lexer.py`):** Reconhecimento de tokens e detecção de caracteres/padrões inválidos.
2. **Análise Sintática (`parser.py`):** Validação gramatical e construção da Árvore de Sintaxe Abstrata (AST) com recuperação de erros sintáticos (sincronização de chaves).
3. **Análise Semântica (`semantic.py`):** Validação de escopos, tipos, constantes, passagem de vetores por parâmetro (validação estática de tamanho), limites de índices de vetores (validação de out of bounds para índices constantes) e propagação segura de tipos inválidos para evitar o efeito cascata.
4. **Geração de Código LLVM IR (`code_generator.py`):** Tradução completa da AST do JSS para código textual LLVM IR (`.ll`).
5. **Runtime de Suporte em C (`runtime.c`):** Biblioteca auxiliar que implementa funções do sistema (E/S, conversão e concatenação de strings, potência inteira) para ser vinculada ao binário nativo final.

---

## 1. Instalação e Configuração

O compilador exige **Python 3.10** ou superior e o compilador **Clang (LLVM)** para gerar binários nativos executáveis.

1. Instale a dependência do PLY (Python Lex-Yacc):
   ```bash
   pip install -r jss-compiler/requirements.txt
   ```

2. **Compilador Clang (LLVM):**
   * **Opção Portátil (Recomendada):** Já disponibilizamos uma versão portátil em `compilador/llvm-mingw` no diretório. O compilador em `main.py` irá detectá-la e utilizá-la automaticamente!
   * **Instalação Global (Opcional):**
     * **Windows:** execute `winget install LLVM.LLVM`
     * **Linux (Ubuntu/Debian):** execute `sudo apt install clang`
     * **macOS:** execute `brew install llvm`

---

## 2. Como Executar o Compilador (Compilação Nativa)

A execução é centralizada no arquivo `jss-compiler/src/main.py`.

Quando executado sobre um arquivo `.jss`, o compilador:
1. Executa as fases de Front-End (Léxico, Sintático e Semântico).
2. Se não houver erros, gera o arquivo intermediário `.ll` (LLVM IR).
3. Invoca o `clang` para compilar o arquivo `.ll` junto com o runtime de suporte (`runtime.c`), gerando um executável nativo `.exe` (ou executável ELF no Linux/macOS).

### A. Compilando um Arquivo de Exemplo
```bash
python jss-compiler/src/main.py jss-compiler/examples/teste_completo.jss
```
Isto gerará `jss-compiler/examples/teste_completo.ll` e `jss-compiler/examples/teste_completo.exe`. Você pode executar o binário nativo diretamente:
```bash
# No Windows:
jss-compiler/examples/teste_completo.exe
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

Temos testes unitários e de integração para todas as fases do compilador (Front-End e Back-End).

### A. Rodar todos os testes de uma vez (Recomendado)
Para rodar toda a suíte (Léxico, Sintático, Semântico, Geração de Código + Execução Nativa End-to-End):
```bash
python jss-compiler/tests/run_all_tests.py
```

### B. Rodar testes isolados por Fase/Módulo
* **Testes do Back-End (Compilação e Execução de Casos de Integração):**
  ```bash
  python jss-compiler/tests/run_backend_tests.py
  ```
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

## 4. Estruturas e Recursos do Backend

O Back-End suporta a compilação de todas as construções da linguagem JSS:
- **Controle de Fluxo e Loops:** Estruturas `if-else`, loops `while` e `for`, suporte a desvio incondicional `break`.
- **Expressões Lógicas de Curto-Circuito:** Implementação robusta das operações `&&` e `||` com blocos e instruções `phi` do LLVM.
- **Tipagem Dinâmica e Coerção:** Conversão segura de inteiros para reais e formatação/concatenação implícita de strings chamando o runtime C.
- **Vetores Unidimensionais e Bidimensionais:** Alocação de memória linearizada na stack (`alloca`) e indexação recursiva via `getelementptr`.
- **Programação Orientada a Objetos (Classes):** Classes mapeadas para estruturas (`%struct`), instanciação com alocação dinâmica (`malloc`), chamadas de métodos e construtores passando a referência implícita `this`, e comparação de ponteiros de objetos com `null`.
