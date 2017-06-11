from threading import Thread, Event

from time import time

import constants as const
from udp_connection import UdpConnection


class NatConnection(UdpConnection):
    def __init__(self, sock, remote_addr):
        super().__init__(sock, remote_addr)
        self.keepalive_sender = KeepaliveSender(sock, remote_addr)
        self._last_packet_time = time()

    def send(self, data):
        self.send_raw(self._escape(data))

    def send_raw(self, data):
        super().send(data)

    def recv(self):
        while True:
            data = self.recv_raw()
            self._last_packet_time = time()
            if not data.startswith(const.COOKIE):
                return self._unescape(data)

    def recv_raw(self):
        return super().recv()

    def close(self):
        self.keepalive_sender.cancel()
        super().close()

    @property
    def active(self):
        return time() - self._last_packet_time < const.DISCONNECT_TIMEOUT

    def __exit__(self, *args):
        self.keepalive_sender.cancel()
        super().__exit__(*args)

    def _escape(self, data):
        if data.startswith(const.COOKIE) or data.startswith(b"\\"):
            data = b"\\" + data
        return data

    def _unescape(self, data):
        if data.startswith(b"\\"):
            data = data[1:]
        return data


class KeepaliveSender(Thread):
    def __init__(self, sock, remote_addr):
        super().__init__()
        self.sock = sock
        self.remote_addr = remote_addr
        self.finished = Event()

    def cancel(self):
        self.finished.set()

    def run(self):
        while not self.finished.is_set():
            self.finished.wait(const.KEEPALIVE_SEND_TIME)
            if not self.finished.is_set():
                self.sock.sendto(const.KEEPALIVE_PACKET, self.remote_addr)
