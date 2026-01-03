import logging

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget

from ..utils import JDLogger, get_theme_colors


class QtLogHandler(QObject, logging.Handler):
    """Custom logging handler that emits log messages as Qt signals."""

    log_signal = Signal(str)
    """ Signal emitted with log message string. """

    def __init__(self, parent: QObject | None = None):
        """Initialize the QtLogger with optional parent."""
        super().__init__(parent)
        logging.Handler.__init__(self, level=logging.INFO)

    def emit(self, record):
        """Send the formatted log record as a Qt signal."""
        self.log_signal.emit(self.format(record))


class ConsolePage(QWidget):
    """Bottom log panel for displaying console output."""

    def __init__(self):
        """Initialize the ConsolePage."""
        super().__init__()

        # Layout Setup
        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)    # type: ignore
        self.layout().setSpacing(0)                     # type: ignore

        # Logger Setup
        log_handler = QtLogHandler()
        logger = JDLogger()
        logger.configure("INFO")
        logger.addHandler(log_handler)
        log_handler.log_signal.connect(self._on_console_output)

        # Log Text Area
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_output.setStyleSheet(f'font-family: "Roboto Mono", monospace; \
                                        color: {get_theme_colors()["primaryTextColor"]};')

        # Assemble Log Panel
        self.layout().addWidget(self.log_output)        # type: ignore

    @Slot()
    def _on_console_output(self, text):
        """Handle text coming from logger."""
        if not text.strip():
            return

        # Append text to log output
        self.log_output.append(text)
        sb = self.log_output.verticalScrollBar()
        sb.setValue(sb.maximum())
