"""Erros do compilador JSS.

Responsavel por centralizar classes e formatacao de mensagens de erro.
"""

class SyntacticError(Exception):
    """Erro encontrado durante a analise sintatica."""

def format_visual_error(source_code, error_class, message, line, lexpos):
    """Formata uma mensagem de erro visual com indicador do caret (^)."""
    if source_code is None:
        source_code = ""

    # Tratar caso de fim de arquivo ou lexpos fora dos limites
    if lexpos is None or lexpos < 0 or lexpos > len(source_code):
        lexpos = len(source_code)
    
    # Encontrar o inicio da linha contendo o lexpos
    line_start = source_code.rfind('\n', 0, lexpos) + 1
    # Encontrar o fim da linha
    line_end = source_code.find('\n', lexpos)
    if line_end == -1:
        line_content = source_code[line_start:]
    else:
        line_content = source_code[line_start:line_end]
        
    line_content_clean = line_content.rstrip('\r\n')
    
    # Calcular a coluna (1-based)
    column = (lexpos - line_start) + 1
    
    # Criar prefixo de linha formatado
    line_prefix = f" {line} | "
    
    # Montar o padding respeitando tabulacoes da linha original para alinhamento correto do caret
    padding_chars = []
    for i in range(column - 1):
        if i < len(line_content_clean) and line_content_clean[i] == '\t':
            padding_chars.append('\t')
        else:
            padding_chars.append(' ')
    padding = "".join(padding_chars)
    
    formatted = (
        f"{error_class} na linha {line}, coluna {column}: {message}\n"
        f"{line_prefix}{line_content_clean}\n"
        f"{' ' * len(line_prefix)}{padding}^"
    )
    return formatted
