import json
import socket
import struct
import sys
import time
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QPushButton
import pygame
from external_windows import SettingsWindow
from backend import connect_to_robot, receive, raw_send, send
from gamepad_input import get_input, BASE_INPUT_DICT


class Thread(QThread):
    def __init__(self) -> None:
        super().__init__()
        self._run_flag = True

    def stop(self):
        self._run_flag = False
        self.wait()


class GamepadInputThread(Thread):
    input_ready_signal = pyqtSignal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.round_digits = 3
        self.input = BASE_INPUT_DICT
        self.clock = pygame.time.Clock()
        pygame.init()
        pygame.joystick.init()
        time.sleep(0.1)
        self.joystick = pygame.joystick.Joystick(0)

    def run(self):
        while self._run_flag:
            pygame.event.pump()
            self.input = get_input(self.joystick, self.round_digits)
            self.input_ready_signal.emit(self.input)
            self.clock.tick(200)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.input = BASE_INPUT_DICT
        self.window_layout = QGridLayout()
        self.settings_window = None

        self.setWindowTitle("Robot Controller")
        self.resize(800, 400)

        self.setup_layout()

        self.gamepad_thread = GamepadInputThread()
        self.gamepad_thread.input_ready_signal.connect(self.set_input)
        self.gamepad_thread.start()

    def setup_layout(self):
        self.container = QWidget()
        self.setCentralWidget(self.container)
        self.container.setLayout(self.window_layout)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.setup_sockets)
        self.window_layout.addWidget(self.connect_button, 0, 0)

    def communicate_with_robot(self):
        raw_send(self.sensor_socket, struct.pack("!I", 1))
        send(self.motor_socket, json.dumps(self.input).encode())

        print(self.get_sensor_data())

    def set_input(self, input: dict):
        self.input = input

    def open_settings_window(self):
        if self.settings_window == None:
            self.settings_window = SettingsWindow()
        self.settings_window.show()
        self.settings_window.raise_()

    def setup_sockets(self):
        self.sensor_socket: socket.socket = connect_to_robot(7777)
        time.sleep(0.5)
        self.motor_socket: socket.socket = connect_to_robot(7778)
        time.sleep(0.5)
        self.command_socket: socket.socket = connect_to_robot(7779)
        time.sleep(0.5)
        raw_send(self.sensor_socket, struct.pack("!I", 1))

        self.timer = QTimer()
        self.timer.timeout.connect(self.communicate_with_robot)
        self.timer.start(1)

    def get_sensor_data(self):
        sensor_data = receive(self.sensor_socket)
        return sensor_data


def main():
    app = QApplication(sys.argv)
    window = MainWindow()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
