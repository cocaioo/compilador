// =====================================================================
// JSS COMPILER - DESAFIO DOS ERROS LÉXICOS E SINTÁTICOS
//
// Rode o comando: python jss-compiler/src/main.py jss-compiler/examples/tutorial_erros.jss
//
// O compilador parará no primeiro erro encontrado. Corrija-o seguindo a
// recomendação do comentário, salve o arquivo e execute novamente
// para prosseguir até o final do tutorial!
// =====================================================================

// =====================================================================
// ETAPA 1: ERROS LÉXICOS
// =====================================================================

// [Desafio Léxico 1] Erro: Caractere inválido
let int erro_lexico1 = @;

// [Desafio Léxico 2] Erro: Comentários multilinha não permitidos
/*corrigido*/

// [Desafio Léxico 3] Erro: Identificador começando com dígito
let int 1erro_lexico = 30;

// [Desafio Léxico 4] Erro: Escape inválido em string
let str erro_lexico4 = "Texto com escape inválido:\t";

// [Desafio Léxico 5] Erro: String não finalizada
let str erro_lexico5 = "Minha string sem fechar;

// [Desafio Léxico 6] Erro: Atribuição lógica composta (&&= ou ||=) não suportada
let bool erro_lexico6 = true;
erro_lexico6 &&= false;


// =====================================================================
// ETAPA 2: ERROS SINTÁTICOS
// =====================================================================

// [Desafio Sintático 1] Erro: Declaração de variável sem a palavra-chave 'let' ou 'const'
int erro1 = 10;

// [Desafio Sintático 2] Erro: Vetor declarado com colchetes no lugar errado (sintaxe C/Java)
let real erro2[5];

// [Desafio Sintático 3] Erro: Falta de tipo na declaração da variável
let erro3 = 20;

// [Desafio Sintático 4] Erro: Métodos de classe declarados antes do construtor e método errático
class Retangulo {
    }
    int largura;
    
    int area() {
        return this.largura;
    }
    Retangulo constructor(int w) {
        this.largura = w;
}

// [Desafio Sintático 5] Erro: Operador pós-fixado 'i++' (JSS exige pré-fixado '++i')
function void testFor() {
    for (let int i = 0; i < 5; i++ {
        console.log(i);
    }
}

// [Desafio Sintático 6] Erro: Falta do ponto e vírgula ';' no final da instrução
function void testSemicolon() {
    let int z = 100
}

// [Desafio Sintático 7] Erro: Bloco aberto sem fechar as chaves '}' correspondentes
function void testUnbalanced() {
    if (true) {
        console.log("bloco aberto");


// =====================================================================
// ETAPA 3: ERROS SEMÂNTICOS
// =====================================================================

// [Desafio Semântico 1] Erro: Redeclaração de variável no mesmo escopo
function void testRedeclaration() {
    let int x = 10;
    let int x = 20;
}

// [Desafio Semântico 2] Erro: Atribuição para constante
function void testConstReassign() {
    const real PI = 3.14;
    PI = 3.1415;
}

// [Desafio Semântico 3] Erro: Tipos incompatíveis (atribuição de string para int)
function void testTypeMismatch() {
    let int valor = 50;
    valor = "cinquenta";
}

// [Desafio Semântico 4] Erro: Identificador não declarado
function void testUndeclared() {
    variavel_inexistente = 42;
}

// [Desafio Semântico 5] Erro: Atribuição direta a um vetor fora da declaração
function void testDirectVectorAssign() {
    let int[3] vetor = [1, 2, 3];
    vetor = [4, 5, 6];
}

// [Desafio Semântico 6] Erro: Condição do 'if' deve ser do tipo 'bool'
function void testIfCondition() {
    if (123) {
        console.log("Número não é booleano!");
    }
}

// [Desafio Semântico 7] Erro: Uso do 'this' fora de métodos de classe
function void testInvalidThis() {
    let int self_val = this.x;
}

