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
    for (let int i = 0; i < 5; i++) {
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
