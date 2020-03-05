import os
import tempfile
import unittest

from avocado.core.future import settings

example_1 = """[foo]
str_key = frobnicate
int_key = 1
float_key = 1.25
bool_key = True
list_key = ['I', 'love', 'settings']
empty_key =
path = ~/path/at/home
relative_path = path/at/home
home_path = ~
"""

class SettingsTest(unittest.TestCase):

    def setUp(self):
        self.config_file = tempfile.NamedTemporaryFile('w', delete=False)
        self.config_file.write(example_1)
        self.config_file.close()

    def test_default(self):
        stgs = settings.Settings(self.config_file.name)
        stgs.register_option('foo', 'existing', 'ohyes', 'existing option')
        config = stgs.as_dict()
        self.assertEqual(config.get('foo.existing'), 'ohyes')

    def test_non_existing_key(self):
        stgs = settings.Settings(self.config_file.name)
        config = stgs.as_dict()
        self.assertIsNone(config.get('foo.non_existing'))

    def test_different_default_int(self):
        stgs = settings.Settings(self.config_file.name)
        stgs.register_option('foo', 'int_key', 2,
                             'integer value', key_type=int)
        # Question: do we want users to call _merge_with_configs()?
        # with the following line enable, we get the right value coming
        # from the configuration file. Without, it fails.
        # stgs._merge_with_configs()
        config = stgs.as_dict()
        self.assertEqual(config.get('foo.int_key'), 1)

    def tearDown(self):
        os.unlink(self.config_file.name)


if __name__ == '__main__':
    unittest.main()
