import json
import socket
import struct
import sys
import time
from types import FunctionType, MethodType
import cv2 as cv
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QImage, QPixmap
from PyQt5.QtWidgets import (
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
    QSlider,
)
import pygame
from external_windows import SettingsWindow
from backend import (
    ROBOT_IP,
    connect_to_robot,
    receive,
    raw_send,
    send,
    dgram_connect_to_robot,
    dgram_send,
)
from gamepad_input import get_gamepad_input, get_keyboard_input, BASE_INPUT_DICT
import threading


class Choice:
    def __init__(
        self, text: str, action: str = "", action_function: MethodType | None = None
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
        self.input_mode = "gamepad"

        self.clock = pygame.time.Clock()

    def run(self):
        match self.input_mode:
            case "keyboard":
                pass
            case "gamepad":
                self.joystick = pygame.joystick.Joystick(0)
            case _:
                pass
        while self._run_flag:
            match self.input_mode:
                case "keyboard":
                    self.input = get_keyboard_input()
                case "gamepad":
                    self.input = get_gamepad_input(self.joystick, self.round_digits)
            self.input_ready_signal.emit(self.input)
            if self.input_mode == "keyboard":
                self.clock.tick(60)
            else:
                self.clock.tick(60)


class CameraThread(Thread):
    frame_ready_signal = pyqtSignal(QImage)

    def __init__(self, url) -> None:
        super().__init__()
        self.source = url

    def run(self) -> None:
        self.capture = cv.VideoCapture(self.source)
        while self._run_flag:
            ret, frame = self.capture.read()
            if not ret:
                frame = cv.imread("./ui/nocamera.png")
                rgb_frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
                height, width, channel_count = rgb_frame.shape
                # Create a deep-copied QImage to avoid dangling pointers to numpy memory
                image = QImage(
                    rgb_frame.data,
                    width,
                    height,
                    width * channel_count,
                    QImage.Format_RGB888,
                ).copy()
                self.frame_ready_signal.emit(image)
                self.msleep(10)
            else:
                rgb_frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
                height, width, channel_count = rgb_frame.shape

                bytes_per_line = width * channel_count

                # Create a deep-copied QImage to avoid dangling pointers to numpy memory
                self.qt_compatible_image = QImage(
                    rgb_frame.data,
                    width,
                    height,
                    bytes_per_line,
                    QImage.Format.Format_RGB888,
                ).copy()
                self.frame_ready_signal.emit(self.qt_compatible_image)

    def stop(self) -> None:
        super().stop()
        if hasattr(self, "capture") and self.capture is not None:
            self.capture.release()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.input = BASE_INPUT_DICT
        self.window_layout = QGridLayout()
        self.settings_window = None
        self.timer = QTimer()

        pygame.init()
        pygame.joystick.init()

        self.setWindowTitle("Robot Controller")
        self.resize(800, 400)

        self.setup_layout()
        self.setup_threads()

    def setup_threads(self):
        self.gamepad_thread = GamepadInputThread()
        self.gamepad_thread.input_ready_signal.connect(self.set_input)

        self.camera_thread = CameraThread(f"http://{ROBOT_IP}:8080/onboard-camera")
        self.camera_thread.frame_ready_signal.connect(self.update_image)

        self.external_camera_thread = threading.Thread(target=self.run_video_window)
        self._input = {}
        self.input = {}

    def setup_layout(self):
        self.container = QWidget()
        self.setCentralWidget(self.container)
        self.container.setLayout(self.window_layout)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.setup_sockets)
        self.window_layout.addWidget(self.connect_button, 0, 0)
        self.connect_window_layout = self.window_layout
        self.image_label = QLabel()
        self.window_layout.addWidget(self.image_label, 3, 0, 3, 3)

    def communicate_with_robot(self):
        raw_send(self.sensor_socket, struct.pack("!I", 1))
        if not any(self._input.values()):
            self.input = BASE_INPUT_DICT
        print(self.input)
        dgram_send(self.motor_socket, json.dumps(self.input).encode())
        try:
            _data = self.get_sensor_data()
            if not "reason" in _data.keys():
                self.data = _data

        except (ConnectionResetError, BrokenPipeError):
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
        self.update_sensor_labels(self.data)

    def reset(self):
        self.gamepad_thread.stop()
        self.clear_layout(self.window_layout)
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

    def run_video_window(self):
        cap = cv.VideoCapture(f"http://{ROBOT_IP}:8081/onboard-camera", cv.CAP_FFMPEG)
        while True:
            if not cap.isOpened():
                print("Error: Cannot open video stream")
                return
            ret, frame = cap.read()

    def update_image(self, image):
        pixmap = QPixmap.fromImage(image)
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled_pixmap)

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
                        lambda _, func=choice.action_function: func(dialog=dialog)
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
        self._input = input
        if self.gamepad_thread.input_mode == "keyboard":
            #! this needs serious refactoring
            if self._input["up"] and not self._input["down"]:
                self.input["ly"] = (
                    self._input["up"] * self.keyboard_speed_slider.value() / 100
                )
            elif self._input["down"] and not self._input["up"]:
                self.input["ly"] = (
                    -self._input["down"] * self.keyboard_speed_slider.value() / 100
                )
            elif self._input["left"] and not self._input["right"]:
                self.input["lx"] = (
                    self._input["left"] * self.keyboard_speed_slider.value() / 100
                )
            elif self._input["right"] and not self._input["left"]:
                self.input["lx"] = (
                    -self._input["right"] * self.keyboard_speed_slider.value() / 100
                )

            elif self._input["c_up"] and not self._input["c_down"]:
                self.input["cam_vert"] = (
                    self._input["c_up"] * self.keyboard_speed_slider.value() / 100
                )
            elif self._input["c_down"] and not self._input["c_up"]:
                self.input["cam_vert"] = (
                    -self._input["c_down"] * self.keyboard_speed_slider.value() / 100
                )

            elif self._input["c_left"] and not self._input["c_right"]:
                self.input["cam_horiz"] = (
                    self._input["c_left"] * self.keyboard_speed_slider.value() / 100
                )
            elif self._input["c_right"] and not self._input["c_left"]:
                self.input["cam_horiz"] = (
                    -self._input["c_right"] * self.keyboard_speed_slider.value() / 100
                )

        pygame.event.pump()

    def open_settings_window(self):
        if self.settings_window == None:
            self.settings_window = SettingsWindow()
        self.settings_window.show()
        self.settings_window.raise_()

    def setup_sockets(self):
        self.clear_layout(self.window_layout)
        self.status_text = QLabel("Please wait...")
        self.window_layout.addWidget(self.status_text)
        if not self.gamepad_check():
            return
        self.gamepad_thread.start()

        try:

            self.sensor_socket: socket.socket = connect_to_robot(7777)
            time.sleep(0.5)
            self.motor_socket: socket.socket = dgram_connect_to_robot(7778)
            time.sleep(0.5)
            self.command_socket: socket.socket = connect_to_robot(7779)
            time.sleep(0.5)
            # self.external_camera_thread.start()
            self.status_text.setText("")
            if self.gamepad_thread.input_mode == "keyboard":
                self.keyboard_speed_slider = QSlider(Qt.Orientation.Vertical, self)
                self.keyboard_speed_slider.setRange(0, 100)
                self.keyboard_speed_slider.setTickPosition(
                    QSlider.TickPosition.TicksBothSides
                )
                self.window_layout.addWidget(self.keyboard_speed_slider)

            # self.camera_thread.start()
        except (ConnectionRefusedError, OSError) as e:
            self.status_text.setText("")
            self.summon_dialog_box_on_error(
                error_type="info",
                error={
                    "title": "Could not connect to the robot.",
                    "message": f"Could not connect to the robot. Error: {e}",
                },
            )
            return

        self.timer.timeout.connect(self.communicate_with_robot)
        self.timer.start(500)

    def reconnect(self, dialog: QDialog):
        dialog.accept()
        self.reset()
        self.timer.stop()
        self.setup_sockets()

    def set_keyboard_mode(self, dialog: QDialog):
        dialog.accept()
        self.gamepad_thread.input_mode = "keyboard"

    def get_sensor_data(self) -> dict:
        sensor_data = receive(self.sensor_socket)
        assert isinstance(sensor_data, dict)
        return sensor_data

    def gamepad_check(self):
        if pygame.joystick.get_count() < 1:
            if self.gamepad_thread.input_mode == "keyboard":
                return True
            self.summon_dialog_box_on_error(
                error_type="choice",
                error={
                    "title": "No controller was found.",
                    "message": "No controller was detected on this system.\nPlease check it is plugged in and working.",
                },
                choices=[
                    Choice(
                        text="Use keyboard",
                        action="",
                        action_function=self.set_keyboard_mode,
                    ),
                    Choice(text="Ignore and continue", action="accept"),
                ],
            )
            return False if self.gamepad_thread.input_mode == "gamepad" else True
        return True

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())


def main():
    app = QApplication(sys.argv)
    window = MainWindow()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
