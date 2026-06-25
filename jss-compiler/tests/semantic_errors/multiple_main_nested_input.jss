function void main(int arg) { 
    // Erro 1: a funcao 'main' nao deve possuir parametros.

    function void nested() {} 
    // Erro 2: declaracao de funcoes aninhadas nao e permitida.
    
    let bool b;
    input(b); 
    // Erro 3: input nao pode ler para tipo 'bool'. Apenas inteiros, reais e strings sao permitidos.
}
