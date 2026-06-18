class Ponto {
    int x;
    int y;

    Ponto constructor(int x, int y) {
        this.x = x;
        this.y = y;
    }

    int soma() {
        return this.x + this.y;
    }

    int desloca(int dx, int dy) {
        return this.x + dx + this.y + dy;
    }
}

function void main() {
    let Ponto p = new Ponto(1, 2);
    console.log(p.x, p.y, p.soma(), p.desloca(3, 4));
}
