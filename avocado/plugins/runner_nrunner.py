# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2019-2020
# Authors: Cleber Rosa <crosa@redhat.com>

"""
NRunner based implementation of job compliant runner
"""

import asyncio
import json
import multiprocessing
import os
from copy import copy

from avocado.core import nrunner
from avocado.core.dispatcher import SpawnerDispatcher
from avocado.core.plugin_interfaces import Runner as RunnerInterface
from avocado.core.status.repo import StatusRepo
from avocado.core.status.server import StatusServer
from avocado.core.task.info import TaskInfo
from avocado.core.task.statemachine import TaskStateMachine, Worker
from avocado.core.test_id import TestID


class Runner(RunnerInterface):

    name = 'nrunner'
    description = '*EXPERIMENTAL* nrunner based implementation of job compliant runner'

    NUMBER_OF_WORKERS = multiprocessing.cpu_count() + 2

    def _save_to_file(self, filename, buff, mode='wb'):
        with open(filename, mode) as fp:
            fp.write(buff)

    def _populate_task_logdir(self, base_path, task, statuses, debug=False):
        # We are copying here to avoid printing duplicated information
        local_statuses = copy(statuses)
        last = local_statuses[-1]
        try:
            stdout = last.pop('stdout')
        except KeyError:
            stdout = None
        try:
            stderr = last.pop('stderr')
        except KeyError:
            stderr = None

        # Create task dir
        task_path = os.path.join(base_path, task.identifier.str_filesystem)
        os.makedirs(task_path, exist_ok=True)

        # Save stdout and stderr
        if stdout is not None:
            stdout_file = os.path.join(task_path, 'stdout')
            self._save_to_file(stdout_file, stdout)
        if stderr is not None:
            stderr_file = os.path.join(task_path, 'stderr')
            self._save_to_file(stderr_file, stderr)

        # Save debug
        if debug:
            debug = os.path.join(task_path, 'debug')
            with open(debug, 'w') as fp:
                json.dump(local_statuses, fp)

        data_file = os.path.join(task_path, 'data')
        with open(data_file, 'w') as fp:
            fp.write("{}\n".format(task.output_dir))

    def _get_all_tasks_info(self, test_suite, status_server_uri):
        result = []
        no_digits = len(str(len(test_suite)))
        for index, task in enumerate(test_suite.tests, start=1):
            task.known_runners = nrunner.RUNNERS_REGISTRY_PYTHON_CLASS
            # this is all rubbish data
            test_id = TestID("{}-{}".format(test_suite.name, index),
                             task.runnable.uri,
                             None,
                             no_digits)
            task.identifier = test_id
            task.status_services.append(nrunner.TaskStatusService(status_server_uri))
            result.append(TaskInfo(task))
        return result

    def _start_status_server(self, status_server_uri):
        # pylint: disable=W0201
        self.status_repo = StatusRepo()
        # pylint: disable=W0201
        self.status_server = StatusServer(status_server_uri,
                                          self.status_repo)
        asyncio.ensure_future(self.status_server.serve_forever())

    def run_suite(self, job, test_suite):
        summary = set()

        # FIXME: re-enable job wide timeout
        # if job.timeout > 0:
        #     deadline = time.time() + job.timeout
        # else:
        #     deadline = None

        test_suite.tests, _ = nrunner.check_tasks_requirements(test_suite.tests)
        job.result.tests_total = test_suite.size  # no support for variants yet
        result_dispatcher = job.result_events_dispatcher

        # FIXME: define URI in a proper registered setting
        status_server_uri = '127.0.0.1:8888'
        self._start_status_server(status_server_uri)

        tasks_info = self._get_all_tasks_info(test_suite,
                                                  status_server_uri)
        tsm = TaskStateMachine(tasks_info)
        # FIXME: should be registered
        spawner_name = test_suite.config.get('run.spawner')
        if spawner_name is None:
            spawner_name = 'process'
        spawner_extension = SpawnerDispatcher()[spawner_name]
        spawner = spawner_extension.obj
        workers = [Worker(tsm, spawner).run()
                   for _ in range(self.NUMBER_OF_WORKERS)]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*workers))

        for task_info in tsm.finished:
            identifier = task_info.task.identifier
            str_identifier = str(identifier)

            early_state = {
                'name': identifier,
                'job_logdir': job.logdir,
                'job_unique_id': job.unique_id,
            }
            job.result.start_test(early_state)
            job.result_events_dispatcher.map_method('start_test',
                                                    job.result,
                                                    early_state)

            # test execution time is currently missing
            # since 358e800e81 all runners all produce the result in a key called
            # 'result', instead of 'status'.  But the Avocado result plugins rely
            # on the current runner approach
            this_task_data = self.status_repo.get_task_data(str_identifier)
            test_state = {'status': this_task_data[-1]['result'].upper()}
            test_state.update(early_state)

            time_start = this_task_data[0]['time']
            time_end = this_task_data[-1]['time']
            time_elapsed = time_end - time_start
            test_state['time_start'] = time_start
            test_state['time_end'] = time_end
            test_state['time_elapsed'] = time_elapsed

            # fake log dir, needed by some result plugins such as HTML
            test_state['logdir'] = ''

            # Populate task dir
            base_path = os.path.join(job.logdir, 'test-results')
            self._populate_task_logdir(base_path,
                                       task_info.task,
                                       this_task_data,
                                       job.config.get('core.debug'))

            job.result.check_test(test_state)
            result_dispatcher.map_method('end_test', job.result, test_state)
        job.result.end_tests()
        return summary
