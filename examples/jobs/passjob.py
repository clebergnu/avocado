#!/usr/bin/env python3
import sys

from avocado.core.job import Job

job_config = {'run.test_runner': 'nrunner',
              'nrunner.status_server_uri': '127.0.0.1:8889',
              'run.references': ['examples/tests/passtest.py:PassTest.test']}

# Automatic helper method (Avocado will try to discovery things from config
# dicts. Since there is magic here, we dont need to pass suite names or suites,
# and test/task id will be prepend with the suite index (in this case 1 and 2)

job = Job.from_config(job_config=job_config)
job.setup()
sys.exit(job.run())
