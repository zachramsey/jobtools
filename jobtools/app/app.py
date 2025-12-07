import logging
from os import path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QStackedWidget, QPushButton, QLabel, 
                               QFrame, QButtonGroup, QSplitter, QTextEdit, QScrollArea)
from PySide6.QtCore import Qt, QSize, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon, QFont, QFontDatabase
from qt_material import apply_stylesheet    # type: ignore
from .collect import CollectorPage
from .filter import FilterPage
from .sort import SortPage
from .settings import SettingsPage
from .utils import get_icon, get_sys_theme
from ..utils.logger import JTLogger


class JobToolsApp(QMainWindow):
    """ Main application window for JobTools. """

    def __init__(self):
        super().__init__()
        # Setup resources
        res_dir = path.join(path.dirname(__file__), "resources")
        
        # Add Roboto for default application font
        sans_path = path.join(res_dir, "Roboto.ttf")
        sans_font_id = QFontDatabase.addApplicationFont(sans_path)
        if sans_font_id != -1:
            sans_font = QFontDatabase.applicationFontFamilies(sans_font_id)[0]
            QGuiApplication.setFont(sans_font)

        # Add Roboto Mono for monospace font
        mono_path = path.join(res_dir, "RobotoMono.ttf")
        mono_font_id = QFontDatabase.addApplicationFont(mono_path)
        if mono_font_id != -1:
            mono_font = QFontDatabase.applicationFontFamilies(mono_font_id)[0]
            QFont(mono_font).setStyleHint(QFont.StyleHint.Monospace)

        # Add Material Symbols Outlined for icon theme
        icon_path = path.join(res_dir, "MaterialSymbolsOutlined.ttf")
        icon_font_id = QFontDatabase.addApplicationFont(icon_path)
        if icon_font_id != -1:
            icon_font = QFontDatabase.applicationFontFamilies(icon_font_id)[0]
            QIcon.setThemeName(icon_font)

        # Window setup
        self.setWindowTitle("JobTools")
        self.resize(1280, 720)

        # Main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setCentralWidget(main_widget)

        # Splitter between pages and log panel
        self.log_splitter = QSplitter(Qt.Orientation.Vertical)

        # Pages Area
        self.pages = QStackedWidget()

        # Log Panel
        self.log_panel = LogPanel(self.log_splitter)
        self.log_panel.hide()

        # Assemble Splitter (Pages/Log)
        self.log_splitter.addWidget(self.pages)
        self.log_splitter.addWidget(self.log_panel)

        # Sidebar Navigation
        self.nav_panel = NavPanel(self.pages)

        # Assemble Main Layout (Sidebar|Splitter)
        self.log_splitter.setCollapsible(0, False)
        main_layout.addWidget(self.nav_panel)
        self.log_splitter.setStretchFactor(0, 1)
        main_layout.addWidget(self.log_splitter)
        self.log_splitter.setStretchFactor(1, 0)

        # Apply stylesheet
        app = QApplication.instance()
        theme_path = path.join(res_dir, f"theme_{get_sys_theme()}.xml")
        qss_path = path.join(res_dir, "custom.qss")
        apply_stylesheet(app, theme=theme_path, css_file=qss_path)

        # Populate Pages
        self.add_page("collect", CollectorPage(), "search")
        self.add_page("filter", FilterPage(), "filter_alt")
        self.add_page("sort", SortPage(), "sort", icon_size=40)
        self.add_page("settings", SettingsPage(), "settings", align_bottom=True)

        # Select first page by default
        if self.nav_panel.btn_group.buttons():
            self.nav_panel.btn_group.buttons()[0].click()

    def add_page(self,
                 page_name: str,
                 widget: QWidget,
                 icon_name: str,
                 icon_size: int = 32,
                 align_bottom: bool = False):
        """ Add a new page to the application with navigation button.

        Parameters
        ----------
        page_name : str
            Name identifier for the page.
        widget : QWidget
            The page widget to display.
        icon_name : str
            Name of the material icon for the navigation button.
        icon_size : int, optional
            Size of the icon in pixels. Default is 32.
        align_bottom : bool, optional
            Whether to align the button at the bottom of the sidebar.
        """
        # Create navigation button
        btn = QPushButton()
        btn.setCheckable(True)
        btn.setIcon(get_icon(icon_name))
        btn.setIconSize(QSize(icon_size, icon_size))
        btn.setToolTip(page_name.capitalize())
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("class", "nav-button")
        # Add button to appropriate sidebar section
        if align_bottom:
            self.nav_panel.bottom.addWidget(btn)
        else:
            self.nav_panel.top.addWidget(btn)
        # Add button to group
        self.nav_panel.btn_group.addButton(btn)
        # Add page to stacked widget
        scrollable = QScrollArea()
        scrollable.setWidgetResizable(True)
        scrollable.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scrollable.setWidget(widget)
        index = self.pages.addWidget(scrollable)
        btn.setProperty("page_index", index)


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


class LogPanel(QWidget):
    """ Bottom log panel for displaying console output. """

    def __init__(self, splitter: QSplitter):
        """ Setup the log panel UI components. """
        super().__init__()
        self._splitter = splitter

        # Layout Setup
        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)    # type: ignore
        self.layout().setSpacing(0)                     # type: ignore

        # Logger Setup
        log_handler = QtLogHandler()
        logger = JTLogger()
        logger.addHandler(log_handler)
        log_handler.log_signal.connect(self._on_console_output)

        # Header
        header = QFrame()
        header.setFixedHeight(30)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 5, 0)

        # Header Title
        title = QLabel("CONSOLE")

        # Close Button
        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close"))
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setFixedSize(24, 24)
        close_btn.setFlat(True)
        close_btn.clicked.connect(self.hide)

        # Assemble Header (Title|<->|Close)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)

        # Log Text Area
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Assemble Log Panel
        self.layout().addWidget(header)                 # type: ignore
        self.layout().addWidget(self.log_output)        # type: ignore

    @Slot()
    def _on_console_output(self, text):
        """ Handle text coming from logger. """
        if self.isHidden() and text.strip():
            # Show log panel if hidden
            self.show()
            sizes = self._splitter.sizes()
            if sizes[1] == 0:
                # Adjust splitter to allocate space for log panel
                total = sum(sizes)
                self._splitter.setSizes([int(total * 0.7), int(total * 0.3)])
        # Append text to log output
        self.log_output.append(text)
        sb = self.log_output.verticalScrollBar()
        sb.setValue(sb.maximum())


class NavPanel(QFrame):
    """ Sidebar navigation panel for switching between pages. """
    
    def __init__(self, pages: QStackedWidget):
        """ Setup the sidebar navigation panel. """
        super().__init__()
        self._pages = pages

        # Sidebar Setup
        self.setFixedWidth(60)
        self.setProperty("class", "sidebar")
        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(0, 10, 0, 10)  # type: ignore
        self.layout().setSpacing(0)                     # type: ignore

        # Top Section
        self.top = QVBoxLayout()
        self.top.setSpacing(10)
        self.top.setContentsMargins(0,0,0,0)

        # Bottom Section
        self.bottom = QVBoxLayout()
        self.bottom.setSpacing(10)
        self.bottom.setContentsMargins(0,0,0,0)

        # Assemble Sidebar (Top/<->/Bottom)
        self.layout().addLayout(self.top)               # type: ignore
        self.layout().addStretch()                      # type: ignore
        self.layout().addLayout(self.bottom)            # type: ignore

        # Navigation Button Group
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self.btn_group.buttonClicked.connect(self._on_nav_button_clicked)
    
    @Slot()
    def _on_nav_button_clicked(self, btn):
        """ Handle navigation button clicks. """
        index = btn.property("page_index")
        if index is not None:
            self._pages.setCurrentIndex(index)
