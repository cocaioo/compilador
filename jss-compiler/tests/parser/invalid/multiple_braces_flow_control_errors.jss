function void main() {
    let int x = 10;
    let int y = 20;

    // Erro 1: while com ponto e virgula em vez de chaves
    while (x < 10);

    // Erro 2: else-if com comando em vez de bloco entre chaves
    if (x > 0) {
        x = 1;
    } else if (y > 0)
        y = 2;

    // Erro 3: for com comando em vez de bloco entre chaves
    for (let int i = 0; i < 5; ++i)
        console.log(i);
}
