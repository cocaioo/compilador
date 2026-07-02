# Funções principais usadas em code_generator.py

Este arquivo resume as funções e métodos mais importantes usados no gerador de código do JSS. A ideia é ajudar a entender como a AST vira LLVM IR e, depois, como esse IR vira o executável final.

## Visão geral

O arquivo `code_generator.py` percorre a AST e usa a API do `llvmlite.ir` para montar instruções LLVM. O objeto central dessa montagem é o `IRBuilder`, que funciona como uma caneta de escrita do IR: ele aponta para o bloco atual e vai inserindo instruções nele.

Em termos práticos:

- a AST diz o que o programa quer fazer;
- o `CodeGenerator` decide como isso vira LLVM IR;
- o `IRBuilder` escreve as instruções dentro dos blocos básicos;
- o `runtime_ir.py` fornece funções prontas para operações como imprimir, ler e converter tipos.

## O que é `builder`

`builder` é a instância de `IRBuilder` que está sendo usada no momento.

Ele sempre aponta para um bloco básico atual. Quando o código chama algo como `builder.add(...)`, `builder.store(...)` ou `builder.cbranch(...)`, a instrução é inserida no bloco em que o builder está posicionado naquele instante.

Em outras palavras, o builder é o objeto que realmente escreve o IR.

## O que é `append_basic_block`

`append_basic_block` cria um novo bloco básico dentro da função atual.

Exemplo conceitual:

~~~text
entry -> while.cond -> while.body -> while.end
~~~

Esse método é muito usado em estruturas de controle como `if`, `while` e `for`, porque cada parte da lógica precisa de um bloco separado.

## O que é um bloco básico

Um bloco básico é um trecho de instruções que o LLVM trata como uma unidade de execução.

Ele tem duas regras principais:

- entra por um único ponto;
- sai por um único ponto, normalmente com um salto ou retorno no final.

Na prática, isso significa que dentro de um bloco básico as instruções são executadas em sequência até aparecer uma instrução que encerra o fluxo, como `branch`, `cbranch` ou `ret`.

No projeto, blocos como `while.cond`, `while.body` e `while.end` são blocos básicos diferentes criados para organizar o fluxo do programa.

Exemplo conceitual:

~~~text
entrada -> bloco de condição -> bloco do corpo -> bloco de saída
~~~

Resumo simples:

- `append_basic_block` cria o bloco;
- o `IRBuilder` escreve as instruções dentro dele;
- `branch` e `cbranch` ligam um bloco ao outro.

## Principais funções usadas

### `branch(destino)`

Cria um salto incondicional para outro bloco.

Uso típico:

- ir da entrada para a condição de um laço;
- voltar do corpo de um `while` para testar a condição de novo;
- sair de um bloco após terminar uma parte do controle de fluxo.

Em resumo: sempre que o fluxo precisa ir obrigatoriamente para outro bloco, usa-se `branch`.

### `cbranch(condicao, bloco_verdadeiro, bloco_falso)`

Cria um salto condicional.

Se a condição for verdadeira, o fluxo vai para o primeiro bloco. Se for falsa, vai para o segundo.

É uma das funções mais importantes para:

- `if`
- `while`
- curto-circuito de `&&` e `||`

### `alloca(tipo, name=...)`

Reserva espaço na pilha da função atual.

É usada para criar variáveis locais. Por exemplo, uma declaração como `let int x = 10;` normalmente vira um `alloca` para `x`, seguido de um `store` com o valor inicial.

### `load(ponteiro)`

Lê o valor guardado em um endereço.

Se uma variável foi armazenada com `alloca`, o `load` recupera o valor real dessa variável.

### `store(valor, ponteiro)`

Escreve um valor em um endereço.

É usado em:

- declarações com inicialização;
- atribuições como `x = y`;
- incrementos e decrementos;
- leitura de entrada com `input`.

### `call(funcao, argumentos)`

Gera uma chamada de função.

No projeto, isso aparece tanto para chamar funções do usuário quanto para chamar funções do runtime, como:

- `print_int`
- `print_real`
- `print_str`
- `read_int`
- `str_concat`
- `ipow`

### `gep(endereco, indices, inbounds=True)`

Significa GetElementPtr.

Ele não lê o valor. Ele calcula o endereço de um elemento dentro de um vetor ou de um campo dentro de uma struct.

Uso típico no projeto:

- acessar `v[i]`;
- acessar `objeto.atributo`;
- navegar em arrays multidimensionais.

### `phi(tipo)`

Cria um nó phi.

O phi é usado quando o valor final depende de por qual bloco o fluxo chegou. Ele aparece principalmente em:

- curto-circuito de `&&` e `||`;
- atribuições lógicas compostas como `&&=` e `||=`.

### `ret(valor)` e `ret_void()`

Finalizam a função atual.

- `ret(valor)` retorna um valor;
- `ret_void()` termina uma função sem retorno.

## Mapeamento rápido por uso

### Controle de fluxo

- `append_basic_block`: cria os blocos
- `branch`: salto incondicional
- `cbranch`: salto condicional
- `phi`: junta caminhos diferentes

### Variáveis e memória

- `alloca`: cria variável local
- `load`: lê valor do endereço
- `store`: grava valor no endereço

### Acesso a dados compostos

- `gep`: calcula endereço de vetor ou atributo

### Chamadas e runtime

- `call`: chama funções do usuário ou do runtime
- `ret` e `ret_void`: encerram funções

## Como isso aparece no projeto

Alguns exemplos diretos no `code_generator.py`:

- `visit_WhileNode` usa `append_basic_block`, `branch` e `cbranch` para montar o laço.
- `visit_IfNode` cria blocos para then, else e merge.
- `visit_VarDeclarationNode` usa `alloca` e `store`.
- `visit_AssignmentNode` usa `load` e `store`.
- `visit_ArrayAccessNode` e `visit_AttributeAccessNode` usam `gep`.
- `visit_ConsoleLogNode` usa `call` para as funções do runtime.

## Resumo final

Se quiser guardar uma ideia simples, pense assim:

- o parser monta a AST;
- o `CodeGenerator` percorre a AST;
- o `IRBuilder` escreve o LLVM IR bloco por bloco;
- `branch` e `cbranch` controlam o fluxo;
- `alloca`, `load` e `store` controlam memória;
- `gep` calcula endereços;
- `call` chama funções;
- `phi` resolve valores que chegam de caminhos diferentes.

Em uma frase: o `code_generator.py` transforma a estrutura lógica da linguagem JSS em blocos e instruções LLVM, e o `runtime_ir.py` fornece as funções prontas que o programa usa para entrada, saída e conversões.