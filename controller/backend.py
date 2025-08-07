import random
import socket
import struct
import json
import time
from typing import Final

"""CONSTANTS"""

ROBOT_IP: Final = "10.10.10.1"


def connect_to_robot(port):
    global ROBOT_IP
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

    sock.connect((ROBOT_IP, port))

    _number_check = random.randint(0, 255)

    sock.sendall(struct.pack("!I", _number_check))
    check_data = None
    start_time = time.time()
    while not check_data:
        if time.time() - start_time > 2:
            sock.shutdown(-1)
            exit(-1)
        check_data = sock.recv(4)

    check_data = struct.unpack("!I", check_data)[0]
    if not check_data == _number_check:
        sock.shutdown(-1)
        exit()
    print(f"Created socket and connected to {ROBOT_IP}:{port}")

    return sock


def receive(sock: socket.socket, decode=True) -> dict | bytes:
    message_size = None
    while not message_size:
        message_size = sock.recv(4)
    message_size = struct.unpack("!I", message_size)[0]

    received = b""

    while len(received) < message_size:
        data = sock.recv(min(message_size - len(received), 1024))
        while not data:
            data = sock.recv(min(message_size - len(received), 1024))
        received += data

    if decode:
        return json.loads(received.decode())

    return received


def raw_send(sock: socket.socket, data: bytes):
    sock.sendall(data)


def send(sock: socket.socket, data: bytes):
    assert isinstance(data, bytes)
    sock.send(struct.pack("!I", len(data)))
    sock.sendall(data)


if __name__ == "__main__":
    sk = connect_to_robot(7777)
    sk = connect_to_robot(7778)
    sk = connect_to_robot(7779)
