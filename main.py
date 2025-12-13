from PySide6.QtWidgets import QApplication
import sys
from jobtools import JobToolsApp

if __name__ == "__main__":
    app = QApplication()
    window = JobToolsApp()
    window.show()
    sys.exit(app.exec())