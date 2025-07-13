import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QPushButton
from external_windows import SettingsWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.window_layout = QGridLayout()
        self.settings_window = None

        self.setWindowTitle("Robot Controller")
        self.resize(800, 400)

    def setup_layout(self):
        container = QWidget()
        container.setLayout(self.window_layout)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect()

    def open_settings_window(self):
        if self.settings_window == None:
            self.settings_window = SettingsWindow()
        self.settings_window.show()
        self.settings_window.raise_()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
