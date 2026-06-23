// =====================================================================
// JSS COMPILER - DESAFIO UNIFICADO DE ERROS (LÉXICOS, SINTÁTICOS E SEMÂNTICOS)
//
// Regras do jogo:
// 1. Rode o comando: python src/main.py examples/tutorial_erros.jss
// 2. O compilador acusará o primeiro erro. Corrija-o seguindo as dicas do comentário.
// 3. Salve o arquivo e rode novamente.
// 4. Repita até o programa compilar com sucesso!
// =====================================================================

// [Desafio Léxico 1]
/* comentário multilinha*/

// [Desafio Sintático 1]
class Retangulo {
    int largura;
    int altura;

    int area() {
        return this.largura * this.altura;
    }

    Retangulo constructor(int w, int h) {
        this.largura = w;
        this.altura = h;
    }
}

// [Desafio Semântico 1]
function void testGlobal() {
    let int valor_this = this.largura; 
}

// [Desafio Léxico 2]
let int caractere_invalido = @;

function int calcular(int limite) {
    // [Desafio Sintático 2 e 3] 
    for (let int i = 0; i < limite; i++ {
        console.log(i);
    }
    return limite;
}

function void main() {
    // [Desafio Sintático 4]
    int numero = 10;

    // [Desafio Sintático 5]
    let real notas[5];

    // [Desafio Sintático 6]
    let sem_tipo = 100;

    // [Desafio Sintático 7]
    let str texto_aviso = "Executando compilador"

    // [Desafio Léxico 3]
    let str string_invalida = "Texto com escape inválido:\t";

    // [Desafio Léxico 4]
    let str string_aberta = "Minha string sem fechar;

    // [Desafio Léxico 5]
    let int 1variavel = 5;

    // [Desafio Léxico 6]
    let bool status = true;
    status &&= false;

    // [Desafio Semântico 2]
    let int total = 10;
    let int total = 20;

    // [Desafio Semântico 3]
    const real PI = 3.14;
    PI = 3.1415;

    // [Desafio Semântico 4]
    let int idade = 18;
    idade = "dezoito";

    // [Desafio Semântico 5]
    variavel_fantasma = 42;

    // [Desafio Semântico 6]
    let int[3] valores = [1, 2, 3];
    valores = [4, 5, 6];

    // [Desafio Semântico 7]
    if (100) {
        console.log("Número não é booleano!");
    }
}
