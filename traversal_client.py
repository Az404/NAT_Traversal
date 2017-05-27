import argparse
import socket
import struct
import uuid
from random import randrange
from time import sleep

import constants as const


class TraversalError(Exception):
    pass


class NATTraversalClient:
    def __init__(self, server_ip, local_id):
        self.local_id = local_id
        self.server_ip = server_ip

    def connect(self, remote_id):
        self.sock = socket.socket(type=socket.SOCK_DGRAM)
        for _ in range(const.PUNCHING_PROBES):
            self.sock.settimeout(const.TIMEOUT * randrange(25, 200) / 100)
            remote_addr = self.get_remote_addr(remote_id)
            print("Remote addr for {}: {}".format(remote_id, remote_addr))
            if not remote_addr:
                raise TraversalError("Can't get remote address from server")
            print("Send hello packet to ", remote_addr)
            self.sock.sendto(const.HELLO_PACKET, remote_addr)
            print("Waiting for response at", self.sock.getsockname())
            try:
                while True:
                    data, addr = self.sock.recvfrom(1024)
                    if data == const.HELLO_PACKET and addr == remote_addr:
                        return self.sock, addr
            except socket.timeout:
                print("No hello packet from remote")
            except ConnectionError as e:
                print("Connection error:", e)
        else:
            raise TraversalError("Connection failed: no any hello packet")

    def server_request(self, remote_id):
        request = "\n".join((const.COOKIE, self.local_id, remote_id))
        for _ in range(const.PROBES):
            self.sock.sendto(request.encode(), (self.server_ip, const.PORT))
            try:
                while True:
                    data, addr = self.sock.recvfrom(1024)
                    if addr[0] == self.server_ip:
                        break
                return data
            except socket.timeout:
                pass

    def get_remote_addr(self, remote_id):
        for _ in range(const.PROBES):
            response = self.server_request(remote_id)
            if response and len(response) == 6 and response != b"\0" * 6:
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


def main():
    args = get_args()
    print("MY ID:", args.id)
    print("REMOTE ID:", args.remote)
    client = NATTraversalClient(args.server, args.id)
    while True:
        try:
            sock, remote_addr = client.connect(args.remote)
        except Exception as e:
            print(e)
        else:
            break
    print("OK!")
    sock.sendto(const.HELLO_PACKET, remote_addr)
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            print("Received {} from {}".format(data, addr))
    except socket.timeout:
        print("No data received")

if __name__ == '__main__':
    main()
