function void main() {
    let int[3] vetor;
    
    // Acessos invalidos constantes (escrita)
    vetor[3] = 10;  // Erro: fora dos limites (tamanho eh 3)
    vetor[-1] = 5;  // Erro: indice negativo
    
    // Acessos invalidos constantes (leitura)
    let int x = vetor[5]; // Erro: fora dos limites
    
    // Acessos validos
    vetor[0] = 1;
    vetor[1] = 2;
    vetor[2] = 3;
    
    // Teste com matriz multidimensional
    let int[2][3] matriz;
    matriz[0][3] = 100; // Erro: fora dos limites (tamanho eh 3)
}
