import sys

from PySide6.QtWidgets import QApplication

from jobtools import JobToolsApp

if __name__ == "__main__":
    app = QApplication()
    window = JobToolsApp()
    window.showMaximized()
    sys.exit(app.exec())
