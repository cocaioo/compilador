# JSS Compiler

## Overview

Compilador academico para a linguagem **JSS (Java Script Simplificado)**, desenvolvido em Python com PLY.

O projeto esta organizado em duas partes principais:

```text
jss-compiler/
|-- src/
|   |-- frontend/
|   |   |-- lexer.py
|   |   |-- parser.py
|   |   |-- ast_nodes.py
|   |   |-- semantic.py
|   |   |-- symbol_table.py
|   |   `-- errors.py
|   |
|   |-- backend/
|   |   `-- code_generator.py
|   |
|   `-- main.py
|
|-- tests/
|-- examples/
|-- requirements.txt
`-- README.md
```

O `frontend` concentra a analise lexica, sintatica, AST, erros e futura analise semantica. O `backend` fica reservado para as etapas futuras de geracao de codigo ou outra forma de saida do compilador.

## Instalacao das dependencias

Crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente virtual no Windows:

```bash
.venv\Scripts\activate
```

Instale as dependencias:

```bash
pip install -r requirements.txt
```

## Instrucoes de como rodar

Execute o compilador passando um arquivo `.jss` como argumento:

```bash
python src/main.py examples/programa.jss
```

Exemplo esperado apos a implementacao do front-end:

```text
Analise concluida com sucesso.
```
