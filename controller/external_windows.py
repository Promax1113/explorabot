from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit
import configparser


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setup_layout()
        self.resize(400, 200)

    def setup_layout(self):
        layout = QVBoxLayout()
