import asyncio
import os
import socket
import time
from threading import Thread

from avocado.core.status import repo, server
from selftests import TestCaseTmpDir


class Server(TestCaseTmpDir):

    @staticmethod
    def client(path):
        msg = b'{"id": "1-foo", "status": "finished", "result": "pass"}'
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(path)
        sock.send(msg)

    @staticmethod
    def run_loop(loop, status_server):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(status_server.serve_forever())

    def test_server(self):
        path = os.path.join(self.tmpdir.name, 'socket')
        status_repo = repo.StatusRepo()
        status_server = server.StatusServer(path, status_repo)
        loop = asyncio.new_event_loop()
        thread = Thread(target=self.run_loop,
                        args=(loop, status_server),
                        daemon=True)
        thread.start()
        time.sleep(0.5)
        self.client(path)
        time.sleep(0.5)
        self.assertEqual(status_repo.get_latest_task_data("1-foo"),
                         {"status": "finished", "result": "pass"})
