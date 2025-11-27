import sys
from PySide6.QtWidgets import QApplication
from jobtools import JobToolsApp


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JobToolsApp()
    window.show()
    sys.exit(app.exec())
