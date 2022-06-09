import os

from avocado import Test


class FileByAnsible(Test):
    """
    :avocado: dependency={"type": "ansible-module", "uri": "file", "path": "/tmp/ansible_tmp", "state": "touch"}
    """
    def test(self):
        files = os.listdir('/tmp')
        self.log.info(files)
        if not 'ansible_tmp' in files:
            self.fail('Did not find an ansible created file')
