import unittest

from avocado.core import bootstrap


INIMAGINABLE = "no_One_shoulD_Ever_n@me_anything_l|ke_th1s"


class BootstrapTest(unittest.TestCase):

    def test_no_component(self):
        with self.assertRaises(bootstrap.NoSuchComponentError) as exc:
            bootstrap.bootstrap(INIMAGINABLE, "local",
                                lambda env, cmd: False)


    def test_no_environment(self):
        with self.assertRaises(bootstrap.NoSuchEnvironmentCommandError) as exc:
            bootstrap.bootstrap("python", INIMAGINABLE,
                                lambda env, cmd: False)

    def test_executor_fail(self):
        self.assertFalse(bootstrap.bootstrap("python", "centos:stream8",
                                             lambda env, cmd: False))
