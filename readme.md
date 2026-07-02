# Compilador JSS (Java Script Simplificado) - Front-End & Back-End

Este repositório contém a implementação completa do compilador para a linguagem **JSS (Java Script Simplificado)**, desenvolvida para a disciplina de Compiladores da Universidade Federal do Piauí (UFPI).

O compilador integra:
1. **Análise Léxica (`lexer.py`):** Reconhecimento de tokens e detecção de caracteres/padrões inválidos.
2. **Análise Sintática (`parser.py`):** Validação gramatical e construção da Árvore de Sintaxe Abstrata (AST) com recuperação de erros sintáticos (sincronização de chaves).
3. **Análise Semântica (`semantic.py`):** Validação de escopos, tipos, constantes, passagem de vetores por parâmetro (validação estática de tamanho), limites de índices de vetores (validação de out of bounds para índices constantes) e propagação segura de tipos inválidos para evitar o efeito cascata.
4. **Geração de Código LLVM IR (`code_generator.py`):** Tradução completa da AST do JSS para um módulo LLVM, construído programaticamente com a API `llvmlite.ir` (veja as regras de tradução detalhadas e exemplos no [Guia de Geração de Código](file:///c:/Users/Caio/Desktop/compilador/GERACAO_CODIGO.md)).
5. **Runtime de Suporte (`runtime_ir.py`):** Biblioteca auxiliar que implementa funções do sistema (E/S, conversão e concatenação de strings, potência inteira), escrita diretamente como funções LLVM IR (via `llvmlite.ir`) e injetada no mesmo módulo do programa do usuário - substitui o antigo `runtime.c`, eliminando qualquer dependência de compilar código C.

---

## 1. Instalação e Configuração

O compilador exige **Python 3.10** ou superior. Diferente de versões anteriores, **não é mais necessário instalar o Clang** (nem qualquer outro compilador C): a própria `llvmlite` (biblioteca Python que embute a LLVM) faz a tradução do IR para código de máquina x86-64.

1. Instale as dependências (PLY e llvmlite):
   ```bash
   pip install -r jss-compiler/requirements.txt
   ```

2. **Linker (`ld.lld`):** a única ferramenta externa que ainda é necessária é um *linker* - não um compilador - para transformar o código objeto x86-64 gerado pela `llvmlite` em um `.exe` do Windows, vinculando-o ao runtime C do sistema (`msvcrt`, para `printf`/`scanf`/`malloc`). Já disponibilizamos um kit portátil com o `ld.lld` em `compilador/llvm-mingw`, que o `main.py` detecta e utiliza automaticamente. Este kit não precisa ser instalado à parte: basta que a pasta `llvm-mingw/` exista na raiz do repositório.

---

## 2. Como Executar o Compilador (Compilação Nativa)

A execução é centralizada no arquivo `jss-compiler/src/main.py`.

Quando executado sobre um arquivo `.jss`, o compilador:
1. Executa as fases de Front-End (Léxico, Sintático e Semântico).
2. Se não houver erros, constrói o módulo LLVM (via `llvmlite.ir`) e grava sua representação textual no arquivo intermediário `.ll`, para inspeção.
3. Usa `llvmlite.binding` (a própria LLVM) para traduzir esse módulo em assembly textual x86-64 (`.s`) e em código objeto nativo (`.o`) - sem invocar nenhum compilador C.
4. Invoca o linker `ld.lld` (parte do projeto LLVM, empacotado em `llvm-mingw/`) para vincular esse objeto ao runtime C do Windows e gerar o executável nativo `.exe` final.

### A. Compilando um Arquivo de Exemplo
```bash
python jss-compiler/src/main.py jss-compiler/examples/teste_completo.jss
```
Isto gerará `jss-compiler/examples/teste_completo.ll`, `jss-compiler/examples/teste_completo.s`, `jss-compiler/examples/teste_completo.o` e `jss-compiler/examples/teste_completo.exe`. Você pode executar o binário nativo diretamente:
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
- **Tipagem Dinâmica e Coerção:** Conversão segura de inteiros para reais e formatação/concatenação implícita de strings chamando o runtime (`runtime_ir.py`).
- **Vetores Unidimensionais e Bidimensionais:** Alocação de memória linearizada na stack (`alloca`) e indexação recursiva via `getelementptr`.
- **Programação Orientada a Objetos (Classes):** Classes mapeadas para estruturas (`%struct`), instanciação com alocação dinâmica (`malloc`), chamadas de métodos e construtores passando a referência implícita `this`, e comparação de ponteiros de objetos com `null`.

---

## 5. Exemplos de Códigos com Sucesso e Erro

### A. Exemplo de Sucesso (Compilação e Execução Bem-Sucedida)

Este exemplo demonstra declaração de classe, construtor, método, concatenação implícita com strings, conversão de tipo explícita, laço `for` com operador de incremento pré-fixado, e alocação dinâmica de objetos.

**Código JSS (`sucesso.jss`):**
```javascript
class Retangulo {
    real largura;
    real altura;

    Retangulo constructor(real largura, real altura) {
        this.largura = largura;
        this.altura = altura;
    }

    real area() {
        return this.largura * this.altura;
    }
}

function void main() {
    let real l = 5.0;
    let real a = 4.0;
    let Retangulo r = new Retangulo(l, a);
    
    let real area_ret = r.area();
    console.log("Largura:", r.largura, "Altura:", r.altura);
    console.log("Area do Retangulo:", area_ret);
}
```

**Comando de Execução:**
```bash
python jss-compiler/src/main.py sucesso.jss
```

**Saída Esperada no Terminal:**
```text
Analise semantica concluida com sucesso.
Gerando codigo LLVM IR...
Codigo LLVM IR gerado com sucesso em 'sucesso.ll'.
Codigo assembly gerado com sucesso em 'sucesso.s'.
Compilando executavel nativo...
Compilacao concluida com sucesso! Executavel gerado em 'sucesso.exe'.
```

**Executando o Binário Gerado:**
```bash
./sucesso.exe
```
**Saída:**
```text
Largura: 5 Altura: 4
Area do Retangulo: 20
```

---

### B. Exemplo com Múltiplos Erros (Falha na Compilação)

Este exemplo introduz erros de fases distintas (léxica, sintática e semântica) demonstrando a capacidade do compilador de reportar múltiplos problemas organizados por categoria em um relatório unificado e com indicação visual da linha e coluna de cada ocorrência.

**Código JSS (`erros.jss`):**
```javascript
let int x = 10 y; // Erro Sintático: token inesperado 'y'

function void main() {
    let int a = nao_declarada; // Erro Semântico: variável não declarada
    let str s = 123;           // Erro Semântico: tipo incompatível (esperava 'str', obteve 'int')
    
    /* Comentário multilinha que é inválido em JSS */
}
```

**Comando de Execução:**
```bash
python jss-compiler/src/main.py erros.jss
```

**Saída Esperada no Terminal:**
```text
==================================================
        RELATÓRIO DE ERROS DE COMPILAÇÃO
==================================================

[ERROS LÉXICOS / SINTÁTICOS] ---------------------
Erro Sintatico na linha 1, coluna 14: token inesperado 'y'. ';' ausente antes de 'y'.
 1 | let int x = 10 y; // Erro Sintático: token inesperado 'y'
                    ^

Erro Léxico na linha 7, coluna 5: comentarios multilinha '/* ... */' nao sao permitidos; use comentarios de linha '//'
 7 |     /* Comentário multilinha que é inválido em JSS */
         ^

[ERROS SEMÂNTICOS] -------------------------------
Erro Semântico na linha 4, coluna 17: identificador 'nao_declarada' nao declarado.
 4 |     let int a = nao_declarada; // Erro Semântico: variável não declarada
                     ^

Erro Semântico na linha 5, coluna 17: tipos incompativeis: esperava 'str', mas obteve 'int'.
 5 |     let str s = 123;           // Erro Semântico: tipo incompatível (esperava 'str', obteve 'int')
                     ^
```

