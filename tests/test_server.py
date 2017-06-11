# Echo server program
import socket

HOST = ''
PORT = 50008
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.settimeout(2)
    s.bind((HOST, PORT))
    while True:
        try:
            data, addr = s.recvfrom(1024)
            print('Received {} from {}'.format(data, addr))
            s.sendto(data[::-1], addr)
        except socket.timeout:
            pass
