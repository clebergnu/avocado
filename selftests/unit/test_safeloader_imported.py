import ast
import unittest

from avocado.core.safeloader.imported import ImportedSymbol


class SymbolAndModulePath(unittest.TestCase):

    def _check(self, input_symbol, input_module_path, input_statement):
        statement = ast.parse(input_statement).body[0]
        symbol = ImportedSymbol.get_symbol_from_statement(statement)
        self.assertEqual(symbol, input_symbol)
        module_path = ImportedSymbol.get_module_path_from_statement(statement)
        self.assertEqual(module_path, input_module_path)
        imported_symbol = ImportedSymbol(symbol, module_path)
        self.assertEqual(imported_symbol.to_str(), input_statement)
        self.assertEqual(imported_symbol,
                         ImportedSymbol.from_statement(statement))

    def test_symbol_only(self):
        self._check("os", "", "import os")

    def test_symbol_module_path(self):
        self._check("path", "os", "from os import path")

    def test_symbol_module_path_compound(self):
        self._check("mock_open", "unittest.mock",
                    "from unittest.mock import mock_open")

    def test_symbol_module_path_only_relative(self):
        self._check("utils", "..", "from .. import utils")

    def test_symbol_module_path_from_relative(self):
        self._check("utils", "..selftests", "from ..selftests import utils")

    def test_symbol_module_path_from_relative_multiple(self):
        self._check("mod", "..selftests.utils",
                    "from ..selftests.utils import mod")

    def test_incorrect_statement_type(self):
        statement = ast.parse("pass").body[0]
        with self.assertRaises(ValueError):
            _ = ImportedSymbol.get_symbol_from_statement(statement)


class RelativePath(unittest.TestCase):

    def test_relative_same(self):
        imported_symbol = ImportedSymbol('symbol', '.module',
                                         '/abs/fs/location')
        self.assertEqual(imported_symbol.get_relative_module_fs_path(),
                         "/abs/fs/location")

    def test_relative_path(self):
        imported_symbol = ImportedSymbol('symbol', '..module',
                                         '/abs/fs/location')
        self.assertEqual(imported_symbol.get_relative_module_fs_path(),
                         "/abs/fs")


class ImporterPath(unittest.TestCase):

    def test_relative_path(self):
        statement = ast.parse("from ..selftests import utils").body[0]
        importer = "/abs/fs/location/of/selftests/unit/test_foo.py"
        symbol = ImportedSymbol.from_statement(statement,
                                               importer)
        self.assertEqual(symbol.get_relative_module_fs_path(),
                         "/abs/fs/location/of")

    def test_relative_path_same_level(self):
        statement = ast.parse("from .unit import test_bar").body[0]
        importer = "/abs/fs/location/of/selftests/unit/test_foo.py"
        symbol = ImportedSymbol.from_statement(statement,
                                               importer)
        self.assertEqual(symbol.get_relative_module_fs_path(),
                         "/abs/fs/location/of/selftests")

    def test_path_compound(self):
        statement = ast.parse("from path import parent3").body[0]
        importer = "/abs/fs/location/of/imports.py"
        symbol = ImportedSymbol.from_statement(statement,
                                               importer)
        self.assertEqual(symbol.get_parent_fs_path(),
                         "/abs/fs/location/of/path")

    def xxx_test_path_compound_levels(self):
        statement = ast.parse("from .path.parent8 import Class8").body[0]
        importer = "/abs/fs/location/of/imports.py"
        symbol = ImportedSymbol.from_statement(statement,
                                               importer)
        self.assertEqual(symbol.get_parent_fs_path(),
                         "/abs/fs/location/of/path/parent8")
