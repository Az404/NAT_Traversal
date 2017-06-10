class ClientServerConnection:
    def __init__(self, sock):
        self.sock = sock
        self.file = sock.makefile("rw")

    def __enter__(self):
        self.sock.__enter__()

    def __exit__(self, *args):
        self.sock.__exit__(*args)

    def readline(self):
        line = self.file.readline()
        if not line:
            raise EOFError()
        return line.replace("\n", "")

    def writeline(self, line):
        self.file.write(line + "\n")
        self.file.flush()

    def read_as_enum(self, enum_class):
        line = self.readline()
        for name, value in enum_class.__members__.items():
            if line == name:
                return value

    def write_as_enum(self, value):
        self.writeline(value.name)

    def send_and_recv(self, value, result_class):
        self.write_as_enum(value)
        return self.read_as_enum(result_class)

    def send_and_wait(self, value, expected_result):
        while True:
            response = self.send_and_recv(value, type(expected_result))
            if response == expected_result:
                return
