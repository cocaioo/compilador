# JSS Compiler

Compilador academico para a linguagem **JSS (Java Script Simplificado)**, desenvolvido como projeto da disciplina de Compiladores.

Nesta primeira entrega, o foco sera o front-end do compilador:

- analise lexica;
- analise sintatica;
- execucao via linha de comando;
- mensagens de erro indicando a linha do problema.

A analise semantica sera implementada posteriormente.

## Tecnologias utilizadas

- Python 3
- PLY (Python Lex-Yacc)

## Estrutura de diretorios

```text
jss-compiler/
|-- src/
|   |-- lexer.py
|   |-- parser.py
|   |-- ast_nodes.py
|   |-- semantic.py
|   |-- symbol_table.py
|   |-- errors.py
|   `-- main.py
|
|-- tests/
|   |-- valid/
|   |-- lexical_errors/
|   |-- syntax_errors/
|   `-- semantic_errors/
|
|-- examples/
|
|-- README.md
|-- requirements.txt
`-- .gitignore
```

## Responsabilidade dos arquivos

- `src/lexer.py`: define os tokens da linguagem, as regras lexicas e o tratamento de erros lexicos.
- `src/parser.py`: define a gramatica da linguagem, executa a analise sintatica e integra a criacao da AST.
- `src/ast_nodes.py`: define as estruturas de dados que representam os nos da arvore sintatica abstrata.
- `src/semantic.py`: concentrara as validacoes semanticas, como tipos, escopos e uso correto de identificadores.
- `src/symbol_table.py`: armazenara simbolos declarados, escopos e informacoes necessarias para a analise semantica.
- `src/errors.py`: centraliza classes, mensagens e formatacao de erros do compilador.
- `src/main.py`: ponto de entrada da aplicacao via linha de comando.
- `tests/valid/`: programas JSS validos usados para testes.
- `tests/lexical_errors/`: programas com erros lexicos esperados.
- `tests/syntax_errors/`: programas com erros sintaticos esperados.
- `tests/semantic_errors/`: programas com erros semanticos esperados, usados em etapa futura.
- `examples/`: exemplos simples de programas JSS para demonstracao.

## Como instalar dependencias

Crie e ative um ambiente virtual:

```bash
python -m venv .venv
```

No Windows:

```bash
.venv\Scripts\activate
```

No Linux/macOS:

```bash
source .venv/bin/activate
```

Instale as dependencias:

```bash
pip install -r requirements.txt
```

## Como executar o compilador

Quando a integracao inicial estiver implementada em `src/main.py`, a execucao devera seguir este formato:

```bash
python src/main.py caminho/do/arquivo.jss
```

## Exemplo de execucao

```bash
python src/main.py examples/programa_valido.jss
```

Saida esperada para um programa valido:

```text
Analise concluida com sucesso.
```

Exemplo de saida para erro:

```text
Erro sintatico na linha 4: token inesperado ')'.
```

## Planejamento das etapas

### Etapa 1: Estrutura inicial

- Criar organizacao de pastas do projeto.
- Documentar responsabilidades dos arquivos.
- Definir planejamento de trabalho entre a dupla.

### Etapa 2: Analise lexica

Responsavel principal: Pessoa 1.

- Definir palavras-chave, operadores, delimitadores e literais da JSS.
- Implementar tokens com PLY.
- Implementar erros lexicos com numero da linha.
- Criar testes em `tests/valid/` e `tests/lexical_errors/`.

### Etapa 3: Analise sintatica e AST

Responsavel principal: Pessoa 2.

- Definir a gramatica da linguagem JSS.
- Implementar regras sintaticas com PLY.
- Criar os nos principais da AST em `ast_nodes.py`.
- Integrar parser, AST e execucao em `main.py`.
- Criar testes em `tests/valid/` e `tests/syntax_errors/`.

### Etapa 4: Integracao da primeira entrega

Responsaveis: Pessoa 1 e Pessoa 2.

- Integrar lexer e parser pela linha de comando.
- Padronizar mensagens de erro em `errors.py`.
- Revisar exemplos de execucao.
- Validar os casos de teste da entrega front-end.

### Etapa 5: Analise semantica

Responsaveis: Pessoa 1 e Pessoa 2.

- Implementar tabela de simbolos.
- Validar declaracoes, escopos e tipos.
- Criar testes em `tests/semantic_errors/`.
- Integrar a analise semantica ao fluxo do compilador.

## Sugestoes de melhorias futuras

- Adicionar `pytest` para automatizar os testes dos exemplos validos e invalidos.
- Criar um diretorio `docs/` para guardar a gramatica formal e decisoes de projeto.
- Criar `tests/fixtures/` caso os testes comecem a compartilhar muitos arquivos auxiliares.
- Usar `src/jss_compiler/` como pacote Python se o projeto crescer e precisar de imports mais organizados.
- Adicionar um arquivo `CHANGELOG.md` para registrar entregas e evolucao do compilador.
