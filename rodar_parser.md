# Comandos para Rodar o Parser (Compilador JSS)

Este documento lista as formas disponíveis de executar a análise sintática (Parser) e validar o código JSS no compilador para a 1ª etapa.

---

## 1. Executar passando o caminho do arquivo como argumento

Esta é a forma padrão de ler um arquivo `.jss` e obter a árvore sintática (AST) gerada.

```bash
python jss-compiler/src/main.py <caminho_do_arquivo.jss>
```

**Exemplo com arquivo válido:**
```bash
python jss-compiler/src/main.py jss-compiler/tests/parser/valid/functions_and_control.jss
```

**Exemplo com arquivo que possui erro de sintaxe:**
```bash
python jss-compiler/src/main.py jss-compiler/tests/parser/invalid/missing_semicolon.jss
```

---

## 2. Executar via Entrada Padrão (Stdin / Pipes)

Útil para integrar o compilador com scripts de testes automatizados ou ferramentas externas que enviam o código diretamente pela entrada padrão.

> [!IMPORTANT]
> **Por que esta funcionalidade é automática?**
> De acordo com o item **3.1.c.I** da especificação do projeto (*"ler da entrada padrão arquivo com programa escrito na linguagem"*), o compilador deve ler o código de forma transparente via stdin. 
> A detecção automática (quando nenhum argumento é passado e o terminal não é interativo) garante que o compilador funcione com **scripts de correção automática** do professor, que costumam injetar o arquivo de teste diretamente na entrada padrão (ex: `python main.py < arquivo.jss`) sem especificar parâmetros de linha de comando.

### No Windows PowerShell:
```powershell
Get-Content jss-compiler/tests/parser/valid/functions_and_control.jss | python jss-compiler/src/main.py
```

### No Windows CMD ou Linux/macOS Bash:
```bash
python jss-compiler/src/main.py < jss-compiler/tests/parser/valid/functions_and_control.jss
```

---

## 3. Executar em modo interativo (leitura do teclado)

Permite digitar ou colar o código JSS diretamente no terminal para teste rápido.

```bash
python jss-compiler/src/main.py -
```

> **Dica:** Para finalizar a digitação e enviar o código para o compilador processar:
> * No **Windows**: Pressione `Ctrl + Z` e depois `Enter`.
> * No **Linux/macOS**: Pressione `Ctrl + D`.

---

## 4. Executar toda a suíte de testes do Parser

Roda o script que valida automaticamente se os arquivos válidos compilam com sucesso e se os arquivos inválidos disparam os erros de sintaxe esperados com indicação de linha.

```bash
python jss-compiler/tests/parser/run_parser_tests.py
```

---

## 5. Executar o Tutorial de Erros Léxicos e Sintáticos

Foi criado um arquivo interativo com erros progressivos para praticar a identificação e correção de problemas léxicos e sintáticos no compilador.

```bash
python jss-compiler/src/main.py jss-compiler/examples/tutorial_erros.jss
```

O compilador parará no primeiro erro. Corrija-o seguindo a recomendação explicada no comentário do arquivo, salve o arquivo e execute o comando novamente até concluir todos os desafios léxicos e sintáticos.
