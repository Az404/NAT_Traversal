from threading import Timer
import constants as const


class NatConnection:
    def __init__(self, sock, remote_addr):
        self.sock = sock
        self.remote_addr = remote_addr
        self.keepalive_sender = KeepaliveSender(sock, remote_addr)

    def send(self, data):
        self.send_raw(self._escape(data))

    def send_raw(self, data):
        self.sock.sendto(data, self.remote_addr)

    def recv(self):
        while True:
            data = self.recv_raw()
            if not data.startswith(const.COOKIE):
                return self._unescape(data)

    def recv_raw(self):
        while True:
            data, addr = self.sock.recvfrom(8192)
            if addr == self.remote_addr:
                return data

    def _escape(self, data):
        if data.startswith(const.COOKIE) or data.startswith(b"\\"):
            data = b"\\" + data
        return data

    def _unescape(self, data):
        if data.startswith(b"\\"):
            data = data[1:]
        return data

    def close(self):
        self.keepalive_sender.cancel()
        self.sock.close()


class KeepaliveSender(Timer):
    def __init__(self, sock, remote_addr):
        super().__init__(const.KEEPALIVE_SEND_TIME, self._send_keepalive)
        self.sock = sock
        self.remote_addr = remote_addr

    def _send_keepalive(self):
        self.sock.sendto(const.KEEPALIVE_PACKET, self.remote_addr)