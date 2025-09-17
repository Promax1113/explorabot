import random
import socket
import struct
import json
import time
import os
from typing import Final

"""CONSTANTS"""

ROBOT_IP: Final = "10.10.10.1" if not os.getenv("ROBOIP") else os.getenv("ROBOIP")
MOTOR_SOCKET_ADDR = (ROBOT_IP, 7778)


def connect_to_robot(port):
    global ROBOT_IP
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((ROBOT_IP, port))
    sock.settimeout(None)

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


def dgram_connect_to_robot(port):
    global ROBOT_IP
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    print(f"Created datagram socket, awaiting for data to be sent to the robot.")
    return sock


def receive(sock: socket.socket, decode=True) -> dict | bytes:
    sock.settimeout(3)
    try:
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
    except socket.timeout:
        return {"reason": "timeout"}
    if decode:
        return json.loads(received.decode())

    return received


def raw_send(sock: socket.socket, data: bytes):
    sock.sendall(data)


def send(sock: socket.socket, data: bytes):
    assert isinstance(data, bytes)

    sock.send(struct.pack("!I", len(data)))
    sock.sendall(data)


def dgram_send(sock: socket.socket, data: bytes):
    assert isinstance(data, bytes)
    sock.sendto(struct.pack("!I", len(data)), MOTOR_SOCKET_ADDR)
    sock.sendto(data, MOTOR_SOCKET_ADDR)


if __name__ == "__main__":
    sk = connect_to_robot(7777)
    sk = connect_to_robot(7778)
    sk = connect_to_robot(7779)
