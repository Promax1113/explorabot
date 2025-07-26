import json
import random
import socket
import struct
import threading
import time
from typing import Final

import serial

from camera import setup_camera

"""CONSTANTS"""

PORT: Final = "/dev/ttyACM0"
BIND_IP: Final = "0.0.0.0"
RETRIES: Final = 5

translated_dict = {
    "header": "motor",
    "right_first": 0,
    "left_first": 0,
    "right_second": 0,
    "left_second": 0,
    "right_speed": 0,
    "left_speed": 0,
    "camera_horizontal": 90,
    "camera_vertical": 90,
}


def socket_setup(port: int) -> socket.socket:
    # Setup IPv4 socket using UDP for lowest latency.
    server = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind((BIND_IP, port))
    client = None

    server.listen(1)
    print(f"Listening on {(BIND_IP, port)}...")

    while client == None:
        client, _addr = server.accept()
        print(f"Connection incoming from {_addr}")
    check_data = client.recv(4)
    check_data = struct.unpack("!I", check_data)[0]

    client.sendall(struct.pack("!I", check_data))
    return client


def serial_setup():
    global PORT, RETRIES
    try:
        ser = serial.Serial(port=PORT, baudrate=9600)
    except serial.SerialException as e:
        print("There was an error:", e)
        print(f"Retrying {RETRIES} times.")
        for _ in range(RETRIES):
            try:
                ser = serial.Serial(port=PORT, baudrate=9600)
                break
            except:
                time.sleep(1)
                pass
                ser = None

        if not ser:
            exit(-1)
    time.sleep(1)
    # Check the connection works well.
    _number_check = random.randint(0, 255)
    ser.write(bytes([_number_check]))

    check = None

    while not check or check != _number_check:
        check = ser.readline()
        check = int(check.decode())

    print(f"Arduino Board connected on {PORT} at baud rate 9600.")

    return ser


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


def serial_read(ser: serial.Serial):
    return ser.readline()


def serial_write(ser: serial.Serial, data):
    ser.write((json.dumps(data) + "\n").encode())


def read_sensor(ser):
    serial_write(ser, {"header": "sensor"})
    return serial_read(ser)


def write_motor(ser, data: dict, last_data: dict):
    # serial_write(ser, {"header": "motor", "right_first": 1, "left_first": 1, "right_second": 0, "left_second": 0})
    global translated_dict

    if data["lx"] == 0:
        translated_dict["right_first"] = 1 if data["ly"] > 0 else 0
        translated_dict["left_first"] = 1 if data["ly"] > 0 else 0
        translated_dict["right_second"] = (
            0 if translated_dict["right_first"] == 1 else 1
        )
        translated_dict["left_second"] = 0 if translated_dict["left_first"] == 1 else 1

        translated_dict["right_speed"] = abs(data["ly"]) * 255
        translated_dict["left_speed"] = abs(data["ly"]) * 255

    translated_dict["camera_horizontal"] -= data["cam_horiz"] * 13
    translated_dict["camera_vertical"] += data["cam_vert"] * 13

    if translated_dict["camera_horizontal"] < 20:
        translated_dict["camera_horizontal"] = 20
    elif translated_dict["camera_horizontal"] > 160:
        translated_dict["camera_horizontal"] = 160
    if translated_dict["camera_vertical"] < 20:
        translated_dict["camera_vertical"] = 20
    elif translated_dict["camera_vertical"] > 160:
        translated_dict["camera_vertical"] = 160
    serial_write(ser, translated_dict)
    return translated_dict


def setup_sockets():
    data_socket = socket_setup(7777)
    motor_socket = socket_setup(7778)
    command_socket = socket_setup(7779)
    return data_socket, motor_socket, command_socket


if __name__ == "__main__":
    ser = serial_setup()

    data_socket, motor_socket, command_socket = setup_sockets()

    reset = False

    # while not reset:
    # imagine motor_socket gets the input from the controller

    last_horiz_camera_input = 0
    last_vert_camera_input = 0
    last_movement_data = {"lx": 0, "ly": 0, "camera_horiz": 0, "camera_vert": 0}
    last_translated_data = translated_dict

    while True:
        try:
            ok = None
            while not ok:
                ok = data_socket.recv(4)
                if ok and struct.unpack("!I", ok)[0] == 1:
                    break

            movement_data: dict = receive(motor_socket, decode=True)  # type: ignore

            movement_data["ly"] = (
                0 if movement_data["lx"] > movement_data["ly"] else movement_data["ly"]
            )
            movement_data["lx"] = (
                0 if movement_data["ly"] > movement_data["lx"] else movement_data["lx"]
            )

            if not sum(movement_data.values()) == 0:
                last_translated_data = write_motor(
                    ser, movement_data, last_translated_data
                )
            elif last_movement_data["lx"] > 0 and movement_data["lx"] < 0.1:
                last_translated_data = write_motor(
                    ser, movement_data, last_translated_data
                )
            elif last_movement_data["ly"] > 0 and movement_data["ly"] < 0.1:
                last_translated_data = write_motor(
                    ser, movement_data, last_translated_data
                )

            sensor_data = read_sensor(ser)
            last_movement_data = movement_data
            if (
                not json.loads(sensor_data.decode())["humidity"]
                or not json.loads(sensor_data.decode())["temperature"]
            ):
                print("dht sensor reading failed, retrying...")
                sensor_data = read_sensor(ser)
            data_socket.send(struct.pack("!I", (len(sensor_data))))
            data_socket.sendall(sensor_data)
        except ConnectionResetError or ConnectionRefusedError:
            data_socket, motor_socket, command_socket = setup_sockets()
