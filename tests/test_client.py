# Echo client program
import socket

HOST = '127.0.0.1'
PORT = 50007
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.settimeout(2)
    s.connect((HOST, PORT))
    while True:
        try:
            s.send(b'Hello, world')
            data = s.recv(1024)
            print('Received', repr(data))
        except socket.timeout:
            pass
