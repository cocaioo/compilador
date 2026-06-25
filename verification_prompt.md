# Diretrizes para Verificação de Robustez do Compilador JSS

Este documento contém a especificação detalhada de testes e verificação de robustez do compilador JSS, com foco especial no tratamento de erros de fechamento de chaves e na integridade da acumulação de erros sintáticos/semânticos sem erros em cascata.

---

## 🎯 Objetivos de Verificação

O objetivo é auditar o compilador JSS para garantir que:
1. **Detecção de Chaves Incompletas:** Erros de fechamento de chaves (como chaves faltantes, chaves sobressalentes ou blocos desalinhados) sejam identificados com precisão, apontando a linha e coluna corretas sem emitir mensagens enganosas de "Fim de Arquivo Inesperado" quando for possível identificar a causa raiz.
2. **Acumulação de Múltiplos Erros:** O compilador deve acumular múltiplos erros de fases distintas (Léxico, Sintático e Semântico) e exibi-los de forma organizada no relatório final, em vez de abortar no primeiro erro encontrado.
3. **Prevenção de Erro Cascata:** Uma falha em um bloco ou instrução não deve corromper o estado do compilador, gerando dezenas de falsos erros subsequentes. O uso de tokens de erro e propagação de tipos especiais (como `INVALID`) deve garantir a estabilização do parser e do analisador semântico.

---

## 🔍 Áreas Críticas de Auditoria

### 1. Recuperação de Chaves e Blocos (`parser.py`)
- **Regras de Bloco:**
  - Auditar a eficácia da produção `block : LBRACE error RBRACE` para garantir que o parser consiga se recuperar de erros sintáticos locais sem descartar o escopo do bloco pai.
  - Verificar se a chamada a `p.parser.errok()` ocorre no momento correto para evitar loops de erro sintático ou supressão excessiva.
- **Estruturas de Controle com Chaves Obrigatórias:**
  - Auditar `if-else`, `while` e `for` para assegurar que a ausência de chaves (`{` e `}`) resulte em um erro sintático explícito instruindo o usuário a utilizar chaves (ex: `"token inesperado '...'. Esperava-se '{'"`).

### 2. Acumulação de Erros Sintáticos e Léxicos (`_ParserWrapper`)
- **Interação Lexer-Parser:**
  - Garantir que a flag `collect_errors` esteja ativa no lexer durante a análise sintática.
  - Verificar se os erros de caracteres inválidos (`t_error` no lexer) são agregados de forma única no relatório final juntamente com os erros gerados pelo parser em `p_error`.
- **Prevenção de Duplicidade:**
  - Auditar se mensagens idênticas geradas durante a pilha de redução do parser são filtradas antes da exibição ao usuário.

### 3. Recuperação Semântica e Coleta (`semantic.py`)
- **Propagação de `INVALID`:**
  - Validar se operações envolvendo variáveis não declaradas ou tipos incompatíveis retornam o tipo `INVALID` e se os nós subsequentes tratam `INVALID` sem levantar novas exceções ou relatar novos erros redundantes para a mesma instrução.
- **Relatório Unificado:**
  - Verificar se `SemanticAnalyzer` acumula todos os erros em sua lista local `self.errors` e levanta a exceção `SemanticError` apenas após a varredura completa da AST.

---

## 🧪 Cenários de Teste Obrigatórios (Suíte de Validação)

### Cenário A: Falta de Fechamento de Chaves (Unbalanced Braces)
```javascript
function void main() {
    let int x = 10;
    if (x > 5) {
        console.log(x);
    // Falta fechar o bloco do 'if' ou da função 'main'
}
```
* **Expectativa:** O compilador deve acusar a chave faltante no final do arquivo com uma sugestão explícita (ex: `"Talvez esteja faltando fechar uma chave '}'"`).

### Cenário B: Chaves Sobressalentes / Mislabeled
```javascript
function void main() {
    if (1 > 0)
        console.log("Erro"); // Falta chaves aqui
    } // Chave órfã fechando prematuramente a função main
    
    let int b = 20;
}
```
* **Expectativa:** O parser deve identificar que a instrução do `if` falhou por não abrir bloco com `{`, reportar a falta do `{`, se recuperar e reportar o desalinhamento das chaves subsequentes de forma limpa.

### Cenário C: Acumulação sem Cascata Semântica
```javascript
function void main() {
    let int a = nao_declarado; // Erro semântico 1
    let int b = a + 10;        // Não deve gerar erro ("a" é INVALID)
    let str s = 123;           // Erro semântico 2 (tipos incompatíveis)
}
```
* **Expectativa:** O relatório final deve exibir exatamente dois erros semânticos (variável não declarada e atribuição de tipo incompatível), sem relatar erro de tipo na soma `a + 10`.

---

## 🛠️ Procedimento de Execução e Verificação

Para cada execução de teste de robustez, siga o fluxo:
1. **Executar a Suíte Completa:**
   ```bash
   python jss-compiler/tests/run_all_tests.py
   ```
2. **Validar Códigos Sintáticos Inválidos Isoladamente:**
   ```bash
   python jss-compiler/src/main.py jss-compiler/tests/parser/invalid/<arquivo>.jss
   ```
3. **Investigar Regressões de Tabelas:**
   Caso edite as regras gramaticais no `parser.py`, remova os arquivos de cache de tabelas gerados no diretório temporário ou local (`parsetab.py`, `_jss_parsetab.py`) para forçar o PLY a regenerar as tabelas LALR.
