function void main() {
    let int a = 1;
    let int b = 2;
    let bool cond = true;
    let int[3] valores = [1, 2, 3];

    if (a < b) {
        console.log();
    } else if (a == b) {
        console.log("igual");
    } else {
        console.log("maior");
    }

    for (let int i = 0; i < 3; i += 1) {
        valores[i] = valores[i] + 1;
    }

    for (; ; ) {
        break;
    }

    input(a, b);
    a = int(3.9);
    b = real(true);
    cond = bool(0);
    console.log(str(a), valores[0]);
    return;
}
