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

function void main() {
    let Retangulo r = new Retangulo(5, 10);
    console.log("Area do retangulo:", r.area());
}
