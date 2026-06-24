"""Ponto de entrada do compilador JSS.

Responsavel por receber arquivos via linha de comando e integrar as etapas de
analise lexica e sintatica utilizando a implementacao do Lexer integrado.
"""

import sys
import os
from frontend.parser import parser
from frontend.lexer import build_lexer, LexicalError
from frontend.errors import SyntacticError, SemanticError
from frontend.semantic import SemanticAnalyzer

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
    lex_syn_errors = []
    sem_errors = []
    has_error = False

    # Fase 1: Análise Léxica e Sintática
    lexer = build_lexer()
    lexer.lineno = 1
    ast = None

    try:
        ast = parser.parse(content, lexer=lexer)
    except LexicalError as le:
        msg = str(le)
        if "Erro" in msg and "\n" in msg:
            lex_syn_errors.append(msg)
        else:
            lex_syn_errors.append(f"Erro lexico: {le}")
        has_error = True
    except SyntacticError as se:
        # A exceção já contém todos os erros léxicos/sintáticos agregados
        for err in str(se).strip().split("\n\n"):
            err = err.strip()
            if err:
                lex_syn_errors.append(err)
        has_error = True

    # Fase 2: Análise Semântica (somente se a AST foi gerada)
    if ast:
        try:
            analyzer = SemanticAnalyzer()
            analyzer.source_code = content
            analyzer.analyze(ast)
        except SemanticError as sme:
            for err in str(sme).strip().split("\n\n"):
                err = err.strip()
                if err:
                    sem_errors.append(err)
            has_error = True
        except Exception as e:
            sem_errors.append(f"Erro durante a analise semantica: {e}")
            has_error = True
    elif not has_error:
        print("Erro: A AST nao pode ser gerada.")
        sys.exit(1)

    # 3. Relatório final
    if has_error:
        print("\n" + "=" * 50)
        print("        RELATÓRIO DE ERROS DE COMPILAÇÃO")
        print("=" * 50)

        if lex_syn_errors:
            print("\n[ERROS LÉXICOS / SINTÁTICOS] ---------------------")
            for err in lex_syn_errors:
                print(err)
                print()

        if sem_errors:
            print("[ERROS SEMÂNTICOS] -------------------------------")
            for err in sem_errors:
                print(err)
                print()

        sys.exit(1)
    else:
        print("Analise concluida com sucesso.")

if __name__ == '__main__':
    main()
