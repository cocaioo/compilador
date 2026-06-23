class CalculosRetangulo {
    real x;
    real y;

    CalculosRetangulo constructor(real x, real y) {
        this.x = x;
        this.y = y;
    }

    real area() {
        return this.x * this.y;
    }

    real perimetro() {
        return this.x *2 + this.y *2;
    }
}

function str maiorque(real x, real y){
   let real[2] xy = [x,y];
   let str verdadeiro = "verdadeiro, " + x + " é maior que " + y ;
   let str falso = "falso, " + x + " é menor que " + y ;

   if(int(xy[0]) > int(xy[1])){
      return verdadeiro;
   }
      return falso;
}

function void main(){
   let real x,y;
   x = 1.1;
   y = 0.3;
   const int z = 3;

   for(let int i = 1; i < z; ++i){
      x = x*i - x*(i - 1);
      y = y*i - y*(i - 1);
   }

   let CalculosRetangulo calculo = new CalculosRetangulo(x, y);

   let str resultado = maiorque(calculo.perimetro(), calculo.area());
   //function void printar(){console.log(resultado);}
}
