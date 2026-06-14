# Testes do lexer JSS

Esta pasta contem testes isolados da analise lexica. Eles nao dependem do parser,
da analise semantica ou do backend.

## Estrutura

```text
tests/lexer/
|-- valid/    # programas que devem gerar tokens sem erro lexico
|-- invalid/  # programas que devem gerar LexicalError
`-- run_lexer_tests.py
```

## Como executar

A partir da raiz do projeto `jss-compiler`, instale as dependencias e execute:

```bash
pip install -r requirements.txt
python tests/lexer/run_lexer_tests.py
```

Saida esperada quando tudo passa:

```text
OK: testes do lexer passaram.
```

Os arquivos em `valid/` validam tokens aceitos pela especificacao da linguagem
JSS. Os arquivos em `invalid/` validam mensagens claras para erros lexicos, com
numero da linha, incluindo identificadores iniciados por digito, strings nao
finalizadas, comentarios multilinha e escapes invalidos.

Nas strings, o lexer aceita somente os escapes `\n`, `\"` e `\\`. Outros escapes,
como `\t`, devem gerar erro lexico.
