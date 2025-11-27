import logging
import os
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QStackedWidget, QPushButton, QLabel, 
                               QFrame, QStyle, QButtonGroup, QSplitter, QTextEdit)
from PySide6.QtCore import Qt, QSize, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from .collector import CollectorPage
from ..utils.logger import JTLogger


class QtLogHandler(QObject, logging.Handler):
    """ Custom logging handler that emits log messages as Qt signals. """

    log_signal = Signal(str)
    """ Signal emitted with log message string. """

    def __init__(self, parent: QObject | None = None):
        """ Initialize the QtLogger with optional parent. """
        super().__init__(parent)
        logging.Handler.__init__(self, level=logging.INFO)
        
    def emit(self, record):
        """ Send the formatted log record as a Qt signal. """
        log_entry = self.format(record)
        self.log_signal.emit(log_entry)


class JobToolsApp(QMainWindow):
    """ Main application window for JobTools. """

    def __init__(self):
        super().__init__()
        # Window setup
        self.setWindowTitle("JobTools")
        self.resize(1200, 700)
        # Main Container
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        # Horizontal layout: Sidebar | Content Splitter
        main_layout = QHBoxLayout(self.main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        # Sidebar Navigation
        self._setup_nav_panel()
        main_layout.addWidget(self.sidebar)
        # Content Splitter
        self.content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.content_splitter.setObjectName("content_splitter")
        # Pages Area
        self.pages = QStackedWidget()
        self.pages.setObjectName("pages")
        self.content_splitter.addWidget(self.pages)
        # Log Panel
        self._setup_log_panel()
        self.content_splitter.addWidget(self.log_panel)
        self.log_panel.hide()
        self.content_splitter.setCollapsible(0, False)
        self.content_splitter.setStretchFactor(0, 1)
        self.content_splitter.setStretchFactor(1, 0)
        main_layout.addWidget(self.content_splitter)
        # Add Stylesheet
        self._update_theme()
        # Setup Logging
        self.log_handler = QtLogHandler()
        logger = JTLogger()
        logger.addHandler(self.log_handler)
        # Connect handler's signal to GUI slot
        self.log_handler.log_signal.connect(self._on_console_output)
        # Populate Pages
        self.add_page(QStyle.StandardPixmap.SP_FileDialogContentsView, "collector", CollectorPage())
        self.add_page(QStyle.StandardPixmap.SP_BrowserReload, "settings", SettingsPage(), align_bottom=True)
        # Select first page by default
        if self.nav_group.buttons():
            self.nav_group.buttons()[0].click()

    def _setup_nav_panel(self):
        """Creates the left navigation sidebar with buttons."""
        # Sidebar container
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(60)
        self.sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 10, 0, 10)
        sidebar_layout.setSpacing(0)
        # Top Section
        self.sidebar_top = QVBoxLayout()
        self.sidebar_top.setSpacing(10)
        self.sidebar_top.setContentsMargins(0,0,0,0)
        sidebar_layout.addLayout(self.sidebar_top)
        # Middle Spacer
        sidebar_layout.addStretch()
        # Bottom Section
        self.sidebar_bottom = QVBoxLayout()
        self.sidebar_bottom.setSpacing(10)
        self.sidebar_bottom.setContentsMargins(0,0,0,0)
        sidebar_layout.addLayout(self.sidebar_bottom)
        # Navigation Button Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.buttonClicked.connect(self._on_nav_button_clicked)

    def _setup_log_panel(self):
        """Creates the bottom log panel with header and text area."""
        # Log Panel Container
        self.log_panel = QWidget()
        self.log_panel.setObjectName("log_panel")
        log_layout = QVBoxLayout(self.log_panel)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(0)
        # Header
        header = QFrame()
        header.setObjectName("log_header")
        header.setFixedHeight(30)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 5, 0)
        # Header Title
        title = QLabel("CONSOLE")
        title.setStyleSheet("font-weight: bold; font-size: 11px;")
        # Close Button
        close_btn = QPushButton()
        close_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DockWidgetCloseButton))
        close_btn.setFixedSize(24, 24)
        close_btn.setFlat(True)
        close_btn.clicked.connect(self.log_panel.hide)
        # Assemble Header
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        # Log Text Area
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("log_output")
        self.log_output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        # Assemble Log Panel
        log_layout.addWidget(header)
        log_layout.addWidget(self.log_output)

    def _update_theme(self, theme: str | None = None):
        """ Update application stylesheet based on system theme.

        Parameters
        ----------
        theme : str | None
            Optional theme override ("light" or "dark"). If None, use system setting.
        """
        app = QApplication.instance()
        if app is None or not hasattr(app, "setStyleSheet"):
            return
        # Determine system color scheme
        color_scheme = QGuiApplication.styleHints().colorScheme()
        if theme == "dark" or color_scheme == Qt.ColorScheme.Dark:
            file_name = "dark_theme"
        elif theme == "light" or color_scheme == Qt.ColorScheme.Light:
            file_name = "light_theme"
        else:
            file_name = "light_theme"
        # Load and apply stylesheet
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            qss_path = os.path.join(base, "styles", f"{file_name}.qss")
            with open(qss_path, "r") as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            JTLogger().warning(f"Failed to load stylesheet '{file_name}': {e}")

    def add_page(self, icon, name, widget, align_bottom=False):
        """ Add a new page to the application with navigation button.

        Parameters
        ----------
        icon : QStyle.StandardPixmap | str
            Icon for the navigation button (standard pixmap or file path).
        name : str
            Name identifier for the page.
        widget : QWidget
            The page widget to display.
        align_bottom : bool, optional
            Whether to align the button at the bottom of the sidebar, by default False.
        """
        # Create navigation button
        btn = QPushButton()
        btn.setCheckable(True)
        btn.setIconSize(QSize(30, 30))
        btn.setToolTip(name.capitalize())
        # Set icon
        if isinstance(icon, QStyle.StandardPixmap):
            btn.setIcon(self.style().standardIcon(icon))
        else:
            btn.setIcon(QIcon(icon))
        # Add button to appropriate sidebar section
        if align_bottom:
            self.sidebar_bottom.addWidget(btn)
        else:
            self.sidebar_top.addWidget(btn)
        # Add button to group
        self.nav_group.addButton(btn)
        # Add page to stacked widget
        index = self.pages.addWidget(widget)
        btn.setProperty("page_index", index)

    @Slot()
    def _on_console_output(self, text):
        """ Handle text coming from logger. """
        # Auto-show panel if hidden and text isn't just whitespace
        if self.log_panel.isHidden() and text.strip():
            self.log_panel.show()
            sizes = self.content_splitter.sizes()
            if sizes[1] == 0:
                total = sum(sizes)
                self.content_splitter.setSizes([int(total * 0.7), int(total * 0.3)])
        # Append text to log output
        self.log_output.append(text)
        sb = self.log_output.verticalScrollBar()
        sb.setValue(sb.maximum())

    @Slot()
    def _on_nav_button_clicked(self, btn):
        """ Handle navigation button clicks. """
        index = btn.property("page_index")
        if index is not None:
            self.pages.setCurrentIndex(index)


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Settings</h2>"))
        layout.addWidget(QLabel("Theme: Dark"))
        layout.addStretch()
