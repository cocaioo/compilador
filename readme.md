# Compilador JSS (Java Script Simplificado) - Front-End

Este repositório contém a implementação completa da etapa de **Front-End** do compilador para a linguagem **JSS (Java Script Simplificado)**, desenvolvida para a disciplina de Compiladores da Universidade Federal do Piauí (UFPI).

O front-end é responsável pelas seguintes etapas de análise:
1. **Análise Léxica (`lexer.py`):** Tokenização e validação de símbolos.
2. **Análise Sintática (`parser.py`):** Validação gramatical e construção da Árvore de Sintaxe Abstrata (AST).
3. **Análise Semântica (`semantic.py`):** Validação de escopos, tipos, constantes e mutabilidade.

---

## 1. Pré-requisitos e Instalação

### Pré-requisitos
* **Python 3.10** ou superior instalado no sistema.

### Instalação das Dependências
O compilador utiliza o pacote **PLY (Python Lex-Yacc)** para a análise léxica e sintática.

1. Navegue até o diretório do projeto:
   ```bash
   cd compilador/jss-compiler
   ```

2. Crie e ative um ambiente virtual (opcional, mas recomendado):
   ```bash
   python -m venv .venv
   # No Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # No Linux/macOS:
   source .venv/bin/activate
   ```

3. Instale a biblioteca PLY:
   ```bash
   pip install -r requirements.txt
   ```

---

## 2. Como Executar o Compilador

A execução do compilador é feita a partir do arquivo principal `src/main.py`. Ele aceita a leitura do código-fonte tanto por arquivo quanto pela entrada padrão (stdin).

### A. Execução por Arquivo de Entrada
Passe o caminho do arquivo `.jss` como argumento:
```bash
python src/main.py caminho/do/arquivo.jss
```

### B. Execução por Entrada Padrão (Redirecionamento)
Você pode redirecionar o conteúdo de um arquivo para o compilador:
* **No Windows (PowerShell):**
  ```powershell
  Get-Content caminho/do/arquivo.jss | python src/main.py
  ```
* **No Linux / macOS / Windows (cmd):**
  ```bash
  python src/main.py < caminho/do/arquivo.jss
  ```

### C. Execução Interativa do Teclado
Use o caractere `-` como argumento para digitar o código no terminal interativamente. Pressione `Ctrl+Z` (Windows) ou `Ctrl+D` (Linux/macOS) seguido de `Enter` para encerrar e compilar:
```bash
python src/main.py -
```

---

## 3. Exemplos de Execução

### A. Exemplo de Sucesso (Código Válido)
Quando o código JSS é válido em todas as etapas, o compilador exibe uma mensagem de confirmação.

* **Código de entrada (`sucesso.jss`):**
  ```jss
  class Retangulo {
      int largura;
      int altura;
      
      Retangulo constructor(int w, int h) {
          this.largura = w;
          this.altura = h;
      }
      
      int area() {
          return this.largura * this.altura;
      }
  }

  function void main() {
      let Retangulo r = new Retangulo(5, 10);
      console.log("Area do retangulo:", r.area());
  }
  ```

* **Saída no Terminal:**
  ```text
  Analise concluida com sucesso.
  ```

---

### B. Exemplos com Erros

O compilador do JSS possui um sistema de detecção e relatório de erros com **ponteiros visuais (caret)** que mostram exatamente em qual linha e coluna o erro ocorreu, acompanhado de uma explicação detalhada.

#### I. Erro Léxico
Ocorre quando um caractere desconhecido ou inválido é inserido no código.

* **Código de entrada:**
  ```jss
  let int x = 10 @;
  ```

* **Saída no Terminal:**
  ```text
  Erro Léxico na linha 1, coluna 14: caractere inválido '@' detectado na entrada.
   1 | let int x = 10 @;
                      ^
  ```

#### II. Erro Sintático
Ocorre quando a estrutura gramatical do código viola as regras sintáticas definidas.

* **Código de entrada (Tentativa de usar palavra reservada como identificador):**
  ```jss
  let int const = 12;
  ```

* **Saída no Terminal:**
  ```text
  Erro Sintático na linha 1, coluna 9: token inesperado 'const'. O nome 'const' é uma palavra reservada da linguagem e não pode ser utilizado como identificador.
   1 | let int const = 12;
               ^
  ```

* **Código de entrada (Declaração invertida):**
  ```jss
  int let x = 10;
  ```

* **Saída no Terminal:**
  ```text
  Erro Sintático na linha 1, coluna 5: token inesperado 'let'. A ordem de declaração de variáveis em JSS exige a palavra-chave antes do tipo (ex: 'let int variavel;' em vez de 'int let variavel;').
   1 | int let x = 10;
           ^
  ```

#### III. Erro Semântico
Ocorre quando o código é válido lexicamente e sintaticamente, mas viola as regras lógicas e de tipos da linguagem.

* **Código de entrada (Tipos Incompatíveis):**
  ```jss
  function void main() {
      let int x = 10;
      x = "texto";
  }
  ```

* **Saída no Terminal:**
  ```text
  Erro Semântico na linha 3, coluna 9: tipos incompativeis: esperava 'int', mas obteve 'str'.
   3 |     x = "texto";
               ^
  ```

* **Código de entrada (Atribuição para constante):**
  ```jss
  function void main() {
      const int limite = 100;
      limite = 200;
  }
  ```

* **Saída no Terminal:**
  ```text
  Erro Semântico na linha 3, coluna 5: atribuicao para alvo constante 'limite' nao e permitida.
   3 |     limite = 200;
           ^
  ```

* **Código de entrada (Atribuição direta de vetor fora da declaração):**
  ```jss
  function void main() {
      let int[3] vetor = [1, 2, 3];
      vetor = [4, 5, 6];
  }
  ```

* **Saída no Terminal:**
  ```text
  Erro Semântico na linha 3, coluna 5: atribuicao direta para vetor nao e permitida. Vetores so podem ser modificados elemento a elemento.
   3 |     vetor = [4, 5, 6];
           ^
  ```

---

## 4. Estrutura de Testes Integrados

Para rodar todos os testes automatizados da análise semântica (tanto casos válidos quanto inválidos):
```bash
python tests/run_semantic_tests.py
```
Se tudo estiver correto, a saída será:
```text
Executando 6 testes semanticos de sucesso...
Executando 8 testes semanticos de falha...
OK: todos os testes semanticos passaram com sucesso.
```
