# Telescope Socket Message Simulator

import socket

IP = "172.23.1.60"
PORT = 6023

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((IP, PORT))

sock.sendall("INIT\n")
msg = sock.recv(128)
print msg

sock.close()
