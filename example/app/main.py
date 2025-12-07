import sys
from PySide6.QtWidgets import QApplication
from jobtools import JobToolsApp
from jobtools.utils.logger import JTLogger


if __name__ == "__main__":
    logger = JTLogger()
    logger.configure("DEBUG")
    app = QApplication()
    window = JobToolsApp()
    window.show()
    sys.exit(app.exec())
