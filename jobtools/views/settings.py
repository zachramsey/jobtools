from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Settings</h2>"))
        layout.addWidget(QLabel("Theme: Dark"))
        layout.addStretch()