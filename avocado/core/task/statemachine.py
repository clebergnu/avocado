import asyncio
import random
import time

# REMOVE ME START



DEBUG = False


def debug(msg):
    if DEBUG:
        print(msg)


def true_or_false(handicap=3):
    """Returns a random positive or negative outcome, with some bias."""
    if handicap > 1:
        choices = [True] + ([False] * handicap)
    else:
        choices = [False] + ([True] * abs(handicap))
    return random.choice(choices)


def mock_check_task_requirement():
    # More success than failures, please
    return true_or_false(-8)
# REMOVE END END 


class TaskStateMachine:
    """Represents all phases that a task can go through its life."""
    def __init__(self, tasks):
        self._requested = tasks
        self._triaging = []
        self._ready = []
        self._started = []
        self._finished = []
        self._lock = asyncio.Lock()

    @property
    def requested(self):
        return self._requested

    @property
    def triaging(self):
        return self._triaging

    @property
    def ready(self):
        return self._ready

    @property
    def started(self):
        return self._started

    @property
    def finished(self):
        return self._finished

    @property
    def lock(self):
        return self._lock

    @property
    async def complete(self):
        async with self._lock:
            pending = any([self._requested, self._triaging,
                           self._ready, self._started])
        return not pending


class Worker:

    def __init__(self, task_state_machine, spawner, max_triaging=8, max_running=8):
        self._tsm = task_state_machine
        self._spawner = spawner
        self._max_triaging = max_triaging
        self._max_running = max_running

    async def bootstrap(self):
        """Reads from requested, moves into triaging."""
        try:
            async with self._tsm.lock:
                if len(self._tsm.triaging) < self._max_triaging:
                    task_info = self._tsm.requested.pop()
                    self._tsm.triaging.append(task_info)
        except IndexError:
            return

    async def triage(self):
        """Reads from triaging, moves into either: ready or finished."""
        try:
            async with self._tsm.lock:
                task_info = self._tsm.triaging.pop()
        except IndexError:
            return

        if mock_check_task_requirement():
            async with self._tsm.lock:
                self._tsm.ready.append(task_info)
        else:
            async with self._tsm.lock:
                self._tsm.finished.append(task_info)
                task_info.status = 'FAILED ON TRIAGE'

    async def start(self):
        """Reads from ready, moves into either: started or finished."""
        try:
            async with self._tsm.lock:
                task_info = self._tsm.ready.pop()
        except IndexError:
            return

        # enforce a rate limit on the number of started (currently running) tasks.
        # this is a global limit, but the spawners can also be queried with regards
        # to their capacity to handle new tasks
        async with self._tsm.lock:
            if len(self._tsm.started) >= self._max_running:
                print(task_info, 'waiting because of max running')
                self._tsm.ready.insert(0, task_info)
                task_info.status = 'WAITING'
                return

        # suppose we're starting the tasks
        start_ok = await self.do_start(task_info)
        if start_ok:
            async with self._tsm.lock:
                task_info.status = None
                # Let's give each task 15 seconds from start time
                task_info.timeout = time.monotonic() + 15
                self._tsm.started.append(task_info)
        else:
            async with self._tsm.lock:
                self._tsm.finished.append(task_info)
                task_info.status = 'FAILED ON START'

    async def do_start(self, task_info):
        """Actual starting of a task."""
        return await self._spawner.spawn_task(task_info)

    async def monitor(self):
        """Reads from started, moves into finished."""
        try:
            async with self._tsm.lock:
                task_info = self._tsm.started.pop()
        except IndexError:
            return

        _ = await self._spawner.wait_task(task_info)

        if time.monotonic() > task_info.timeout:
            async with self._tsm.lock:
                task_info.status = 'FAILED W/ TIMEOUT'
                self._tsm.finished.append(task_info)
        elif not self._spawner.is_task_alive(task_info):
            async with self._tsm.lock:
                self._tsm.finished.append(task_info)
        else:
            async with self._tsm.lock:
                self._tsm.started.insert(0, task_info)

    async def run(self):
        """Pushes Tasks forward and makes them do something with their lifes."""
        while True:
            is_complete = await self._tsm.complete
            if is_complete:
                break
            await self.bootstrap()
            await self.triage()
            await self.start()
            await self.monitor()
