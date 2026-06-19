"""Ponto de entrada do compilador JSS.

Responsavel por receber arquivos via linha de comando e integrar as etapas de
analise lexica e sintatica utilizando a implementacao do Lexer integrado.
"""

import sys
import os
from frontend.parser import parser
from frontend.lexer import build_lexer, LexicalError
from frontend.errors import SyntacticError

def main():
    content = None

    # 1. Determinar a origem do código-fonte (argumento de arquivo, stdin redirecionado ou '-' flag)
    if len(sys.argv) >= 2:
        filepath = sys.argv[1]
        if filepath == "-":
            content = sys.stdin.read()
        else:
            if not os.path.exists(filepath):
                print(f"Erro: Arquivo '{filepath}' nao encontrado.")
                sys.exit(1)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"Erro ao ler o arquivo: {e}")
                sys.exit(1)
    else:
        # Se não há argumentos, checar se a entrada padrão está redirecionada/piped
        if not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            # Caso interativo sem argumentos: executa o teste demonstrativo padrão
            print("Uso: python src/main.py <caminho_do_arquivo.jss>")
            print("Ou: python src/main.py - (para ler interativamente do teclado ate EOF)")
            print("Ou: python src/main.py < arquivo.jss (para redirecionar um arquivo)")
            print("\nExecutando teste demonstrativo com codigo JSS valido (Classe + Funcao Recursiva)...")
            demo_code = """
        function int fatorial(int fat) {
            if (fat > 1) {
                console.log(fat);
                return fat * fatorial(fat - 1);
            } else {
                return 1;
            }
        }

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
            let int numero = 5;
            console.log("Fatorial de 5:", fatorial(numero));
            
            let Ponto p = new Ponto(10, 20);
            console.log("Soma das coordenadas:", p.soma());
        }
            """
            print("-" * 40)
            print("Código de Demonstração JSS:")
            print(demo_code)
            print("-" * 40)
            content = demo_code

    # 2. Executar a análise sobre o código obtido
    try:
        lexer = build_lexer()
        lexer.lineno = 1
        
        ast = parser.parse(content, lexer=lexer)
        if ast:
            # Para visualizar a AST resultante, descomente as linhas abaixo:
            # print("AST Resultante:")
            # print(ast.print_tree())
            print("Analise concluida com sucesso.")
        else:
            print("Erro: A AST nao pode ser gerada.")
            sys.exit(1)
    except LexicalError as le:
        # Tratamento do erro léxico do colega (abortando de imediato)
        print(f"Erro lexico: {le}")
        sys.exit(1)
    except SyntacticError as se:
        print(se)
        sys.exit(1)
    except Exception as e:
        print(f"Erro durante a analise: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
