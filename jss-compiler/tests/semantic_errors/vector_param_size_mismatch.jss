function void test(int[5] a) {
    console.log(a[0]);
}

class Ponto3D {
    int[3] coordenadas;
    Ponto3D constructor(int[3] coords) {
        this.coordenadas[0] = coords[0];
        this.coordenadas[1] = coords[1];
        this.coordenadas[2] = coords[2];
    }
}

function void main() {
    let int[3] v3 = [1, 2, 3];
    test(v3); // Erro: esperado 5, mas obteve 3

    let int[5] v5 = [1, 2, 3, 4, 5];
    let Ponto3D p = new Ponto3D(v5); // Erro: esperado 3, mas obteve 5
}
