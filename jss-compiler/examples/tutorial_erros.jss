// =====================================================================
// JSS COMPILER - DESAFIO DOS ERROS SINTÁTICOS
//
// Rode o comando: python src/main.py examples/tutorial_erros.jss
//
// O compilador parará no primeiro erro. Corrija-o seguindo a recomendação,
// salve o arquivo e execute novamente para ir para o próximo desafio!
// =====================================================================

// [Desafio 1] Erro: Declaração de variável sem a palavra-chave 'let'
int erro1 = 10;

// [Desafio 2] Erro: Vetor declarado com colchetes no lugar errado (sintaxe C/Java)
let real erro2[5];

// [Desafio 3] Erro: Falta de tipo na declaração da variável
let erro3 = 20;

// [Desafio 4] Erro: Métodos de classe declarados antes do construtor
class Retangulo {
    int largura;
    
    int area() {
        return this.largura;
    }
    
    Retangulo constructor(int w) {
        this.largura = w;
    }
}

// [Desafio 5] Erro: Operador pós-fixado 'i++' (JSS exige pré-fixado '++i')
function void testFor() {
    for (let int i = 0; i < 5; i++) {
        console.log(i);
    }
}

// [Desafio 6] Erro: Falta do ponto e vírgula ';' no final da instrução
function void testSemicolon() {
    let int z = 100
}

// [Desafio 7] Erro: Bloco aberto sem fechar as chaves '}' correspondentes
function void testUnbalanced() {
    if (true) {
        console.log("bloco aberto");
    // Faltam os fechamentos '}' do 'if' e da função 'testUnbalanced'
