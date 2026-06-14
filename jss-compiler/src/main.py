"""Ponto de entrada do compilador JSS.

Responsavel por receber arquivos via linha de comando e integrar as etapas de
analise lexica e sintatica utilizando a implementacao do Lexer integrado.
"""

import sys
import os
from frontend.parser import parser
from frontend.lexer import build_lexer, LexicalError

def main():
    if len(sys.argv) < 2:
        print("Uso: python src/main.py <caminho_do_arquivo.jss>")
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
        print("AST Resultante:")
        try:
            lexer = build_lexer()
            lexer.lineno = 1
            ast = parser.parse(demo_code, lexer=lexer)
            if ast:
                print(ast.print_tree())
                print("Analise concluida com sucesso.")
            else:
                print("Erro: AST não gerada.")
        except LexicalError as le:
            print(f"Erro lexico durante a analise: {le}")
        except Exception as e:
            print(f"Erro durante o parsing: {e}")
        return

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"Erro: Arquivo '{filepath}' nao encontrado.")
        sys.exit(1)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Erro ao ler o arquivo: {e}")
        sys.exit(1)

    try:
        lexer = build_lexer()
        lexer.lineno = 1
        ast = parser.parse(content, lexer=lexer)
        if ast:
            print("AST Resultante:")
            print(ast.print_tree())
            print("Analise concluida com sucesso.")
        else:
            print("Erro: A AST nao pode ser gerada.")
    except LexicalError as le:
        print(f"Erro lexico: {le}")
    except Exception as e:
        print(f"Erro durante a analise: {e}")

if __name__ == '__main__':
    main()
