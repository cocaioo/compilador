	.def	@feat.00;
	.scl	3;
	.type	0;
	.endef
	.globl	@feat.00
.set @feat.00, 0
	.file	"<string>"
	.def	__jss_rt_clear_input_buffer;
	.scl	3;
	.type	32;
	.endef
	.text
	.p2align	4
__jss_rt_clear_input_buffer:
.seh_proc __jss_rt_clear_input_buffer
	subq	$40, %rsp
	.seh_stackalloc 40
	.seh_endprologue
	.p2align	4
.LBB0_1:
	callq	getchar
	cmpl	$10, %eax
	je	.LBB0_3
	cmpl	$-1, %eax
	jne	.LBB0_1
.LBB0_3:
	addq	$40, %rsp
	retq
	.seh_endproc

	.def	__jss_rt_strdup;
	.scl	3;
	.type	32;
	.endef
	.p2align	4
__jss_rt_strdup:
.seh_proc __jss_rt_strdup
	pushq	%rsi
	.seh_pushreg %rsi
	subq	$32, %rsp
	.seh_stackalloc 32
	.seh_endprologue
	movq	%rcx, %rsi
	callq	strlen
	leaq	1(%rax), %rcx
	callq	malloc
	testq	%rax, %rax
	je	.LBB1_2
	movq	%rax, %rcx
	movq	%rsi, %rdx
	movq	%rax, %rsi
	callq	strcpy
	movq	%rsi, %rax
	addq	$32, %rsp
	popq	%rsi
	retq
.LBB1_2:
	movl	$1, %ecx
	callq	exit
	int3
	.seh_endproc

	.def	print_int;
	.scl	2;
	.type	32;
	.endef
	.globl	print_int
	.p2align	4
print_int:
.seh_proc print_int
	subq	$40, %rsp
	.seh_stackalloc 40
	.seh_endprologue
	movl	%ecx, %edx
	leaq	.Lrt.str.0(%rip), %rcx
	callq	printf
	nop
	addq	$40, %rsp
	retq
	.seh_endproc

	.def	print_real;
	.scl	2;
	.type	32;
	.endef
	.globl	print_real
	.p2align	4
print_real:
.seh_proc print_real
	subq	$40, %rsp
	.seh_stackalloc 40
	.seh_endprologue
	leaq	.Lrt.str.1(%rip), %rcx
	movdqa	%xmm0, %xmm1
	movq	%xmm0, %rdx
	callq	printf
	nop
	addq	$40, %rsp
	retq
	.seh_endproc

	.def	print_str;
	.scl	2;
	.type	32;
	.endef
	.globl	print_str
	.p2align	4
print_str:
.seh_proc print_str
	subq	$40, %rsp
	.seh_stackalloc 40
	.seh_endprologue
	testq	%rcx, %rcx
	je	.LBB4_2
	movq	%rcx, %rdx
	leaq	.Lrt.str.2(%rip), %rcx
	callq	printf
.LBB4_2:
	nop
	addq	$40, %rsp
	retq
	.seh_endproc

	.def	print_bool;
	.scl	2;
	.type	32;
	.endef
	.globl	print_bool
	.p2align	4
print_bool:
.seh_proc print_bool
	subq	$40, %rsp
	.seh_stackalloc 40
	.seh_endprologue
	leaq	.Lrt.str.3(%rip), %rax
	leaq	.Lrt.str.4(%rip), %rdx
	testb	$1, %cl
	cmovneq	%rax, %rdx
	leaq	.Lrt.str.2(%rip), %rcx
	callq	printf
	nop
	addq	$40, %rsp
	retq
	.seh_endproc

	.def	print_space;
	.scl	2;
	.type	32;
	.endef
	.globl	print_space
	.p2align	4
print_space:
.seh_proc print_space
	subq	$40, %rsp
	.seh_stackalloc 40
	.seh_endprologue
	leaq	.Lrt.str.5(%rip), %rcx
	callq	printf
	nop
	addq	$40, %rsp
	retq
	.seh_endproc

	.def	print_newline;
	.scl	2;
	.type	32;
	.endef
	.globl	print_newline
	.p2align	4
print_newline:
.seh_proc print_newline
	subq	$40, %rsp
	.seh_stackalloc 40
	.seh_endprologue
	leaq	.Lrt.str.6(%rip), %rcx
	callq	printf
	nop
	addq	$40, %rsp
	retq
	.seh_endproc

	.def	read_int;
	.scl	2;
	.type	32;
	.endef
	.globl	read_int
	.p2align	4
read_int:
.seh_proc read_int
	subq	$40, %rsp
	.seh_stackalloc 40
	.seh_endprologue
	movl	$0, 36(%rsp)
	leaq	.Lrt.str.0(%rip), %rcx
	leaq	36(%rsp), %rdx
	callq	scanf
	cmpl	$1, %eax
	je	.LBB8_2
	callq	__jss_rt_clear_input_buffer
.LBB8_2:
	movl	36(%rsp), %eax
	addq	$40, %rsp
	retq
	.seh_endproc

	.def	read_real;
	.scl	2;
	.type	32;
	.endef
	.globl	read_real
	.p2align	4
read_real:
.seh_proc read_real
	subq	$40, %rsp
	.seh_stackalloc 40
	.seh_endprologue
	movq	$0, 32(%rsp)
	leaq	.Lrt.str.7(%rip), %rcx
	leaq	32(%rsp), %rdx
	callq	scanf
	cmpl	$1, %eax
	je	.LBB9_2
	callq	__jss_rt_clear_input_buffer
.LBB9_2:
	movsd	32(%rsp), %xmm0
	addq	$40, %rsp
	retq
	.seh_endproc

	.def	read_str;
	.scl	2;
	.type	32;
	.endef
	.globl	read_str
	.p2align	4
read_str:
.seh_proc read_str
	movl	$4136, %eax
	callq	___chkstk_ms
	subq	%rax, %rsp
	.seh_stackalloc 4136
	.seh_endprologue
	leaq	.Lrt.str.8(%rip), %rcx
	leaq	40(%rsp), %rdx
	callq	scanf
	cmpl	$1, %eax
	jne	.LBB10_3
	leaq	40(%rsp), %rcx
	jmp	.LBB10_2
.LBB10_3:
	callq	__jss_rt_clear_input_buffer
	leaq	.Lrt.str.9(%rip), %rcx
.LBB10_2:
	callq	__jss_rt_strdup
	nop
	addq	$4136, %rsp
	retq
	.seh_endproc

	.def	str_concat;
	.scl	2;
	.type	32;
	.endef
	.globl	str_concat
	.p2align	4
str_concat:
.seh_proc str_concat
	pushq	%rsi
	.seh_pushreg %rsi
	pushq	%rdi
	.seh_pushreg %rdi
	pushq	%rbx
	.seh_pushreg %rbx
	subq	$32, %rsp
	.seh_stackalloc 32
	.seh_endprologue
	movq	%rdx, %rsi
	movq	%rcx, %rdi
	testq	%rcx, %rcx
	leaq	.Lrt.str.9(%rip), %rax
	cmoveq	%rax, %rdi
	testq	%rdx, %rdx
	cmoveq	%rax, %rsi
	movq	%rdi, %rcx
	callq	strlen
	movq	%rax, %rbx
	movq	%rsi, %rcx
	callq	strlen
	leaq	1(%rbx,%rax), %rcx
	callq	malloc
	testq	%rax, %rax
	je	.LBB11_2
	movq	%rax, %rcx
	movq	%rdi, %rdx
	movq	%rax, %rdi
	callq	strcpy
	movq	%rdi, %rcx
	movq	%rsi, %rdx
	callq	strcat
	movq	%rdi, %rax
	addq	$32, %rsp
	popq	%rbx
	popq	%rdi
	popq	%rsi
	retq
.LBB11_2:
	movl	$1, %ecx
	callq	exit
	int3
	.seh_endproc

	.def	int_to_str;
	.scl	2;
	.type	32;
	.endef
	.globl	int_to_str
	.p2align	4
int_to_str:
.seh_proc int_to_str
	pushq	%rsi
	.seh_pushreg %rsi
	subq	$64, %rsp
	.seh_stackalloc 64
	.seh_endprologue
	movl	%ecx, %r8d
	leaq	.Lrt.str.0(%rip), %rdx
	leaq	32(%rsp), %rsi
	movq	%rsi, %rcx
	callq	sprintf
	movq	%rsi, %rcx
	callq	__jss_rt_strdup
	nop
	addq	$64, %rsp
	popq	%rsi
	retq
	.seh_endproc

	.def	real_to_str;
	.scl	2;
	.type	32;
	.endef
	.globl	real_to_str
	.p2align	4
real_to_str:
.seh_proc real_to_str
	pushq	%rsi
	.seh_pushreg %rsi
	subq	$96, %rsp
	.seh_stackalloc 96
	.seh_endprologue
	leaq	.Lrt.str.1(%rip), %rdx
	leaq	32(%rsp), %rsi
	movq	%rsi, %rcx
	movdqa	%xmm0, %xmm2
	movq	%xmm0, %r8
	callq	sprintf
	movq	%rsi, %rcx
	callq	__jss_rt_strdup
	nop
	addq	$96, %rsp
	popq	%rsi
	retq
	.seh_endproc

	.def	bool_to_str;
	.scl	2;
	.type	32;
	.endef
	.globl	bool_to_str
	.p2align	4
bool_to_str:
	leaq	.Lrt.str.3(%rip), %rdx
	leaq	.Lrt.str.4(%rip), %rax
	testb	$1, %cl
	cmovneq	%rdx, %rax
	retq

	.def	ipow;
	.scl	2;
	.type	32;
	.endef
	.globl	ipow
	.p2align	4
ipow:
.seh_proc ipow
	subq	$16, %rsp
	.seh_stackalloc 16
	.seh_endprologue
	movl	%ecx, 12(%rsp)
	movl	%edx, 8(%rsp)
	movl	$1, 4(%rsp)
	testl	%edx, %edx
	jns	.LBB15_4
	xorl	%eax, %eax
	addq	$16, %rsp
	retq
	.p2align	4
.LBB15_3:
	movl	12(%rsp), %eax
	imull	%eax, %eax
	movl	%eax, 12(%rsp)
	sarl	8(%rsp)
.LBB15_4:
	cmpl	$0, 8(%rsp)
	jle	.LBB15_7
	testb	$1, 8(%rsp)
	je	.LBB15_3
	movl	4(%rsp), %eax
	imull	12(%rsp), %eax
	movl	%eax, 4(%rsp)
	jmp	.LBB15_3
.LBB15_7:
	movl	4(%rsp), %eax
	addq	$16, %rsp
	retq
	.seh_endproc

	.def	main;
	.scl	2;
	.type	32;
	.endef
	.globl	main
	.p2align	4
main:
.seh_proc main
	pushq	%rbp
	.seh_pushreg %rbp
	pushq	%r15
	.seh_pushreg %r15
	pushq	%r14
	.seh_pushreg %r14
	pushq	%rsi
	.seh_pushreg %rsi
	pushq	%rdi
	.seh_pushreg %rdi
	pushq	%rbx
	.seh_pushreg %rbx
	pushq	%rax
	.seh_stackalloc 8
	movq	%rsp, %rbp
	.seh_setframe %rbp, 0
	.seh_endprologue
	subq	$32, %rsp
	callq	__main
	addq	$32, %rsp
	movl	$20, g_idade(%rip)
	xorl	%eax, %eax
	subq	$32, %rsp
	testb	%al, %al
	jne	.LBB16_2
	leaq	.Lstr.0(%rip), %rcx
	jmp	.LBB16_3
.LBB16_2:
	leaq	.Lstr.1(%rip), %rcx
.LBB16_3:
	callq	print_str
	callq	print_newline
	addq	$32, %rsp
	movl	$7, g_nota(%rip)
	movb	$1, %al
	testb	%al, %al
	jne	.LBB16_9
	subq	$32, %rsp
	leaq	.Lstr.2(%rip), %rcx
	jmp	.LBB16_5
.LBB16_9:
	cmpl	$6, g_nota(%rip)
	jle	.LBB16_10
	subq	$32, %rsp
	leaq	.Lstr.3(%rip), %rcx
	jmp	.LBB16_5
.LBB16_10:
	cmpl	$5, g_nota(%rip)
	jl	.LBB16_12
	subq	$32, %rsp
	leaq	.Lstr.4(%rip), %rcx
	jmp	.LBB16_5
.LBB16_12:
	subq	$32, %rsp
	leaq	.Lstr.5(%rip), %rcx
.LBB16_5:
	callq	print_str
	callq	print_newline
	addq	$32, %rsp
	movl	$0, g_soma(%rip)
	movl	$16, %eax
	callq	___chkstk_ms
	subq	%rax, %rsp
	movq	%rsp, %rax
	movl	$1, (%rax)
	cmpl	$10, (%rax)
	jg	.LBB16_13
	.p2align	4
.LBB16_7:
	movl	(%rax), %ecx
	addl	%ecx, g_soma(%rip)
	incl	(%rax)
	cmpl	$10, (%rax)
	jle	.LBB16_7
.LBB16_13:
	subq	$32, %rsp
	leaq	.Lstr.6(%rip), %rcx
	callq	print_str
	addq	$32, %rsp
	movl	g_soma(%rip), %esi
	subq	$32, %rsp
	callq	print_space
	movl	%esi, %ecx
	callq	print_int
	callq	print_newline
	addq	$32, %rsp
	movl	$16, %eax
	callq	___chkstk_ms
	subq	%rax, %rsp
	movq	%rsp, %r14
	movl	$0, (%r14)
	leaq	.Lstr.7(%rip), %rsi
	leaq	.Lstr.8(%rip), %rdi
	jmp	.LBB16_14
	.p2align	4
.LBB16_18:
	incl	(%r14)
.LBB16_14:
	cmpl	$2, (%r14)
	jg	.LBB16_19
	movl	$16, %eax
	callq	___chkstk_ms
	subq	%rax, %rsp
	movq	%rsp, %r15
	movl	$0, (%r15)
	cmpl	$1, (%r15)
	jg	.LBB16_18
	.p2align	4
.LBB16_17:
	subq	$32, %rsp
	movq	%rsi, %rcx
	callq	print_str
	addq	$32, %rsp
	movl	(%r14), %ebx
	subq	$32, %rsp
	callq	print_space
	movl	%ebx, %ecx
	callq	print_int
	callq	print_space
	movq	%rdi, %rcx
	callq	print_str
	addq	$32, %rsp
	movl	(%r15), %ebx
	subq	$32, %rsp
	callq	print_space
	movl	%ebx, %ecx
	callq	print_int
	callq	print_newline
	addq	$32, %rsp
	incl	(%r15)
	cmpl	$1, (%r15)
	jle	.LBB16_17
	jmp	.LBB16_18
.LBB16_19:
	movl	$16, %eax
	callq	___chkstk_ms
	subq	%rax, %rsp
	movq	%rsp, %r14
	movl	$0, (%r14)
	leaq	g_numeros(%rip), %r15
	leaq	.Lstr.9(%rip), %rsi
	leaq	.Lstr.10(%rip), %rdi
	cmpl	$4, (%r14)
	jg	.LBB16_22
	.p2align	4
.LBB16_21:
	movslq	(%r14), %rax
	movl	%eax, (%r15,%rax,4)
	subq	$32, %rsp
	movq	%rsi, %rcx
	callq	print_str
	addq	$32, %rsp
	movl	(%r14), %ebx
	subq	$32, %rsp
	callq	print_space
	movl	%ebx, %ecx
	callq	print_int
	callq	print_space
	movq	%rdi, %rcx
	callq	print_str
	addq	$32, %rsp
	movslq	(%r14), %rax
	movl	(%r15,%rax,4), %ebx
	subq	$32, %rsp
	callq	print_space
	movl	%ebx, %ecx
	callq	print_int
	callq	print_newline
	addq	$32, %rsp
	incl	(%r14)
	cmpl	$4, (%r14)
	jle	.LBB16_21
.LBB16_22:
	movl	$0, g_contador(%rip)
	leaq	.Lstr.11(%rip), %rsi
	cmpl	$4, g_contador(%rip)
	jg	.LBB16_25
	.p2align	4
.LBB16_24:
	subq	$32, %rsp
	movq	%rsi, %rcx
	callq	print_str
	addq	$32, %rsp
	movl	g_contador(%rip), %edi
	subq	$32, %rsp
	callq	print_space
	movl	%edi, %ecx
	callq	print_int
	callq	print_newline
	addq	$32, %rsp
	incl	g_contador(%rip)
	cmpl	$4, g_contador(%rip)
	jle	.LBB16_24
.LBB16_25:
	movl	$0, g_j(%rip)
	leaq	.Lstr.12(%rip), %rsi
	cmpl	$3, g_j(%rip)
	je	.LBB16_27
	.p2align	4
.LBB16_33:
	subq	$32, %rsp
	movq	%rsi, %rcx
	callq	print_str
	addq	$32, %rsp
	movl	g_j(%rip), %edi
	subq	$32, %rsp
	callq	print_space
	movl	%edi, %ecx
	callq	print_int
	callq	print_newline
	addq	$32, %rsp
	incl	g_j(%rip)
	cmpl	$3, g_j(%rip)
	jne	.LBB16_33
.LBB16_27:
	movl	$0, g_a(%rip)
	leaq	.Lstr.13(%rip), %rsi
	leaq	.Lstr.14(%rip), %rdi
	jmp	.LBB16_28
	.p2align	4
.LBB16_32:
	incl	g_a(%rip)
.LBB16_28:
	cmpl	$1, g_a(%rip)
	jg	.LBB16_34
	movl	$16, %eax
	callq	___chkstk_ms
	subq	%rax, %rsp
	movq	%rsp, %r14
	movl	$0, (%r14)
	cmpl	$2, (%r14)
	jg	.LBB16_32
	.p2align	4
.LBB16_31:
	subq	$32, %rsp
	movq	%rsi, %rcx
	callq	print_str
	addq	$32, %rsp
	movl	g_a(%rip), %ebx
	subq	$32, %rsp
	callq	print_space
	movl	%ebx, %ecx
	callq	print_int
	callq	print_space
	movq	%rdi, %rcx
	callq	print_str
	addq	$32, %rsp
	movl	(%r14), %ebx
	subq	$32, %rsp
	callq	print_space
	movl	%ebx, %ecx
	callq	print_int
	callq	print_newline
	addq	$32, %rsp
	incl	(%r14)
	cmpl	$2, (%r14)
	jle	.LBB16_31
	jmp	.LBB16_32
.LBB16_34:
	xorl	%eax, %eax
	leaq	8(%rbp), %rsp
	popq	%rbx
	popq	%rdi
	popq	%rsi
	popq	%r14
	popq	%r15
	popq	%rbp
	retq
	.seh_endproc

	.section	.rdata,"dr"
.Lrt.str.0:
	.asciz	"%d"

.Lrt.str.1:
	.asciz	"%g"

.Lrt.str.2:
	.asciz	"%s"

.Lrt.str.3:
	.asciz	"true"

.Lrt.str.4:
	.asciz	"false"

.Lrt.str.5:
	.asciz	" "

.Lrt.str.6:
	.asciz	"\n"

.Lrt.str.7:
	.asciz	"%lf"

.Lrt.str.8:
	.asciz	"%4095s"

.Lrt.str.9:
	.zero	1

	.bss
	.globl	g_idade
	.p2align	2, 0x0
g_idade:
	.long	0

	.section	.rdata,"dr"
.Lstr.0:
	.asciz	"Maior de idade"

.Lstr.1:
	.asciz	"Menor de idade"

	.bss
	.globl	g_nota
	.p2align	2, 0x0
g_nota:
	.long	0

	.section	.rdata,"dr"
.Lstr.2:
	.asciz	"A"

.Lstr.3:
	.asciz	"B"

.Lstr.4:
	.asciz	"C"

.Lstr.5:
	.asciz	"F"

	.bss
	.globl	g_soma
	.p2align	2, 0x0
g_soma:
	.long	0

	.section	.rdata,"dr"
.Lstr.6:
	.asciz	"Soma 1-10:"

.Lstr.7:
	.asciz	"x:"

.Lstr.8:
	.asciz	"y:"

	.bss
	.globl	g_numeros
	.p2align	4, 0x0
g_numeros:
	.zero	20

	.section	.rdata,"dr"
.Lstr.9:
	.asciz	"numeros["

.Lstr.10:
	.asciz	"]:"

	.bss
	.globl	g_contador
	.p2align	2, 0x0
g_contador:
	.long	0

	.section	.rdata,"dr"
.Lstr.11:
	.asciz	"Contador:"

	.bss
	.globl	g_j
	.p2align	2, 0x0
g_j:
	.long	0

	.section	.rdata,"dr"
.Lstr.12:
	.asciz	"j:"

	.bss
	.globl	g_a
	.p2align	2, 0x0
g_a:
	.long	0

	.section	.rdata,"dr"
.Lstr.13:
	.asciz	"a:"

.Lstr.14:
	.asciz	"b:"

