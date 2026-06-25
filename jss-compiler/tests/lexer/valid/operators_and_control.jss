function int calcula(int a, int b) {
    let int diferenca = a - b;
    let int produto = a * b;
    let bool ok = !(a != b) && a <= b;

    while (a < b) {
        a += 1;
        if (b > a) {
            b = b - 1;
        }
        if (a == 3) {
            break;
        }
    }

    for (a = 0; a <= 10; a = a + 1) {
        b -= 1;
        b *= 2;
        b /= 2;
        b %= 2;
    }

    ok &&= true;
    ok ||= false;

    return (diferenca + produto + a) % 2;
}
