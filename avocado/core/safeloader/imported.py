import ast
import os


class ImportedSymbol:
    """A representation of a importable symbol.

    Attributes:

    symbol : str
    module_path : str or None
    """

    def __init__(self, symbol, module_path='', importer_fs_path=None):
        #: The name of the imported symbol.  On a statement such as
        #: "import os", the symbol is "os".  On a statement such as
        #: "from unittest.mock import mock_open", the symbol is "mock_open"
        self.symbol = symbol
        #: Path from where the symbol was imported.  On a statement such as
        #: "import os", module_path is None.  On a statement such as
        #: "from unittest.mock import mock_open", the module_path is
        #: "unittest.mock".  On a statement such as "from ..foo import bar",
        #: module_path is "..foo" (relative).
        self.module_path = module_path
        #: The full, absolute path of the module importing this symbol.
        #: This is used for relative path calculations.
        self.importer_fs_path = importer_fs_path

    @staticmethod
    def get_symbol_from_statement(statement):
        if isinstance(statement, ast.ImportFrom):
            return statement.names[0].name

        if isinstance(statement, ast.Import):
            if getattr(statement, 'module', None) is not None:
                # Module has a name, so its path is absolute, and not relative
                # to the directory structure
                module_path = statement.module
            else:
                relative_level = getattr(statement, 'level', 0)
                relative_path = "".join(["." for _ in range(relative_level)])
                name = statement.names[0].name
                module_path = relative_path + name
            return module_path

        raise ValueError("Statement is not an import: %s" % statement)

    @staticmethod
    def get_module_path_from_statement(statement):
        module_path = getattr(statement, 'module', None) or ''
        if isinstance(statement, ast.Import):
            if statement.names[0].asname:
                module_path = statement.names[0].name
                if '.' in module_path:
                    module_path = module_path.rsplit('.', 1)[0]
        # If this is an aliased import, module_path will be
        # everything but the last component
        relative_level = getattr(statement, 'level', 0)
        relative_level_prefix = "".join(["." for _ in range(relative_level)])
        return relative_level_prefix + module_path

    @classmethod
    def from_statement(cls, statement, importer_fs_path=None):
        return cls(cls.get_symbol_from_statement(statement),
                   cls.get_module_path_from_statement(statement),
                   importer_fs_path)

    def to_str(self):
        """Returns a string representation of the plausible statement used."""
        if not self.module_path:
            return "import %s" % self.symbol
        return "from %s import %s" % (self.module_path, self.symbol)

    def is_relative(self):
        """Returns whether the imported symbol is on a relative path."""
        return self.module_path.startswith(".")

    def get_relative_module_fs_path(self):
        """Returns the module base dir, based on its relative path

        The base dir for the module is the directory where one is
        expected to find the first module of the module path.  For a
        module path of "..foo.bar", and its importer being at
        "/abs/path", the base dir where "foo" is supposed to be found
        would be "/abs".  And as a consequence, "bar" would be found
        at "/abs/foo/bar".

        This assumes that the module path is indeed related to the location
        of its importer.  This may not be true if the namespaces match, but
        are distributed across different filesystem paths.
        """
        path = self.importer_fs_path
        for char in self.module_path[1:]:
            if char != ".":
                break
            path = os.path.dirname(path)
        return path

    def get_parent_fs_path(self):
        if self.is_relative():
            return self.get_relative_module_fs_path()
        parent_path = os.path.dirname(self.importer_fs_path)
        if self.module_path:
            return os.path.join(parent_path, self.module_path)
        return parent_path

    def __repr__(self):
        return '<ImportedSymbol symbol="%s" module_path="%s">' % (self.symbol,
                                                                  self.module_path)

    def __eq__(self, other):
        return ((self.symbol == other.symbol) and
                (self.module_path == other.module_path) and
                (self.importer_fs_path == other.importer_fs_path))
