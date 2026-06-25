function void main() {
    const int c = 10;
    
    // Erro 1: identificador 'x' nao declarado.
    let int a = x; 
    
    // Erro 2: tipos incompativeis: esperava 'str', mas obteve 'int'.
    let str s = 5; 
    
    // Erro 3: atribuicao para alvo constante 'c' nao e permitida.
    c = 20; 
}
