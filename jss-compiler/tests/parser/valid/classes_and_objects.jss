class Retangulo {
    int largura;
    int altura;
    
    Retangulo constructor(int w, int h) {
        this.largura = w;
        this.altura = h;
    }
    
    int area() {
        return this.largura * this.altura;
    }
}

class Quadrado {
    int lado;
    
    Quadrado constructor(int l) {
        this.lado = l;
    }
    
    int area() {
        return this.lado * this.lado;
    }
}

function void main() {
    let Retangulo r = new Retangulo(5, 10);
    let Quadrado q = new Quadrado(5);
    console.log("Area do retangulo:", r.area());
    console.log("Area do quadrado:", q.area());
}
