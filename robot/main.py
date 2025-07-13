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

translated_dict = {"header": "motor", "right_first": 0, "left_first": 0, "right_second": 0, "left_second": 0, "right_speed": 0, "left_speed": 0, "camera_horizontal": 90, "camera_vertical": 90}


def socket_setup(port: int):
    # Setup IPv4 socket using UDP for lowest latency.
    server = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    server.bind((BIND_IP, port))
    client = None

    server.listen(1)
    print(f"Listening on {(BIND_IP, port)}...")

    while client == None:
        client, _addr = server.accept()
        print(f"Conneection incoming from {_addr}")
    check_data = client.recv(4)
    check_data = struct.unpack("!I", check_data)[0]

    client.sendall(struct.pack("!I", check_data))


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

def serial_read(ser: serial.Serial):
    return ser.readline()

def serial_write(ser: serial.Serial, data):
    ser.write((json.dumps(data) + "\n").encode())

def read_sensor(ser):
    serial_write(ser, {"header": "sensor"})
    return serial_read(ser)



def write_motor(ser, data: dict):
    # serial_write(ser, {"header": "motor", "right_first": 1, "left_first": 1, "right_second": 0, "left_second": 0})
    global translated_dict
    if data["lx"] == 0:
        translated_dict["right_first"] = 1 if data["ly"] > 0 else 0
        translated_dict["left_first"] = 1 if data["ly"] > 0 else 0
        translated_dict["right_second"] = 0 if translated_dict["right_first"] == 1 else 1
        translated_dict["left_second"] = 0 if translated_dict["left_first"] == 1 else 1

        translated_dict["right_speed"] = abs(data["ly"]) * 255
        translated_dict["left_speed"] = abs(data["ly"]) * 255


    translated_dict["camera_horizontal"] -= data["camera_horiz"] * 13
    translated_dict["camera_vertical"] += data["camera_vert"] * 13

    if translated_dict["camera_horizontal"] < 20:
        translated_dict["camera_horizontal"] = 20
    elif translated_dict["camera_horizontal"] > 160:
        translated_dict["camera_horizontal"] = 160
    if translated_dict["camera_vertical"] < 20:
        translated_dict["camera_vertical"] = 20
    elif translated_dict["camera_vertical"] > 160:
        translated_dict["camera_vertical"] = 160

    
    serial_write(ser, translated_dict)

if __name__ == "__main__":
    ser = serial_setup()

    """
    data_socket = socket_setup(7777)
    motor_socket = socket_setup(7778)
    command_socket = socket_setup(7779)
    """
    reset = False


    # while not reset:
        #imagine motor_socket gets the input from the controller

    last_horiz_camera_input = 0
    last_vert_camera_input = 0
    while True:

        
        movement_data = {"ly": -0.6, "lx": 0.4, "ry": 0.2, "rx": 0.9}



        movement_data["ly"] = 0 if movement_data["lx"] > movement_data["ly"] else movement_data["ly"]
        movement_data["lx"] = 0 if movement_data["ly"] > movement_data["lx"] else movement_data["lx"]



        if not sum(movement_data.values()) == 0:
            write_motor(ser, movement_data)
        sensor_data = read_sensor(ser)
        print(sensor_data)


