class UdpConnection:
    def __init__(self, sock, remote_addr=None, recv_strict=True):
        self.sock = sock
        self.remote_addr = remote_addr
        self.recv_strict = recv_strict

    def send(self, data):
        self.sock.sendto(data, self.remote_addr)

    def recv(self):
        while True:
            data, addr = self.sock.recvfrom(8192)
            if not self.recv_strict or addr == self.remote_addr:
                self.remote_addr = addr
                return data

    def close(self):
        self.sock.close()

    def __enter__(self):
        self.sock.__enter__()

    def __exit__(self, *args):
        self.sock.__exit__(*args)
