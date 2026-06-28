import os
import sys
import subprocess
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
MAIN_PY = PROJECT_ROOT / "src" / "main.py"

def run_backend_test(test_name, jss_code, expected_output, input_data=None):
    print(f"\n========================================\nExecutando Teste: {test_name}")
    
    # Criar arquivo temporário com o código JSS
    with tempfile.TemporaryDirectory() as tmpdir:
        jss_file = Path(tmpdir) / f"{test_name}.jss"
        jss_file.write_text(jss_code, encoding="utf-8")
        
        # 1. Compilar usando nosso main.py
        print("Compilando código JSS...")
        res_comp = subprocess.run(
            [sys.executable, str(MAIN_PY), str(jss_file)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        if res_comp.returncode != 0:
            print("FALHA na compilação!")
            print("Stdout:", res_comp.stdout)
            print("Stderr:", res_comp.stderr)
            return False
            
        print("Compilação concluída com sucesso.")
        
        # Localizar o executável gerado
        exe_ext = ".exe" if os.name == 'nt' else ""
        exe_file = Path(tmpdir) / f"{test_name}{exe_ext}"
        
        if not exe_file.exists():
            print(f"Erro: O executável '{exe_file}' não foi encontrado.")
            return False
            
        # 2. Executar o binário nativo
        print("Executando binário nativo...")
        res_exec = subprocess.run(
            [str(exe_file)],
            input=input_data,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        if res_exec.returncode != 0:
            print(f"FALHA na execução! Código de retorno: {res_exec.returncode}")
            print("Stdout:", res_exec.stdout)
            print("Stderr:", res_exec.stderr)
            return False
            
        # 3. Comparar a saída
        actual = res_exec.stdout.strip().replace("\r\n", "\n")
        expected = expected_output.strip().replace("\r\n", "\n")
        
        # Substituir pequenas variações de formatação científica se necessário, 
        # mas por hora faremos comparação de strings.
        if actual == expected:
            print(f"SUCESSO! A saída coincide exatamente.")
            return True
        else:
            print(f"FALHA! A saída não coincide.")
            print("--- Esperado ---")
            print(expected)
            print("--- Obtido ---")
            print(actual)
            return False

def main():
    # Teste 1: Fatorial Recursivo
    code_fat = """
    function int fatorial(int fat) {
        if (fat > 1) {
            return fat * fatorial(fat - 1);
        } else {
            return 1;
        }
    }
    function void main() {
        console.log("Fatorial de 5:", fatorial(5));
    }
    """
    expected_fat = "Fatorial de 5: 120"
    
    # Teste 2: Média de Notas & Conversões (Casting)
    code_cast = """
    function void main() {
        let int n1 = 8;
        let int n2 = 7;
        let real n3 = 6.5;
        let real media = (real(n1) + real(n2) + n3) / 3.0;
        console.log("Media:", media);
        
        console.log("Casts:");
        console.log(int(3.9));
        console.log(int(true));
        console.log(real(10));
        console.log(real(true));
        console.log(bool(1));
        console.log(bool(0.0));
        console.log(str(10 + 5));
        console.log(str(true));
    }
    """
    expected_cast = """Media: 7.16667
Casts:
3
1
10
1
true
false
15
true"""

    # Teste 3: Classes, construtores e comparações nulas
    code_classes = """
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
    }
    function void main() {
        let Ponto p1 = new Ponto(10, 20);
        console.log("Ponto 1 soma:", p1.soma());
        
        let Ponto p2;
        if (p2 == null) {
            console.log("p2 is null");
        }
        p2 = new Ponto(30, 40);
        if (p2 != null) {
            console.log("p2 is not null now, soma:", p2.soma());
        }
    }
    """
    expected_classes = """Ponto 1 soma: 30
p2 is null
p2 is not null now, soma: 70"""

    # Teste 4: Vetores unidimensionais e bidimensionais
    code_arrays = """
    function void main() {
        let int[3] v = [10, 20, 30];
        console.log("v[0]:", v[0], "v[1]:", v[1], "v[2]:", v[2]);
        
        v[1] = 99;
        console.log("v[1] modificado:", v[1]);
        
        let int[2][3] m;
        m[0][0] = 1;
        m[0][1] = 2;
        m[0][2] = 3;
        m[1][0] = 4;
        m[1][1] = 5;
        m[1][2] = 6;
        
        console.log("m[0][0]:", m[0][0], "m[1][2]:", m[1][2]);
    }
    """
    expected_arrays = """v[0]: 10 v[1]: 20 v[2]: 30
v[1] modificado: 99
m[0][0]: 1 m[1][2]: 6"""

    success = True
    success &= run_backend_test("Teste 1 - Fatorial", code_fat, expected_fat)
    success &= run_backend_test("Teste 2 - Castings", code_cast, expected_cast)
    success &= run_backend_test("Teste 3 - Classes", code_classes, expected_classes)
    success &= run_backend_test("Teste 4 - Vetores", code_arrays, expected_arrays)
    
    print("\n========================================")
    if success:
        print("TODOS OS TESTES DO BACKEND PASSARAM COM SUCESSO!")
        sys.exit(0)
    else:
        print("ALGUNS TESTES DO BACKEND FALHARAM.")
        sys.exit(1)

if __name__ == "__main__":
    main()
