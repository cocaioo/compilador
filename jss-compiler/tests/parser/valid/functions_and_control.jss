function int soma(int a, int b) {
    return a + b;
}

function void executa_loop(int limite) {
    let int i = 0;
    while (i < limite) {
        if (i == 5) {
            const int z = 0;
            break;
        }
        console.log("i e: ", i);
        ++i;
    }
    
    let int j;
    for (j = 0; j < 10; ++j) {
        console.log("j e: ", j);
    }
}
