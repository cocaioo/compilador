"""Runtime de suporte do compilador JSS, escrito diretamente em LLVM IR.

Por que este arquivo existe
----------------------------
Um programa em JSS não consegue, sozinho, imprimir na tela, ler do teclado,
concatenar strings ou converter número em texto - essas operações dependem
do sistema operacional. Antes, elas viviam em `runtime.c`, um arquivo C
compilado pelo Clang e depois linkado junto com o código gerado a partir do
JSS.

Este módulo faz exatamente o mesmo trabalho, mas sem usar C em nenhum
momento: cada função do runtime (`print_int`, `str_concat`, `ipow`, etc.) é
construída como uma função LLVM IR de verdade, usando a mesma API
`llvmlite.ir` que o gerador de código principal (`code_generator.py`) usa
para compilar os programas dos usuários. O resultado final é equivalente ao
`runtime.c` antigo - só que, em vez de nascer como texto C e passar por um
compilador C, ele já nasce como IR, montado programaticamente pelo Python.

A única coisa "externa" de que ainda precisamos são funções prontas da
biblioteca C padrão do próprio sistema operacional (`printf`, `scanf`,
`malloc`, ...). Elas são apenas *declaradas* aqui (sem corpo) e resolvidas
em tempo de link contra a `msvcrt.dll` do Windows - isso é só reaproveitar
uma biblioteca do sistema, o mesmo que Rust, Go ou qualquer outra linguagem
compilada faz; não envolve compilar nenhum código C.
"""

import llvmlite.ir as ir

# --- Tipos LLVM usados no runtime (nomes curtos para deixar o código abaixo legível) ---
i1 = ir.IntType(1)          # booleano
i8 = ir.IntType(8)          # byte / char
i32 = ir.IntType(32)        # inteiro do JSS
i64 = ir.IntType(64)        # usado para tamanhos (size_t da libc)
f64 = ir.DoubleType()       # real do JSS
i8p = ir.PointerType(i8)    # "i8*": ponteiro de string (char*) do JSS
void = ir.VoidType()


def _zero32():
    """Atalho para a constante inteira 0 de 32 bits, usada em quase todo `getelementptr`."""
    return ir.Constant(i32, 0)


def _global_cstr(module, cache, text):
    """Devolve um ponteiro i8* constante para a string `text` (terminada em '\\0').

    Equivale, em texto LLVM IR, a declarar uma constante global:
        @nome = private unnamed_addr constant [N x i8] c"texto\\00"
    e depois pegar o endereço do seu primeiro byte com `getelementptr`.

    Como `GlobalVariable.gep(...)` é calculado em tempo de compilação (não
    depende de nenhuma instrução dentro de uma função), o ponteiro resultante
    pode ser usado como argumento de chamada em qualquer função do módulo,
    sem precisar de um `IRBuilder`.

    O parâmetro `cache` (um dict) evita criar duas constantes globais para o
    mesmo texto - se "%d" já foi criado antes, devolve o ponteiro existente.
    """
    if text in cache:
        return cache[text]

    data = bytearray((text + "\0").encode("utf8"))
    arr_ty = ir.ArrayType(i8, len(data))
    gv = ir.GlobalVariable(module, arr_ty, name=f"rt.str.{len(cache)}")
    gv.global_constant = True
    gv.linkage = "private"
    gv.unnamed_addr = True
    gv.initializer = ir.Constant(arr_ty, data)

    ptr = gv.gep([_zero32(), _zero32()])
    cache[text] = ptr
    return ptr


def _null_i8p():
    """Ponteiro nulo do tipo i8* (usado para checar strings vazias/ausentes)."""
    return ir.Constant(i8p, None)


def _declare_libc(module):
    """Declara as funções da biblioteca C padrão usadas pelo runtime do JSS.

    Isso é o equivalente LLVM de um `#include <stdio.h>` em C: dizemos que a
    função existe em algum lugar, com essa assinatura, mas sem fornecer o
    corpo dela. Quem resolve o endereço real (dentro da `msvcrt.dll`) é o
    linker (`ld.lld`), na etapa final de geração do executável.
    """
    libc = {}
    libc['printf'] = ir.Function(module, ir.FunctionType(i32, [i8p], var_arg=True), name="printf")
    libc['scanf'] = ir.Function(module, ir.FunctionType(i32, [i8p], var_arg=True), name="scanf")
    libc['sprintf'] = ir.Function(module, ir.FunctionType(i32, [i8p, i8p], var_arg=True), name="sprintf")
    libc['malloc'] = ir.Function(module, ir.FunctionType(i8p, [i64]), name="malloc")
    libc['strlen'] = ir.Function(module, ir.FunctionType(i64, [i8p]), name="strlen")
    libc['strcpy'] = ir.Function(module, ir.FunctionType(i8p, [i8p, i8p]), name="strcpy")
    libc['strcat'] = ir.Function(module, ir.FunctionType(i8p, [i8p, i8p]), name="strcat")
    libc['getchar'] = ir.Function(module, ir.FunctionType(i32, []), name="getchar")
    libc['exit'] = ir.Function(module, ir.FunctionType(void, [i32]), name="exit")
    return libc


# --- Funções auxiliares internas (não são chamadas diretamente pelo código JSS) ---

def _build_clear_input_buffer(module, libc):
    """`__jss_rt_clear_input_buffer()`: descarta o resto de uma linha de entrada inválida.

    Quando `scanf` falha em interpretar o que o usuário digitou (ex.: texto
    onde se esperava um número), os caracteres problemáticos continuam
    esperando no buffer de entrada. Sem descartá-los, a próxima leitura
    encontraria o mesmo lixo e falharia de novo, travando o programa num
    loop infinito. Esta função consome caracteres com `getchar()` até achar
    uma quebra de linha (código 10) ou o fim da entrada / EOF (código -1).
    """
    fn = ir.Function(module, ir.FunctionType(void, []), name="__jss_rt_clear_input_buffer")
    fn.linkage = "internal"

    entry = fn.append_basic_block("entry")
    loop = fn.append_basic_block("loop")
    end = fn.append_basic_block("end")

    builder = ir.IRBuilder(entry)
    builder.branch(loop)

    builder = ir.IRBuilder(loop)
    c = builder.call(libc['getchar'], [])
    is_newline = builder.icmp_signed('==', c, ir.Constant(i32, 10))
    is_eof = builder.icmp_signed('==', c, ir.Constant(i32, -1))
    should_stop = builder.or_(is_newline, is_eof)
    builder.cbranch(should_stop, end, loop)

    builder = ir.IRBuilder(end)
    builder.ret_void()

    return fn


def _build_strdup(module, libc):
    """`__jss_rt_strdup(i8* src) -> i8*`: copia uma string para o heap.

    Substitui o `strdup`/`_strdup` do C (que nem sempre existe com esse
    nome, dependendo do runtime C do sistema) por uma implementação própria:
    aloca `strlen(src) + 1` bytes com `malloc` e copia o conteúdo com
    `strcpy`. É usada sempre que uma função do runtime precisa devolver uma
    string que sobreviva ao retorno da função (buffers criados com `alloca`
    são destruídos assim que a função termina).
    """
    fn = ir.Function(module, ir.FunctionType(i8p, [i8p]), name="__jss_rt_strdup")
    fn.linkage = "internal"
    fn.args[0].name = "src"

    entry = fn.append_basic_block("entry")
    alloc_ok = fn.append_basic_block("alloc_ok")
    alloc_fail = fn.append_basic_block("alloc_fail")

    builder = ir.IRBuilder(entry)
    src = fn.args[0]
    length = builder.call(libc['strlen'], [src])
    size = builder.add(length, ir.Constant(i64, 1))
    mem = builder.call(libc['malloc'], [size])
    is_null = builder.icmp_unsigned('==', mem, _null_i8p())
    builder.cbranch(is_null, alloc_fail, alloc_ok)

    # Falha de alocação é um erro fatal e raríssimo (sem memória disponível);
    # encerramos o processo em vez de propagar um ponteiro nulo adiante.
    builder = ir.IRBuilder(alloc_fail)
    builder.call(libc['exit'], [ir.Constant(i32, 1)])
    builder.unreachable()

    builder = ir.IRBuilder(alloc_ok)
    builder.call(libc['strcpy'], [mem, src])
    builder.ret(mem)

    return fn


# --- Funções públicas do runtime (chamadas pelo código gerado a partir do JSS) ---

def _build_print_int(module, libc, strs):
    """`print_int(i32)`: imprime um inteiro decimal, sem quebra de linha."""
    fn = ir.Function(module, ir.FunctionType(void, [i32]), name="print_int")
    fn.args[0].name = "val"
    builder = ir.IRBuilder(fn.append_basic_block("entry"))
    # `console.log` chama esta função quando a expressão avaliada é um inteiro.
    fmt = _global_cstr(module, strs, "%d")
    builder.call(libc['printf'], [fmt, fn.args[0]])
    builder.ret_void()
    return fn


def _build_print_real(module, libc, strs):
    """`print_real(double)`: imprime um real com '%g' (formato compacto, sem zeros à direita)."""
    fn = ir.Function(module, ir.FunctionType(void, [f64]), name="print_real")
    fn.args[0].name = "val"
    builder = ir.IRBuilder(fn.append_basic_block("entry"))
    # O backend escolhe este caminho quando a expressão de `console.log` tem tipo real.
    fmt = _global_cstr(module, strs, "%g")
    builder.call(libc['printf'], [fmt, fn.args[0]])
    builder.ret_void()
    return fn


def _build_print_str(module, libc, strs):
    """`print_str(i8*)`: imprime uma string, ignorando ponteiros nulos (string ausente)."""
    fn = ir.Function(module, ir.FunctionType(void, [i8p]), name="print_str")
    fn.args[0].name = "val"

    entry = fn.append_basic_block("entry")
    do_print = fn.append_basic_block("do_print")
    done = fn.append_basic_block("done")

    builder = ir.IRBuilder(entry)
    # Strings nulas são tratadas como ausência de texto e não devem quebrar o `printf`.
    is_null = builder.icmp_unsigned('==', fn.args[0], _null_i8p())
    builder.cbranch(is_null, done, do_print)

    builder = ir.IRBuilder(do_print)
    fmt = _global_cstr(module, strs, "%s")
    builder.call(libc['printf'], [fmt, fn.args[0]])
    builder.branch(done)

    builder = ir.IRBuilder(done)
    builder.ret_void()

    return fn


def _build_print_bool(module, libc, strs):
    """`print_bool(i1)`: imprime "true" ou "false" por extenso."""
    fn = ir.Function(module, ir.FunctionType(void, [i1]), name="print_bool")
    fn.args[0].name = "val"
    builder = ir.IRBuilder(fn.append_basic_block("entry"))
    # Em vez de montar um `if`, o runtime usa `select` para escolher a string.
    s_true = _global_cstr(module, strs, "true")
    s_false = _global_cstr(module, strs, "false")
    # `select` escolhe entre os dois ponteiros sem precisar de um `if` (branch) em IR.
    chosen = builder.select(fn.args[0], s_true, s_false)
    fmt = _global_cstr(module, strs, "%s")
    builder.call(libc['printf'], [fmt, chosen])
    builder.ret_void()
    return fn


def _build_print_space(module, libc, strs):
    """`print_space()`: imprime um único espaço (usado entre argumentos de `console.log`)."""
    fn = ir.Function(module, ir.FunctionType(void, []), name="print_space")
    builder = ir.IRBuilder(fn.append_basic_block("entry"))
    # Mantém a mesma separação visual que `console.log(a, b, c)` costuma ter.
    s = _global_cstr(module, strs, " ")
    builder.call(libc['printf'], [s])
    builder.ret_void()
    return fn


def _build_print_newline(module, libc, strs):
    """`print_newline()`: imprime uma quebra de linha (fim de cada `console.log`)."""
    fn = ir.Function(module, ir.FunctionType(void, []), name="print_newline")
    builder = ir.IRBuilder(fn.append_basic_block("entry"))
    # Toda chamada de `console.log` termina com nova linha.
    s = _global_cstr(module, strs, "\n")
    builder.call(libc['printf'], [s])
    builder.ret_void()
    return fn


def _build_read_int(module, libc, strs, clear_buf_fn):
    """`read_int() -> i32`: lê um inteiro do teclado via `scanf("%d", ...)`.

    Se a leitura falhar (o usuário digitou algo que não é um número inteiro),
    descarta o resto da linha (`__jss_rt_clear_input_buffer`) para evitar um
    loop de leitura travado, e devolve 0.
    """
    fn = ir.Function(module, ir.FunctionType(i32, []), name="read_int")

    entry = fn.append_basic_block("entry")
    fail = fn.append_basic_block("fail")
    done = fn.append_basic_block("done")

    builder = ir.IRBuilder(entry)
    slot = builder.alloca(i32, name="val")
    builder.store(ir.Constant(i32, 0), slot)
    fmt = _global_cstr(module, strs, "%d")
    n = builder.call(libc['scanf'], [fmt, slot])
    ok = builder.icmp_signed('==', n, ir.Constant(i32, 1))
    builder.cbranch(ok, done, fail)

    builder = ir.IRBuilder(fail)
    builder.call(clear_buf_fn, [])
    builder.branch(done)

    builder = ir.IRBuilder(done)
    builder.ret(builder.load(slot))

    return fn


def _build_read_real(module, libc, strs, clear_buf_fn):
    """`read_real() -> double`: mesma lógica de `read_int`, mas lendo um `double` com "%lf"."""
    fn = ir.Function(module, ir.FunctionType(f64, []), name="read_real")

    entry = fn.append_basic_block("entry")
    fail = fn.append_basic_block("fail")
    done = fn.append_basic_block("done")

    builder = ir.IRBuilder(entry)
    slot = builder.alloca(f64, name="val")
    builder.store(ir.Constant(f64, 0.0), slot)
    fmt = _global_cstr(module, strs, "%lf")
    n = builder.call(libc['scanf'], [fmt, slot])
    ok = builder.icmp_signed('==', n, ir.Constant(i32, 1))
    builder.cbranch(ok, done, fail)

    builder = ir.IRBuilder(fail)
    builder.call(clear_buf_fn, [])
    builder.branch(done)

    builder = ir.IRBuilder(done)
    builder.ret(builder.load(slot))

    return fn


def _build_read_str(module, libc, strs, clear_buf_fn, strdup_fn):
    """`read_str() -> i8*`: lê uma palavra (sem espaços) do teclado.

    Usa um buffer temporário de até 4095 caracteres (`alloca`) e devolve uma
    cópia no heap (via `__jss_rt_strdup`), já que o buffer local deixa de
    existir assim que a função retorna. Em caso de falha, devolve "".
    """
    fn = ir.Function(module, ir.FunctionType(i8p, []), name="read_str")

    entry = fn.append_basic_block("entry")
    ok_block = fn.append_basic_block("ok")
    fail_block = fn.append_basic_block("fail")

    builder = ir.IRBuilder(entry)
    buf = builder.alloca(ir.ArrayType(i8, 4096), name="buffer")
    buf_ptr = builder.gep(buf, [_zero32(), _zero32()], inbounds=True)
    fmt = _global_cstr(module, strs, "%4095s")
    n = builder.call(libc['scanf'], [fmt, buf_ptr])
    ok = builder.icmp_signed('==', n, ir.Constant(i32, 1))
    builder.cbranch(ok, ok_block, fail_block)

    builder = ir.IRBuilder(ok_block)
    builder.ret(builder.call(strdup_fn, [buf_ptr]))

    builder = ir.IRBuilder(fail_block)
    builder.call(clear_buf_fn, [])
    empty = _global_cstr(module, strs, "")
    builder.ret(builder.call(strdup_fn, [empty]))

    return fn


def _build_str_concat(module, libc, strs):
    """`str_concat(i8* s1, i8* s2) -> i8*`: concatena duas strings em uma nova, alocada no heap.

    Implementa o operador `+` entre strings do JSS. Ponteiros nulos (strings
    ausentes) são tratados como string vazia, para não travar em `strlen(NULL)`.
    """
    fn = ir.Function(module, ir.FunctionType(i8p, [i8p, i8p]), name="str_concat")
    fn.args[0].name = "s1"
    fn.args[1].name = "s2"

    entry = fn.append_basic_block("entry")
    builder = ir.IRBuilder(entry)

    empty = _global_cstr(module, strs, "")
    s1_is_null = builder.icmp_unsigned('==', fn.args[0], _null_i8p())
    src1 = builder.select(s1_is_null, empty, fn.args[0])
    s2_is_null = builder.icmp_unsigned('==', fn.args[1], _null_i8p())
    src2 = builder.select(s2_is_null, empty, fn.args[1])

    len1 = builder.call(libc['strlen'], [src1])
    len2 = builder.call(libc['strlen'], [src2])
    total_size = builder.add(builder.add(len1, len2), ir.Constant(i64, 1))

    alloc_ok = fn.append_basic_block("alloc_ok")
    alloc_fail = fn.append_basic_block("alloc_fail")
    mem = builder.call(libc['malloc'], [total_size])
    is_null = builder.icmp_unsigned('==', mem, _null_i8p())
    builder.cbranch(is_null, alloc_fail, alloc_ok)

    builder = ir.IRBuilder(alloc_fail)
    builder.call(libc['exit'], [ir.Constant(i32, 1)])
    builder.unreachable()

    builder = ir.IRBuilder(alloc_ok)
    builder.call(libc['strcpy'], [mem, src1])
    builder.call(libc['strcat'], [mem, src2])
    builder.ret(mem)

    return fn


def _build_int_to_str(module, libc, strs, strdup_fn):
    """`int_to_str(i32) -> i8*`: converte um inteiro para sua representação em texto."""
    fn = ir.Function(module, ir.FunctionType(i8p, [i32]), name="int_to_str")
    fn.args[0].name = "val"
    builder = ir.IRBuilder(fn.append_basic_block("entry"))
    buf = builder.alloca(ir.ArrayType(i8, 32), name="buf")
    buf_ptr = builder.gep(buf, [_zero32(), _zero32()], inbounds=True)
    fmt = _global_cstr(module, strs, "%d")
    builder.call(libc['sprintf'], [buf_ptr, fmt, fn.args[0]])
    builder.ret(builder.call(strdup_fn, [buf_ptr]))
    return fn


def _build_real_to_str(module, libc, strs, strdup_fn):
    """`real_to_str(double) -> i8*`: converte um real para texto, no formato compacto '%g'."""
    fn = ir.Function(module, ir.FunctionType(i8p, [f64]), name="real_to_str")
    fn.args[0].name = "val"
    builder = ir.IRBuilder(fn.append_basic_block("entry"))
    buf = builder.alloca(ir.ArrayType(i8, 64), name="buf")
    buf_ptr = builder.gep(buf, [_zero32(), _zero32()], inbounds=True)
    fmt = _global_cstr(module, strs, "%g")
    builder.call(libc['sprintf'], [buf_ptr, fmt, fn.args[0]])
    builder.ret(builder.call(strdup_fn, [buf_ptr]))
    return fn


def _build_bool_to_str(module, strs):
    """`bool_to_str(i1) -> i8*`: converte um booleano para "true"/"false".

    Diferente das outras conversões, aqui não é preciso alocar nada no heap:
    como o texto resultante é sempre um dos dois literais fixos - e strings
    em JSS são imutáveis, nunca modificadas depois de criadas - basta
    devolver o ponteiro para a constante global correspondente.
    """
    fn = ir.Function(module, ir.FunctionType(i8p, [i1]), name="bool_to_str")
    fn.args[0].name = "val"
    builder = ir.IRBuilder(fn.append_basic_block("entry"))
    s_true = _global_cstr(module, strs, "true")
    s_false = _global_cstr(module, strs, "false")
    builder.ret(builder.select(fn.args[0], s_true, s_false))
    return fn


def _build_ipow(module):
    """`ipow(i32 base, i32 exp) -> i32`: potência inteira (operador `**` do JSS).

    Implementa exponenciação rápida por elevação ao quadrado sucessiva
    ("exponentiation by squaring"), a mesma técnica usada no `runtime.c`
    original, em vez de chamar a função `pow` de ponto flutuante da libc
    (que introduziria erros de arredondamento em resultados inteiros).
    Para expoente negativo, o JSS define o resultado como 0.
    """
    fn = ir.Function(module, ir.FunctionType(i32, [i32, i32]), name="ipow")
    fn.args[0].name = "base"
    fn.args[1].name = "exp"

    entry = fn.append_basic_block("entry")
    negative_exp = fn.append_basic_block("negative_exp")
    loop_check = fn.append_basic_block("loop_check")
    loop_body = fn.append_basic_block("loop_body")
    loop_odd = fn.append_basic_block("loop_odd")
    loop_cont = fn.append_basic_block("loop_cont")
    end = fn.append_basic_block("end")

    builder = ir.IRBuilder(entry)
    base_slot = builder.alloca(i32, name="base.addr")
    exp_slot = builder.alloca(i32, name="exp.addr")
    result_slot = builder.alloca(i32, name="result")
    builder.store(fn.args[0], base_slot)
    builder.store(fn.args[1], exp_slot)
    builder.store(ir.Constant(i32, 1), result_slot)
    is_negative = builder.icmp_signed('<', fn.args[1], ir.Constant(i32, 0))
    builder.cbranch(is_negative, negative_exp, loop_check)

    builder = ir.IRBuilder(negative_exp)
    builder.ret(ir.Constant(i32, 0))

    # while (exp > 0) { ... }
    builder = ir.IRBuilder(loop_check)
    keep_going = builder.icmp_signed('>', builder.load(exp_slot), ir.Constant(i32, 0))
    builder.cbranch(keep_going, loop_body, end)

    # if (exp & 1) result *= base;
    builder = ir.IRBuilder(loop_body)
    is_odd_bit = builder.and_(builder.load(exp_slot), ir.Constant(i32, 1))
    is_odd = builder.icmp_signed('!=', is_odd_bit, ir.Constant(i32, 0))
    builder.cbranch(is_odd, loop_odd, loop_cont)

    builder = ir.IRBuilder(loop_odd)
    builder.store(builder.mul(builder.load(result_slot), builder.load(base_slot)), result_slot)
    builder.branch(loop_cont)

    # base *= base; exp >>= 1;
    builder = ir.IRBuilder(loop_cont)
    builder.store(builder.mul(builder.load(base_slot), builder.load(base_slot)), base_slot)
    builder.store(builder.ashr(builder.load(exp_slot), ir.Constant(i32, 1)), exp_slot)
    builder.branch(loop_check)

    builder = ir.IRBuilder(end)
    builder.ret(builder.load(result_slot))

    return fn


def build_runtime(module):
    """Injeta todas as funções de runtime do JSS dentro do módulo do programa.

    É chamada uma única vez, no início de `CodeGenerator.generate()`. A partir
    daí, o restante do gerador de código simplesmente chama essas funções
    (`builder.call(runtime['print_int'], [...])`) como se fossem funções JSS
    comuns. Programa do usuário e runtime moram no mesmo módulo LLVM, então
    não existe mais um "runtime.o" separado para linkar: é tudo uma coisa só,
    e nada disso passou por um compilador C.

    Devolve um dicionário {nome_da_função: ir.Function}, usado pelo gerador
    de código para localizar cada função do runtime pelo nome.
    """
    libc = _declare_libc(module)
    strs = {}  # cache de constantes de string do runtime (evita duplicar "%d", "%s", ...)

    clear_buf_fn = _build_clear_input_buffer(module, libc)
    strdup_fn = _build_strdup(module, libc)

    runtime = {
        'malloc': libc['malloc'],
        'print_int': _build_print_int(module, libc, strs),
        'print_real': _build_print_real(module, libc, strs),
        'print_str': _build_print_str(module, libc, strs),
        'print_bool': _build_print_bool(module, libc, strs),
        'print_space': _build_print_space(module, libc, strs),
        'print_newline': _build_print_newline(module, libc, strs),
        'read_int': _build_read_int(module, libc, strs, clear_buf_fn),
        'read_real': _build_read_real(module, libc, strs, clear_buf_fn),
        'read_str': _build_read_str(module, libc, strs, clear_buf_fn, strdup_fn),
        'str_concat': _build_str_concat(module, libc, strs),
        'int_to_str': _build_int_to_str(module, libc, strs, strdup_fn),
        'real_to_str': _build_real_to_str(module, libc, strs, strdup_fn),
        'bool_to_str': _build_bool_to_str(module, strs),
        'ipow': _build_ipow(module),
    }
    return runtime
