import json
import socket
import struct
import sys
import time
from types import FunctionType, MethodType
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTableView,
    QVBoxLayout,
    QWidget,
    QGridLayout,
    QPushButton,
)
from numpy._core.multiarray import error
import pygame
from external_windows import SettingsWindow
from backend import connect_to_robot, receive, raw_send, send
from gamepad_input import get_input, BASE_INPUT_DICT


class Choice:
    def __init__(
        self, text: str, action: str, action_function: MethodType | None = None
    ) -> None:
        self.text = text
        self.action = action
        self.action_function = action_function


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
        self.timer = QTimer()

        self.setWindowTitle("Robot Controller")
        self.resize(800, 400)

        self.setup_layout()
        self.setup_threads()

    def setup_threads(self):
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
        self.connect_window_layout = self.window_layout

    def communicate_with_robot(self):
        raw_send(self.sensor_socket, struct.pack("!I", 1))
        send(self.motor_socket, json.dumps(self.input).encode())
        try:
            data = self.get_sensor_data()
        except ConnectionResetError:
            self.summon_dialog_box_on_error(
                error_type="choice",
                error={
                    "title": "The connection was reset.",
                    "message": "The connection was reset by the robot. It has most likely crashed and will restart on its own in a few seconds. \nPlease wait until the status LED on the robot indicates it is functional again.",
                },
                choices=[
                    Choice(text="Ok", action="accept"),
                    Choice(
                        text="Retry",
                        action="connect",
                        action_function=self.reconnect,
                    ),
                ],
            )

            return
        self.update_sensor_labels(data)

    def reset(self):
        self.gamepad_thread.stop()
        self.setup_layout()
        self.setup_threads()

    def update_sensor_labels(self, data: dict):
        self.sensor_data_table = QTableView()
        self.model = QStandardItemModel()

        headers = ["Sensor", "Value"]
        self.model.setHorizontalHeaderLabels(headers)
        for index, value in data.items():
            row_position = self.model.rowCount()
            index = QStandardItem(str(index))
            value = QStandardItem(str(value))

            index.setFlags(index.flags() & ~Qt.ItemFlag.ItemIsEditable)
            value.setFlags(value.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.model.insertRow(row_position, [index, value])
            self.sensor_data_table.setModel(self.model)
            self.window_layout.addWidget(self.sensor_data_table, 1, 0, 1, 2)

    def summon_dialog_box_on_error(
        self, error_type, error: dict, choices: list[Choice] = []
    ):
        dialog = QDialog()
        dialog.setWindowTitle(error["title"])

        dialog_layout = QVBoxLayout()
        label = QLabel(error["message"])

        dialog_layout.addWidget(label)

        if error_type == "info":
            accept_button = QPushButton("Ok")
            accept_button.clicked.connect(lambda _: self.kill_dialog(dialog=dialog))
            dialog_layout.addWidget(accept_button)
        elif error_type == "choice":
            button_layout = QHBoxLayout()
            for choice in choices:
                button = QPushButton(choice.text)
                if choice.action == "accept":
                    button.clicked.connect(lambda _: self.kill_dialog(dialog=dialog))
                else:
                    assert isinstance(choice.action_function, MethodType)
                    button.clicked.connect(
                        lambda _: choice.action_function(dialog=dialog)
                    )
                button_layout.addWidget(button)
            dialog_layout.addLayout(button_layout)

        dialog.setLayout(dialog_layout)

        dialog.exec()

    def kill_dialog(self, dialog: QDialog):
        dialog.accept()
        self.reset()
        if self.timer:
            self.timer.stop()

    def set_input(self, input: dict):
        self.input = input

    def open_settings_window(self):
        if self.settings_window == None:
            self.settings_window = SettingsWindow()
        self.settings_window.show()
        self.settings_window.raise_()

    def setup_sockets(self):
        try:
            self.sensor_socket: socket.socket = connect_to_robot(7777)
            time.sleep(0.5)
            self.motor_socket: socket.socket = connect_to_robot(7778)
            time.sleep(0.5)
            self.command_socket: socket.socket = connect_to_robot(7779)
            time.sleep(0.5)
        except ConnectionRefusedError or OSError:
            self.summon_dialog_box_on_error(
                error_type="info",
                error={
                    "title": "Could not connect to the robot.",
                    "message": "Could not connect to the robot, check your ports 7777, 7778 and 7779 are allowed and that the robot is on.",
                },
            )
            return
        raw_send(self.sensor_socket, struct.pack("!I", 1))

        self.timer.timeout.connect(self.communicate_with_robot)
        self.timer.start(1)

    def reconnect(self, dialog: QDialog):
        dialog.accept()
        self.reset()
        self.timer.stop()
        self.setup_sockets()

    def get_sensor_data(self) -> dict:
        sensor_data = receive(self.sensor_socket)
        assert isinstance(sensor_data, dict)
        return sensor_data


def main():
    app = QApplication(sys.argv)
    window = MainWindow()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
