#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

#ifdef _WIN32
#define strdup _strdup
#endif

// Funções de saída (console.log)
void print_int(int val) {
    printf("%d", val);
}

void print_real(double val) {
    // %g imprime de forma compacta (ex: 5.5 ou 1.2e+06) e sem zeros inúteis à direita
    printf("%g", val);
}

void print_str(const char* val) {
    if (val) {
        printf("%s", val);
    }
}

void print_bool(bool val) {
    printf(val ? "true" : "false");
}

void print_space() {
    printf(" ");
}

void print_newline() {
    printf("\n");
}

// Funções de entrada (input)
int read_int() {
    int val = 0;
    if (scanf("%d", &val) != 1) {
        // Limpar buffer em caso de erro de leitura para evitar loops infinitos
        int c;
        while ((c = getchar()) != '\n' && c != EOF);
    }
    return val;
}

double read_real() {
    double val = 0.0;
    if (scanf("%lf", &val) != 1) {
        int c;
        while ((c = getchar()) != '\n' && c != EOF);
    }
    return val;
}

char* read_str() {
    char buffer[4096];
    if (scanf("%4095s", buffer) != 1) {
        int c;
        while ((c = getchar()) != '\n' && c != EOF);
        return strdup("");
    }
    return strdup(buffer);
}

// Concatenação de strings
char* str_concat(const char* s1, const char* s2) {
    const char* src1 = s1 ? s1 : "";
    const char* src2 = s2 ? s2 : "";
    size_t len1 = strlen(src1);
    size_t len2 = strlen(src2);
    char* res = (char*)malloc(len1 + len2 + 1);
    if (!res) {
        fprintf(stderr, "Erro de alocação de memória na runtime (str_concat)\n");
        exit(1);
    }
    strcpy(res, src1);
    strcat(res, src2);
    return res;
}

// Conversões (Casting) para string
char* int_to_str(int val) {
    char buf[32];
    sprintf(buf, "%d", val);
    return strdup(buf);
}

char* real_to_str(double val) {
    char buf[64];
    sprintf(buf, "%g", val);
    return strdup(buf);
}

char* bool_to_str(bool val) {
    return strdup(val ? "true" : "false");
}

// Exponenciação de inteiros (operador **)
int ipow(int base, int exp) {
    if (exp < 0) return 0; // JSS foca em potências inteiras positivas
    int result = 1;
    while (exp > 0) {
        if (exp & 1) {
            result *= base;
        }
        base *= base;
        exp >>= 1;
    }
    return result;
}
