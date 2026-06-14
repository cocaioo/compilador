# Testes do parser JSS

Esta pasta contem testes isolados da analise sintatica. Eles dependem do lexer (para obter os tokens) e da AST, mas nao da analise semantica ou do backend.

## Estrutura

```text
tests/parser/
|-- valid/    # programas JSS que devem ser parseados com sucesso gerando a AST
|-- invalid/  # programas JSS que devem falhar com SyntacticError
`-- run_parser_tests.py
```

## Como executar

A partir da raiz do projeto `jss-compiler`, certifique-se de que o ambiente virtual está ativo e execute:

```bash
python tests/parser/run_parser_tests.py
```

Saida esperada quando tudo passa:

```text
OK: testes do parser passaram.
```

Os arquivos em `valid/` validam a gramatica aceita pela especificacao da linguagem JSS (declaracoes tipadas, classes, construtores, vetores, chamadas e operadores). Os arquivos em `invalid/` validam erros sintaticos comuns que devem levantar excecoes `SyntacticError` com numero de linha identificando o token inesperado.
