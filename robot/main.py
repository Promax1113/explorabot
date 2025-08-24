import json
import random
import socket
import struct
import threading
import time
from typing import Final

from numpy import right_shift
import serial

from camera import setup_camera

"""CONSTANTS"""

PORT: Final = "/dev/ttyACM0"
BIND_IP: Final = "0.0.0.0"
RETRIES: Final = 5

translated_dict_template = {
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
    global BIND_IP
    server = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
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
def dgram_socket_setup(port: int) -> socket.socket:
    global BIND_IP
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind((BIND_IP, port))

    return sock

def serial_setup():
    global PORT, RETRIES
    try:
        ser = serial.Serial(port=PORT, baudrate=9600, timeout=2)
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
    time.sleep(2)
    # # Check the connection works well.
    # _number_check = random.randint(1, 254)
    # ser.write(bytes([_number_check]))

    # check = None

    # while check != _number_check:
    #     print("checking... sent", _number_check)
    #     check = ser.readline()
    #     if not check:
    #         print("had a timeout")
    #         continue
    #     check = int(check.decode().strip())
    #     print(check)

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

def dgram_receive(sock: socket.socket, decode=True) -> dict | bytes:
    message_size = None
    while not message_size:
        message_size = sock.recvfrom(4)[0]
    message_size = struct.unpack("!I", message_size)[0]

    received = b""

    while len(received) < message_size:
        data = sock.recvfrom(min(message_size - len(received), 1024))[0]
        while not data:
            data = sock.recvfrom(min(message_size - len(received), 1024))[0]
        received += data

    return json.loads(received.decode()) if decode else received

def serial_read(ser: serial.Serial):
    return ser.readline()


def serial_write(ser: serial.Serial, data):
    ser.write((json.dumps(data) + "\n").encode())


def read_sensor(ser):
    serial_write(ser, {"header": "sensor"})
    return serial_read(ser)


def write_motor(ser, data: dict, last_data: dict):
    # serial_write(ser, {"header": "motor", "right_first": 1, "left_first": 1, "right_second": 0, "left_second": 0})
    global translated_dict_template



    translated_dict = translated_dict_template


    if data["lx"] == 0:
        translated_dict["right_first"] = 1 if data["ly"] > 0 else 0
        translated_dict["left_first"] = 1 if data["ly"] > 0 else 0
        translated_dict["right_second"] = 0 if translated_dict["right_first"] == 1 else 1
        translated_dict["left_second"] = 0 if translated_dict["left_first"] == 1 else 1
        translated_dict["right_speed"] = int(abs(data["ly"]) * 150)
        translated_dict["left_speed"] = int(abs(data["ly"]) * 150)



    elif data["ly"] == 0:
        translated_dict["right_first"] = 1 if data["lx"] > 0 else 0
        translated_dict["left_first"] = 1 if data["lx"] < 0 else 0
        translated_dict["right_second"] = 0 if translated_dict["right_first"] == 1 else 1
        translated_dict["left_second"] = 0 if translated_dict["left_first"] == 1 else 1
        translated_dict["right_speed"] = int(abs(data["lx"]) * 150)
        translated_dict["left_speed"] = int(abs(data["lx"]) * 150)




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

    print(translated_dict)
    serial_write(ser, translated_dict)
    return translated_dict


def setup_sockets():
    data_socket = socket_setup(7777)
    motor_socket = dgram_socket_setup(7778)
    command_socket = socket_setup(7779)
    return data_socket, motor_socket, command_socket


if __name__ == "__main__":
    ser = serial_setup()

    camera_thread = threading.Thread(target=setup_camera)
    camera_thread.start()
    
    data_socket, motor_socket, command_socket = setup_sockets()
    


    reset = False

    # while not reset:
    # imagine motor_socket gets the input from the controller

    last_horiz_camera_input = 0
    last_vert_camera_input = 0
    last_translated_data = translated_dict_template
    last_movement_data = {"lx": 0, "ly": 0, "cam_horiz": 0, "cam_vert": 0}
    blank_movement_data = {"lx": 0, "ly": 0, "cam_horiz": 0, "cam_vert": 0}



    while True:

        try:
           

            movement_data: dict = dgram_receive(motor_socket, decode=True)  # type: ignore



            movement_data["ly"] = (
                0 if abs(movement_data["lx"]) > abs(movement_data["ly"]) else movement_data["ly"]
            )
            movement_data["lx"] = (
                0 if abs(movement_data["ly"]) > abs(movement_data["lx"]) else movement_data["lx"]
            )
            try:
                abs_movement_data = {k: abs(v) for k, v in movement_data.items()}
                if not sum(abs_movement_data.values()) <= 0.2:
                    last_translated_data = write_motor(
                        ser, movement_data, last_translated_data
                    )
                elif abs(last_movement_data["lx"]) > 0 and abs(movement_data["lx"]) < 0.2:
                    last_translated_data = write_motor(
                        ser, blank_movement_data, last_translated_data
                    )
                elif abs(last_movement_data["ly"]) > 0 and abs(movement_data["ly"]) < 0.2:
                    last_translated_data = write_motor(
                        ser, blank_movement_data, last_translated_data
                    )



                sensor_data = read_sensor(ser)
                last_movement_data = movement_data
                if (
                    json.loads(sensor_data.decode())["humidity"]
                    or json.loads(sensor_data.decode())["temperature"]
                ):
                    print("dht sensor reading failed, retrying...")
                    sensor_data = read_sensor(ser)
                data_socket.send(struct.pack("!I", (len(sensor_data))))
                data_socket.sendall(sensor_data)
            except serial.SerialException:
                ser = serial_setup()
                continue
        except ConnectionResetError or ConnectionRefusedError:
            data_socket, motor_socket, command_socket = setup_sockets()
