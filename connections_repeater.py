import socket
from threading import Thread, Event


class ConnectionsRepeater:
    def __init__(self, connection_a, connection_b):
        self.connections = [connection_a, connection_b]
        self.threads = [
            Thread(target=self._repeat_from, args=(0, 1)),
            Thread(target=self._repeat_from, args=(1, 0))
        ]
        self._finish_event = Event()

    def start(self):
        self._finish_event.clear()
        for thread in self.threads:
            thread.start()

    def stop(self):
        self._finish_event.set()

    @property
    def finished(self):
        return self._finish_event.is_set()

    def _repeat_from(self, idx_a, idx_b):
        while not self.finished:
            try:
                self.connections[idx_b].send(self.connections[idx_a].recv())
            except (socket.timeout, ConnectionError):
                pass
