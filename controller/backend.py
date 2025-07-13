import random
import socket
import struct
import time
from typing import Final

"""CONSTANTS"""

ROBOT_IP: Final = "192.168.1.60"


def connect_to_robot(port):
    global ROBOT_IP
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

    sock.connect((ROBOT_IP, port))


    _number_check = random.randint(0, 255)

    sock.sendall(struct.pack("!I", _number_check))

    check_data = sock.recv(4)
    check_data = struct.unpack("!I", check_data)
    if not check_data == _number_check:
        sock.shutdown(-1)
        exit()
    print(f"Created socket and connected to {ROBOT_IP}:{port}")

    return sock

if __name__ == "__main__":
    sk = connect_to_robot(7777)