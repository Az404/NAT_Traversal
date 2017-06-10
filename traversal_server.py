import socket
import struct
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from traceback import print_exc

import constants as const
from clientserver_connection import ClientServerConnection
from enums import Operation, OperationResult


class NATTraversalServer:
    def __init__(self):
        self.udp_listener = socket.socket(type=socket.SOCK_DGRAM)
        self.tcp_listener = socket.socket()
        self.pool = ThreadPoolExecutor(const.SERVER_WORKERS)
        self.table = {}
        self.tcp_connections = {}
        self.connections_lock = Lock()

    def run(self):
        self.pool.submit(self._process_tcp_connections)
        self.udp_listener.bind(("", const.PORT))
        while True:
            data, addr = self.udp_listener.recvfrom(1024)
            self.pool.submit(self.process_client, addr, data)

    def process_client(self, addr, data):
        data = data.decode(errors="replace")
        lines = data.split("\n")
        if len(lines) != 3 or lines[0] != const.COOKIE.decode():
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
            response = b"\0" * 6
        self.udp_listener.sendto(response, addr)

    def _pack_addr(self, addr):
        return socket.inet_aton(addr[0]) + struct.pack("!H", addr[1])

    def _process_tcp_connections(self):
        try:
            self.tcp_listener.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_listener.bind(("", const.PORT))
            self.tcp_listener.listen(5)
            while True:
                sock, addr = self.tcp_listener.accept()
                self.pool.submit(self._process_tcp_client, sock)
        except:
            print_exc()

    def _process_tcp_client(self, sock):
        try:
            sock.settimeout(const.OPERATION_TIMEOUT)
            try:
                conn_a = ClientServerConnection(sock)
                remote_id = conn_a.readline()
                requested_id = conn_a.readline()
                print("Connected {} waiting {}".format(remote_id, requested_id))
                with self.connections_lock:
                    if requested_id not in self.tcp_connections:
                        self.tcp_connections[remote_id] =\
                            ClientServerConnection(sock)
                        return

                conn_b = self.tcp_connections[requested_id]
                del self.tcp_connections[requested_id]
                print("Starting traverse...")
                if not self._traverse(conn_a, conn_b):
                    print("Hole punching between {} and {} failed".format(
                        remote_id, requested_id
                    ))
            except socket.timeout:
                pass
        except:
            print_exc()

    def _traverse(self, conn_a, conn_b):
        with conn_a, conn_b:
            return (self._try_punch_hole(conn_a, conn_b) or
                    self._try_punch_hole(conn_b, conn_a))

    def _try_punch_hole(self, conn_a, conn_b):
        print("Hole punching initiated from {} to {}".format(
            *self._get_remote_ips(conn_a, conn_b)))

        connections = [conn_a, conn_b]
        for conn in connections:
            conn.send_and_wait(Operation.BIND, OperationResult.OK)
        for conn in connections:
            conn.send_and_wait(Operation.ANNOUNCE_ADDR, OperationResult.OK)
        for conn in connections:
            conn.send_and_wait(Operation.UPDATE_ADDR, OperationResult.OK)
        for conn in connections:
            conn.send_and_wait(Operation.SEND_HELLO, OperationResult.OK)

        result = conn_a.send_and_recv(Operation.WAIT_HELLO, OperationResult)
        if result == OperationResult.OK:
            conn_a.send_and_wait(Operation.SEND_HELLO, OperationResult.OK)
            conn_b.send_and_wait(Operation.WAIT_HELLO, OperationResult.OK)
            for conn in connections:
                conn.write_as_enum(Operation.FINISH)
            print("Successful hole punching from {} to {}".format(
                *self._get_remote_ips(conn_a, conn_b)
            ))
            return True

    def _get_remote_ips(self, *connections):
        return [conn.sock.getpeername()[0] for conn in connections]


def main():
    NATTraversalServer().run()


if __name__ == '__main__':
    main()
