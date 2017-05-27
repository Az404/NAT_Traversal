import socket
import struct
from concurrent.futures import ThreadPoolExecutor

import constants as const


class NATTraversalServer:
    def __init__(self):
        self.listener = socket.socket(type=socket.SOCK_DGRAM)
        self.pool = ThreadPoolExecutor()
        self.table = {}

    def run(self):
        self.listener.bind(("", const.PORT))
        while True:
            data, addr = self.listener.recvfrom(1024)
            self.pool.submit(self.process_client, addr, data)

    def process_client(self, addr, data):
        data = data.decode(errors="replace")
        lines = data.split("\n")
        if len(lines) != 3 or lines[0] != const.COOKIE:
            return

        remote_id, requested_id = lines[1:3]

        self.table[remote_id] = addr

        print("Client {} {} requested {}: ".format(
            remote_id, addr, requested_id), end="")
        if requested_id in self.table:
            print(" found", self.table[requested_id])
            response = self._pack_addr(self.table[requested_id])
        else:
            print(" not found")
            return b"\0" * 6
        self.listener.sendto(response, addr)

    def _pack_addr(self, addr):
        return socket.inet_aton(addr[0]) + struct.pack("!H", addr[1])


def main():
    NATTraversalServer().run()


if __name__ == '__main__':
    main()