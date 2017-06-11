import argparse
import re
import socket
import struct
import uuid
from time import sleep

import constants as const
from clientserver_connection import ClientServerConnection
from connections_repeater import ConnectionsRepeater
from enums import Operation, OperationResult
from nat_connection import NatConnection
from udp_connection import UdpConnection


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
        self.udp_sock.settimeout(const.UDP_SOCKET_TIMEOUT)
        print("Bind to {}".format(self.udp_sock.getsockname()))
        self._update_connection()
        return True

    def _process_announce(self):
        print("Announce addr to server...")
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
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "-l", "--listen",
        help="interface and port to listen (example: 0.0.0.0:1234)"
    )
    action.add_argument(
        "-c", "--connect",
        help="ip and port to connect (example: 127.0.0.1:1234)"
    )
    return parser.parse_args()


def get_server_connection(local_addr):
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.bind(local_addr)
    sock.settimeout(const.LOCAL_CONNECTION_TIMEOUT)
    return UdpConnection(sock, recv_strict=False)


def get_client_connection(remote_addr):
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.settimeout(const.LOCAL_CONNECTION_TIMEOUT)
    return UdpConnection(sock, remote_addr)


def parse_hostport(address):
    match = re.match("([\w.-]+):(\d+)", address)

    if not match:
        raise Exception(
            "{} has wrong format (ip:port required)".format(address))

    host, port = match.groups()
    port = int(port)
    return host, port


def main():
    args = get_args()
    if args.listen:
        local_connection = get_server_connection(parse_hostport(args.listen))
    else:
        local_connection = get_client_connection(parse_hostport(args.connect))
    with local_connection:
        print("MY ID:", args.id)
        print("REMOTE ID:", args.remote)
        client = NATTraversalClient(args.server, args.id, args.remote)
        nat_connection = client.connect()
        print("NAT traversal completed!")
        with nat_connection:
            nat_connection.keepalive_sender.start()
            repeater = ConnectionsRepeater(nat_connection, local_connection)
            repeater.start()
            try:
                while True:
                    sleep(1)
            except KeyboardInterrupt:
                repeater.stop()

if __name__ == '__main__':
    main()
