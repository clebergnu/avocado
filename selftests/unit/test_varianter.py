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

    def test_to_str_empty(self):
        self.assertEqual(varianter.Varianter().to_str(), "")

    def test_to_str_summary(self):
        self.assertEqual(self.varianter.to_str(summary=1),
                         ("Multiplex tree representation:\n"
                          " \xe2\x94\x97\xe2\x94\x81\xe2\x94\x81 path\n"
                          "      \xe2\x95\xa0\xe2\x95\x90\xe2\x95\x90 path1\n"
                          "      \xe2\x95\x9a\xe2\x95\x90\xe2\x95\x90 path2\n"))

    def test_to_str_variants(self):
        self.assertEqual(self.varianter.to_str(variants=1),
                         ("Multiplex variants:\n"
                          "Variant 1:    /path/path1\n"
                          "Variant 2:    /path/path2"))

    def test_to_str_summary_variants(self):
        self.assertEqual(self.varianter.to_str(summary=1, variants=1),
                         ("Multiplex tree representation:\n"
                          " \xe2\x94\x97\xe2\x94\x81\xe2\x94\x81 path\n"
                          "      \xe2\x95\xa0\xe2\x95\x90\xe2\x95\x90 path1\n"
                          "      \xe2\x95\x9a\xe2\x95\x90\xe2\x95\x90 path2\n\n"
                          "Multiplex variants:\n"
                          "Variant 1:    /path/path1\n"
                          "Variant 2:    /path/path2"))
