"""Tabela de símbolos da linguagem JSS.

Responsável por armazenar identificadores, escopos e metadados semânticos.
"""

class Symbol:
    def __init__(self, name, type_name, is_const=False, is_function=False, is_class=False, is_method=False, is_attribute=False, dimension=None, params=None, return_type=None, attributes=None, methods=None, constructor=None):
        self.name = name
        self.type = type_name
        self.is_const = is_const
        self.is_function = is_function
        self.is_class = is_class
        self.is_method = is_method
        self.is_attribute = is_attribute
        self.dimension = dimension  # None para escalar, int/lista de int para vetores
        self.params = params or []  # Lista de tuplas (tipo, nome) para funções/métodos
        self.return_type = return_type  # Tipo de retorno para funções/métodos
        self.attributes = attributes or {}  # Atributos de classes (nome -> Symbol)
        self.methods = methods or {}  # Métodos de classes (nome -> Symbol)
        self.constructor = constructor  # Construtor da classe (Symbol)


class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent
        self.children = []
        if parent:
            parent.children.append(self)

    def define(self, name, symbol):
        """Define um novo símbolo no escopo atual."""
        self.symbols[name] = symbol

    def lookup(self, name):
        """Busca um símbolo no escopo atual ou nos escopos superiores (recursivamente)."""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_local(self, name):
        """Busca um símbolo apenas no escopo atual (útil para verificar redeclarações)."""
        return self.symbols.get(name, None)
