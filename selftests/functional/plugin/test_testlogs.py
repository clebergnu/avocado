import os

from avocado.core import exit_codes
from avocado.utils import process
from avocado.utils import script

from ... import AVOCADO, BASEDIR, TestCaseTmpDir


class TestLogs(TestCaseTmpDir):

    def setUp(self):
        super(TestLogs, self).setUp()
        self.config_file = script.TemporaryScript(
            'avocado.conf',
            "[job.output.testlogs]\n"
            "statuses = ['FAIL']\n"
            "logfiles = ['stdout', 'stderr', 'DOES_NOT_EXIST']\n")
        self.config_file.save()

    def test_simpletest_logfiles(self):
        fail_test = os.path.join(BASEDIR, 'examples', 'tests', 'failtest.sh')
        cmd_line = ('%s --config %s run --job-results-dir %s --disable-sysinfo'
                    ' -- %s' % (AVOCADO, self.config_file.path,
                                self.tmpdir.name, fail_test))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))
        self.assertNotIn('Log file "debug.log" content', result.stdout_text)
        self.assertIn('Log file "stdout" content', result.stdout_text)
        self.assertIn('Log file "stderr" content', result.stdout_text)
        self.assertRegex(result.stderr_text,
                         r'Failure to access log file.*DOES_NOT_EXIST"')

    def tearDown(self):
        super(TestLogs, self).tearDown()
        self.config_file.remove()
