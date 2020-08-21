import asyncio
from unittest import TestCase

from avocado.core.nrunner import Runnable, Task
from avocado.core.task import statemachine
from avocado.core.task.info import TaskInfo
from avocado.plugins.spawners.process import ProcessSpawner


class StateMachine(TestCase):

    def test(self):
        number_of_tasks = 80
        number_of_workers = 8

        runnable = Runnable("noop", "noop")
        tasks_info = [TaskInfo(Task("%03i" % _, runnable))
                      for _ in range(1, number_of_tasks + 1)]
        spawner = ProcessSpawner()

        state_machine = statemachine.TaskStateMachine(tasks_info)
        loop = asyncio.get_event_loop()
        workers = [statemachine.Worker(state_machine, spawner).run()
                   for _ in range(number_of_workers)]

        loop.run_until_complete(asyncio.gather(*workers))
        self.assertEqual(number_of_tasks, len(state_machine.finished))
