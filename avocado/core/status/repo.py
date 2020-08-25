import os
from .utils import json_loads


class StatusMsgMissingDataError(Exception):
    """Status message does not contain the required data."""


class StatusRepo:
    """Maintains tasks' status related data and provides aggregated info."""

    def __init__(self):
        #: Contains all reveived messages by a given task (by its ID)
        self._all_data = {}
        #: Contains the most up to date status of a task, and the time it
        #: it was set in a tuple (status, time).  This is keyed
        #: by the task ID, and the most up to date status is determined by
        #: the "timestamp" in the "time" field of the message, that is,
        #: it's *not* based by the order it was received.
        self._status = {}
        #: Contains the task IDs keyed by the result received
        self._by_result = {}

    def _handle_task_finished(self, message):
        # SAME BLOCK ON _handle_task_finished
        class FakeId:
            str_uid = message.get('id').split('-')[1]
            name = message.get('id').split('-', 2)[2]
            str_variant = ''
        early_state = {
                'name': FakeId, #message.get('id'),
                'job_logdir': self.job.logdir,
                'job_unique_id': self.job.unique_id,
            }
        # SAME BLOCK ON _handle_task_finished

        this_task_data = self._all_data[message.get('id')]

        # FIXME: this is *assuming* a result
        test_state = {'status': message['result'].upper()}
        test_state.update(early_state)

        time_start = this_task_data[0]['time']
        time_end = message['time']
        time_elapsed = time_end - time_start
        test_state['time_start'] = time_start
        test_state['time_end'] = time_end
        test_state['time_elapsed'] = time_elapsed

        # fake log dir, needed by some result plugins such as HTML
        test_state['logdir'] = ''

        self.job.result.check_test(test_state)
        self.job.result_events_dispatcher.map_method('end_test', self.job.result, test_state)
        self._set_by_result(message)
        self._set_task_data(message)

    def _handle_task_started(self, message):
        if 'output_dir' not in message:
            raise StatusMsgMissingDataError('output_dir')

        # SAME BLOCK ON _handle_task_finished
        class FakeId:
            try:
                str_uid = message.get('id').split('-')[1]
            except:
                str_uid = 'ERROR str_uid'
            try:
                name = message.get('id').split('-', 2)[2]
            except:
                name = 'ERROR name'
            str_variant = ''
        early_state = {
                'name': FakeId, #message.get('id'),
                'job_logdir': self.job.logdir,
                'job_unique_id': self.job.unique_id,
            }
        # SAME BLOCK ON _handle_task_finished

        self._set_task_data(message)
        self.job.result.start_test(early_state)
        self.job.result_events_dispatcher.map_method('start_test',
                                                     self.job.result,
                                                     early_state)

    def _set_by_result(self, message):
        """Sets an entry in the aggregate by result.

        For messages that include a "result" key, expected for example,
        from a "finished" status message, this will allow users to query
        for tasks with a given result."""
        result = message.get('result')
        if result not in self._by_result:
            self._by_result[result] = []
        if message['id'] not in self._by_result[result]:
            self._by_result[result].append(message['id'])

    def _set_task_data(self, message):
        """Appends all data on message to an entry keyed by the task's ID."""
        task_id = message.pop('id')
        if not task_id in self._all_data:
            self._all_data[task_id] = []
        self._all_data[task_id].append(message)

    def get_task_data(self, task_id):
        """Returns all data on a given task, by its ID."""
        return self._all_data.get(task_id)

    def get_latest_task_data(self, task_id):
        """Returns the latest data on a given task, by its ID."""
        task_data = self._all_data.get(task_id)
        if task_data is None:
            return None
        return task_data[-1]

    def _update_status(self, message):
        """Update the latest status of atask (by time, not by message)."""
        task_id = message.get('id')
        status = message.get('status')
        time = message.get('time')
        if not all((task_id, status, time)):
            return
        if task_id not in self._status:
            self._status[task_id] = (status, time)
        else:
            current_time = self._status[task_id][1]
            if time > current_time:
                self._status[task_id] = (status, time)

    def process_message(self, message):
        if 'id' not in message:
            raise StatusMsgMissingDataError('id')

        self._update_status(message)
        handlers = {'started': self._handle_task_started,
                    'finished': self._handle_task_finished}
        meth = handlers.get(message.get('status'),
                            self._set_task_data)
        meth(message)

    def process_raw_message(self, raw_message):
        raw_message = raw_message.strip()
        message = json_loads(raw_message)
        self.process_message(message)

    @property
    def result_stats(self):
        return {key: len(value) for key, value in self._by_result.items()}

    def get_task_status(self, task_id):
        if task_id not in self._status:
            return None
        return self._status.get(task_id, (None, None))[0]
