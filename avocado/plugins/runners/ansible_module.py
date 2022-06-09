import asyncio
import time
from multiprocessing import Process, SimpleQueue

from avocado.utils import process

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import RUNNER_RUN_STATUS_INTERVAL, BaseRunner
from avocado.core.utils import messages


class AnsibleModuleRunner(BaseRunner):
    """Runner for dependencies of type ansible-module

    This runner handles download and verification.

    Runnable attributes usage:

     * kind: 'ansible-module'

     * uri: the name of the module

     * args: not used

     * kwargs: passed as arguments to ansible module
    """

    name = 'ansible-module'
    description = f'Runner for dependencies of type {name}'

    def _run_ansible_module(self, uri, queue):
        args = " ".join([f"{k}={v}" for k, v in self.runnable.kwargs.items()])
        if args:
            args_cmdline = f"-a '{args}'"
        else:
            args_cmdline = ""
        try:
            proc_result = process.run(f"ansible -m {uri} {args_cmdline} localhost")
            result = 'pass'
            stdout = proc_result.stdout
            stderr = proc_result.stderr
        except process.CmdError as e:
            result = 'fail'
            stdout = ''
            stderr = str(e)
        queue.put({'result': result,
                   'stdout': stdout,
                   'stderr': stderr})

    def run(self, runnable):
        # pylint: disable=W0201
        self.runnable = runnable
        yield messages.StartedMessage.get()

        if not runnable.uri:
            reason = 'uri identifying the ansible module is required'
            yield messages.FinishedMessage.get('error', reason)
        else:
            queue = SimpleQueue()
            process = Process(target=self._run_ansible_module,
                              args=(runnable.uri, queue))
            process.start()
            while queue.empty():
                time.sleep(RUNNER_RUN_STATUS_INTERVAL)
                yield messages.RunningMessage.get()

            output = queue.get()
            yield messages.FinishedMessage.get(output['result'])


class RunnerApp(BaseRunnerApp):
    PROG_NAME = f'avocado-runner-{AnsibleModuleRunner.name}'
    PROG_DESCRIPTION = (AnsibleModuleRunner.description)
    RUNNABLE_KINDS_CAPABLE = [AnsibleModuleRunner.name]


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == '__main__':
    main()
