import argparse
import socket
import struct
import uuid
from random import randrange
from time import sleep

import constants as const
from nat_connection import NatConnection


class TraversalError(Exception):
    pass


class NATTraversalClient:
    def __init__(self, server_ip, local_id, remote_id):
        self.server_ip = server_ip
        self.local_id = local_id
        self.remote_id = remote_id

    def connect(self):
        while True:
            self.sock = socket.socket(type=socket.SOCK_DGRAM)
            for _ in range(const.PORT_PUNCHING_PROBES):
                self.sock.settimeout(self._rand_timeout())
                connection = self._try_punch_hole()
                if connection:
                    return connection

    def _try_punch_hole(self):
        print("Waiting for remote addr from server...")
        remote_addr = self._get_remote_addr()
        print("Remote addr for {}: {}".format(self.remote_id, remote_addr))

        connection = NatConnection(self.sock, remote_addr)
        print("Send hello packets to ", remote_addr)
        self._send_hello_packets(connection)
        print("Waiting for response at", connection.sock.getsockname())
        try:
            while True:
                data = connection.recv_raw()
                if data == const.HELLO_PACKET:
                    print("Received hello packet!")
                    self._send_hello_packets(connection)
                    return connection
        except socket.timeout:
            print("No hello packet from remote")
        except ConnectionError as e:
            print("Connection error:", e)

    def _send_hello_packets(self, connection):
        for _ in range(const.HELLO_PACKETS_COUNT):
            connection.send(const.HELLO_PACKET)

    @staticmethod
    def _rand_timeout():
        return const.BASE_SOCKET_TIMEOUT * randrange(
            int(const.TIMEOUT_MULTIPLIER_RANGE[0] * 100),
            int(const.TIMEOUT_MULTIPLIER_RANGE[1] * 100)
        ) / 100

    def _server_request(self):
        request = "\n".join(
            (const.COOKIE.decode(), self.local_id, self.remote_id))
        for _ in range(const.SERVER_REQUEST_PROBES):
            self.sock.sendto(request.encode(), (self.server_ip, const.PORT))
            try:
                while True:
                    data, addr = self.sock.recvfrom(1024)
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
