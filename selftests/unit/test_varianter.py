import unittest
import argparse

from avocado.core import varianter
from avocado.core import mux


class TestVarianter(unittest.TestCase):

    def setUp(self):
        self.tree = mux.MuxTreeNode('')
        path = mux.MuxTreeNode('path', parent=self.tree)
        path.multiplex = True
        path1 = mux.MuxTreeNode('path1', {'key1': 'value1'}, parent=path)
        path2 = mux.MuxTreeNode('path2', {'key2': 'value2'}, parent=path)
        self.varianter = varianter.Varianter()
        self.varianter.data = self.tree
        self.varianter.parse(argparse.Namespace())

    def test_str_variants(self):
        self.assertEqual(self.varianter.str_variants(),
                         ("Variant 1:    /path/path1\n"
                          "Variant 2:    /path/path2"))

    def test_str_variants_long(self):
        self.assertEqual(self.varianter.str_variants_long(),
                         ("Variant 1: /path/path1\n\n"
                          "    /path/path1:key1 => value1\n\n"
                          "Variant 2: /path/path2\n\n"
                          "    /path/path2:key2 => value2\n"))

    def test_str_long(self):
        self.assertEqual(self.varianter.str_long(),
                         ("Multiplex tree representation:\n"
                          " \\-- path\n"
                          "      #== path1\n"
                          "      #      -> key1: value1\n"
                          "      #== path2\n"
                          "             -> key2: value2\n\n"
                          "Variant 1:    /path/path1\n"
                          "Variant 2:    /path/path2\n"))

    def test_len(self):
        self.assertEqual(len(self.tree), 2)
