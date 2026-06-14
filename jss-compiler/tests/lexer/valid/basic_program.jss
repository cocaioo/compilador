// Programa valido para exercitar tokens principais do lexer.
function void main() {
    let int numero = 10;
    let real media = 10.5E2;
    let real expoente = 1E2;
    let str texto = "Ola\nmundo";
    let bool ativo = true;

    numero++;
    --numero;
    numero += 2;
    media = (media / 2.0) ** 2;

    if (ativo && numero >= 10 || false) {
        console.log("Resultado: ", texto, media);
    } else {
        input(numero);
    }
}
