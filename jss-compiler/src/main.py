"""Ponto de entrada do compilador JSS.

Responsavel por receber arquivos via linha de comando e integrar as etapas de
analise lexica e sintatica utilizando a implementacao do Lexer integrado.

A etapa final (transformar o código LLVM IR gerado em um `.exe` nativo) usa
apenas duas ferramentas, nenhuma delas um compilador C:
1. `llvmlite.binding` - a própria LLVM, através da llvmlite, traduz o IR
   diretamente para código objeto x86-64 (o mesmo trabalho que antes era
   delegado ao Clang).
2. `ld.lld` - o linker do projeto LLVM (não compila nada, só junta o objeto
   gerado com bibliotecas do sistema já compiladas) transforma esse objeto
   no executável final.
"""

import sys
import os
import glob
import subprocess
import llvmlite.binding as llvm

from frontend.parser import parser
from frontend.lexer import build_lexer, LexicalError
from frontend.errors import SyntacticError, SemanticError
from frontend.semantic import SemanticAnalyzer
from backend.code_generator import CodeGenerator, TARGET_TRIPLE

# Prepara o backend nativo da LLVM (dentro da llvmlite) para o processador
# desta máquina. É preciso fazer isso uma única vez, antes de pedir para
# qualquer TargetMachine emitir código objeto.
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()


def _find_llvm_mingw_dir():
    """Localiza a pasta `llvm-mingw/` (kit portátil com o linker `ld.lld` e o
    runtime C do MinGW/Windows), subindo até 5 níveis de diretório a partir
    deste arquivo - a mesma estratégia de busca que antes era usada para
    encontrar um `clang.exe` portátil.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        candidate = os.path.join(current_dir, "llvm-mingw")
        if os.path.exists(os.path.join(candidate, "bin", "ld.lld.exe")):
            return candidate
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent
    return None


def _link_executable(mingw_dir, object_filepath, exe_filepath):
    """Invoca o `ld.lld.exe` do llvm-mingw para transformar o `.o` (gerado pela
    llvmlite) em um `.exe` do Windows.

    `ld.lld` é *só um linker*: ele não compila nenhum código-fonte, apenas
    junta peças já compiladas - o nosso objeto (`object_filepath`) com as
    bibliotecas prontas do runtime C do sistema (`msvcrt`, para `printf`,
    `scanf`, `malloc`, ...) e os arquivos de inicialização padrão do MinGW
    (`crt2.o`, que configura a pilha e chama `@main` ao iniciar o processo).
    Devolve o `subprocess.CompletedProcess` da chamada ao linker.
    """
    linker = os.path.join(mingw_dir, "bin", "ld.lld.exe")
    sysroot_lib = os.path.join(mingw_dir, "x86_64-w64-mingw32", "lib")
    # A versão do Clang embutida no llvm-mingw pode mudar; localizamos a pasta
    # de bibliotecas de runtime (`libclang_rt.builtins-x86_64.a`, que fornece
    # rotinas auxiliares internas do compilador, como `__chkstk_ms`) por
    # padrão em vez de fixar o número da versão.
    clang_rt_dirs = glob.glob(os.path.join(mingw_dir, "lib", "clang", "*", "lib", "windows"))

    cmd = [
        linker, "-m", "i386pep", "-o", exe_filepath,
        os.path.join(sysroot_lib, "crt2.o"),
        object_filepath,
        "-L", sysroot_lib,
    ]
    for d in clang_rt_dirs:
        cmd.extend(["-L", d])
    cmd.extend([
        "-lmingw32", "-lmingwex", "-lmsvcrt", "-lkernel32", "-lclang_rt.builtins-x86_64",
        "-e", "mainCRTStartup", "--subsystem", "console",
    ])

    return subprocess.run(cmd, capture_output=True, text=True, errors="replace")


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
        ast = getattr(parser, 'last_ast', None)
    except SyntacticError as se:
        # A exceção já contém todos os erros léxicos/sintáticos agregados
        for err in str(se).strip().split("\n\n"):
            err = err.strip()
            if err:
                lex_syn_errors.append(err)
        has_error = True
        ast = getattr(parser, 'last_ast', None)

    # Fase 2: Análise Semântica (mesmo com erros léxicos/sintáticos, se a AST parcial existe)
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
        print("Analise semantica concluida com sucesso.")

        # Determinar nomes dos arquivos de saída
        input_filepath = "output.jss"
        if len(sys.argv) >= 2 and sys.argv[1] != "-":
            input_filepath = sys.argv[1]

        base_path, _ = os.path.splitext(input_filepath)
        llvm_filepath = base_path + ".ll"
        obj_filepath = base_path + ".o"
        # O backend gera executaveis nativos do Windows (PE/COFF, via ld.lld +
        # runtime do MinGW) - por isso a extensao .exe nao depende de plataforma.
        exe_filepath = base_path + ".exe"

        print("Gerando codigo LLVM IR...")
        try:
            generator = CodeGenerator()
            ir_module = generator.generate(ast)
            llvm_ir_text = str(ir_module)

            with open(llvm_filepath, 'w', encoding='utf-8') as f:
                f.write(llvm_ir_text)
            print(f"Codigo LLVM IR gerado com sucesso em '{llvm_filepath}'.")
        except Exception as e:
            print(f"Erro ao gerar codigo intermediario LLVM IR: {e}")
            sys.exit(1)

        print("Compilando executavel nativo...")

        # Etapa 1: traduzir o IR para código objeto x86-64 nativo usando o
        # backend da própria LLVM (via llvmlite.binding) - sem invocar
        # nenhum compilador C. `parse_assembly` + `verify()` reconstrói o
        # módulo a partir do texto do `.ll` e confirma que ele é válido
        # antes de gerar código de máquina a partir dele.
        try:
            binding_module = llvm.parse_assembly(llvm_ir_text)
            binding_module.verify()
        except RuntimeError as e:
            print("Erro: o codigo LLVM IR gerado pelo compilador e invalido:")
            print(e)
            sys.exit(1)

        target_machine = llvm.Target.from_triple(TARGET_TRIPLE).create_target_machine(codemodel='small')
        object_bytes = target_machine.emit_object(binding_module)
        with open(obj_filepath, 'wb') as f:
            f.write(object_bytes)

        # Etapa 2: linkar o objeto contra o runtime C do sistema usando o
        # linker ld.lld (parte do projeto LLVM, não um compilador C).
        mingw_dir = _find_llvm_mingw_dir()
        if mingw_dir is None:
            print("\n" + "!" * 50)
            print("AVISO: O executavel nao pode ser gerado porque a pasta 'llvm-mingw' nao foi encontrada.")
            print("Essa pasta traz o linker (ld.lld) e o runtime C do MinGW usados para gerar o .exe final.")
            print("Restaure a pasta 'llvm-mingw' na raiz do projeto e execute novamente o compilador.")
            print("!" * 50)
            sys.exit(1)

        res = _link_executable(mingw_dir, obj_filepath, exe_filepath)
        if res.returncode == 0:
            print(f"Compilacao concluida com sucesso! Executavel gerado em '{exe_filepath}'.")
        else:
            print("Erro no link do executavel:")
            print(res.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
