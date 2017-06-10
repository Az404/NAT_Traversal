import argparse
import socket
import struct
import uuid
from time import sleep

import constants as const
from clientserver_connection import ClientServerConnection
from enums import Operation, OperationResult
from nat_connection import NatConnection


class TraversalError(Exception):
    pass


class NATTraversalClient:
    def __init__(self, server_ip, local_id, remote_id):
        self.server_ip = server_ip
        self.local_id = local_id
        self.remote_id = remote_id
        self.remote_addr = None
        self.udp_sock = None
        self.nat_connection = None
        self._handlers = {
            Operation.BIND: self._process_bind,
            Operation.SEND_HELLO: self._process_send_hello,
            Operation.WAIT_HELLO: self._process_wait_hello,
            Operation.ANNOUNCE_ADDR: self._process_announce,
            Operation.UPDATE_ADDR: self._process_update_addr
        }

    def connect(self):
        while True:
            try:
                server_connection = ClientServerConnection(
                    socket.create_connection((self.server_ip, const.PORT)))
                with server_connection:
                    server_connection.writeline(self.local_id)
                    server_connection.writeline(self.remote_id)
                    while True:
                        operation = server_connection.read_as_enum(Operation)
                        if operation == Operation.FINISH:
                            return self.nat_connection
                        if operation in self._handlers:
                            result = self._handlers[operation]()
                            server_connection.write_as_enum(
                                OperationResult.OK if result
                                else OperationResult.FAIL
                            )
                        else:
                            print("Unknown operation from server")
            except (socket.timeout, ConnectionError, EOFError):
                print("Connection attempt failed")

    def _process_bind(self):
        if self.udp_sock:
            self.udp_sock.close()
        self.udp_sock = socket.socket(type=socket.SOCK_DGRAM)
        self.udp_sock.bind(("", 0))
        self.udp_sock.settimeout(const.BASE_SOCKET_TIMEOUT)
        print("Bind to {}".format(self.udp_sock.getsockname()))
        self._update_connection()
        return True

    def _process_announce(self):
        self._server_request()
        return True

    def _process_update_addr(self):
        print("Waiting for remote addr from server...")
        self.remote_addr = self._get_remote_addr()
        print("Remote addr for {}: {}".format(self.remote_id, self.remote_addr))
        self._update_connection()
        return True

    def _update_connection(self):
        self.nat_connection = NatConnection(self.udp_sock, self.remote_addr)

    def _process_send_hello(self):
        print("Send hello packets to", self.remote_addr)
        for _ in range(const.HELLO_PACKETS_COUNT):
            self.nat_connection.send_raw(const.HELLO_PACKET)
        return True

    def _process_wait_hello(self):
        print("Waiting for response at", self.nat_connection.sock.getsockname())
        try:
            while True:
                data = self.nat_connection.recv_raw()
                if data == const.HELLO_PACKET:
                    print("Received hello packet!")
                    return True
        except socket.timeout:
            print("No hello packet from remote")
        except ConnectionError as e:
            print("Connection error:", e)

    def _server_request(self):
        request = "\n".join(
            (const.COOKIE.decode(), self.local_id, self.remote_id))
        for _ in range(const.SERVER_REQUEST_PROBES):
            self.udp_sock.sendto(request.encode(), (self.server_ip, const.PORT))
            try:
                while True:
                    data, addr = self.udp_sock.recvfrom(1024)
                    if addr[0] == self.server_ip:
                        break
                return data
            except socket.timeout:
                pass
        else:
            raise TraversalError("No response from traversal server")

    def _get_remote_addr(self):
        while True:
            response = self._server_request()
            if len(response) == 6 and response != b"\0" * 6:
                ip, port = struct.unpack("!4sH", response)
                ip = socket.inet_ntoa(ip)
                return ip, port
            sleep(const.ADDR_WAIT_TIME)


def get_args():
    parser = argparse.ArgumentParser(
        description="Nat traversal client")
    parser.add_argument(
        "-s", "--server",
        required=True,
        help="traversal server ip")
    parser.add_argument(
        "--id",
        default=uuid.uuid4().hex,
        help="client id")
    parser.add_argument(
        "-r", "--remote",
        required=True,
        help="remote id")
    return parser.parse_args()


def send_and_recv(connection, string):
    print("Send {} to remote...".format(string))
    connection.send(string.encode())
    try:
        while True:
            data = connection.recv()
            print("Received {}".format(data.decode()))
    except socket.timeout:
        print("No data received")


def main():
    args = get_args()
    print("MY ID:", args.id)
    print("REMOTE ID:", args.remote)
    client = NATTraversalClient(args.server, args.id, args.remote)
    connection = client.connect()
    print("OK!")
    connection.keepalive_sender.start()
    send_and_recv(connection, args.id)
    while True:
        msg = input("Message to send:")
        send_and_recv(connection, msg)

if __name__ == '__main__':
    main()
