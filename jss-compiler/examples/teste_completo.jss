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
   let real[1][2] xy;
   xy[0][0] = x;
   xy[0][1] = y;
   let str verdadeiro = "verdadeiro, " + x + " eh maior que " + y ;
   let str falso = "falso, " + x + " eh menor que " + y ;

   if(int(xy[0][0]) > int(xy[0][1])){
      return verdadeiro;
   }
      return falso;
}

function void printar(str string){console.log(string + "mas olha aqui esse numero foda: " + 0869);}

function void main(){
   let real x,y;
   x = 10;
   y = 3;
   const int z = 2;

   for(let int i = 1; i < z; ++i){
      x += x*i;
      y += y*i;
   }

   let CalculosRetangulo calculo = new CalculosRetangulo(x, y);

   let str resultado = maiorque(calculo.perimetro(), calculo.area());
   //function void printar_interno(){console.log(resultado);}
   printar(resultado);
}
