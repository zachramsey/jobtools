import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QStackedWidget, QPushButton,
                               QFrame, QButtonGroup, QScrollArea)
from PySide6.QtCore import Qt, QSize, Slot
from PySide6.QtGui import QGuiApplication, QIcon, QFont, QFontDatabase
from qt_material import apply_stylesheet    # type: ignore
from .model import ConfigModel
from .runner import RunnerPage
from .collect import CollectPage
from .filter import FilterPage
from .sort import SortPage
from .console import ConsolePanel
from .settings import SettingsPage
from .utils import get_icon, get_sys_theme


class JobToolsApp(QMainWindow):
    """ Main application window for JobTools. """

    def __init__(self):
        super().__init__()
        # Setup resources
        res_dir = os.path.join(os.path.dirname(__file__), "resources")
        
        # Add Roboto for default application font
        sans_path = os.path.join(res_dir, "Roboto.ttf")
        sans_font_id = QFontDatabase.addApplicationFont(sans_path)
        if sans_font_id != -1:
            sans_font = QFontDatabase.applicationFontFamilies(sans_font_id)[0]
            QGuiApplication.setFont(sans_font)

        # Add Roboto Mono for monospace font
        mono_path = os.path.join(res_dir, "RobotoMono.ttf")
        mono_font_id = QFontDatabase.addApplicationFont(mono_path)
        if mono_font_id != -1:
            mono_font = QFontDatabase.applicationFontFamilies(mono_font_id)[0]
            QFont(mono_font).setStyleHint(QFont.StyleHint.Monospace)

        # Add Material Symbols Outlined for icon theme
        icon_path = os.path.join(res_dir, "MaterialSymbolsOutlined.ttf")
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

        # Pages Area
        self.pages = QStackedWidget()

        # Sidebar Navigation
        self.nav_panel = NavPanel(self.pages)

        # Assemble Main Layout (Sidebar|Pages)
        main_layout.addWidget(self.nav_panel)
        main_layout.addWidget(self.pages)

        # Apply stylesheet
        app = QApplication.instance()
        theme_path = os.path.join(res_dir, f"theme_{get_sys_theme()}.xml")
        qss_path = os.path.join(res_dir, "custom.qss")
        light_extra = {'danger': '#DB3E03', 'warning': '#977100', 'success': '#008679'}
        dark_extra = {'danger': '#FF8B69', 'warning': '#D8A300', 'success': '#48BDAE'}
        extra = dark_extra if get_sys_theme() == "dark" else light_extra
        apply_stylesheet(app, theme=theme_path, css_file=qss_path, extra=extra)

        # Initialize the config model
        cfg_model = ConfigModel()

        # Populate Pages
        self.add_page(RunnerPage(cfg_model), "runner", "play_arrow", icon_size=36)
        self.add_page(CollectPage(cfg_model), "collect", "search")
        self.add_page(FilterPage(cfg_model), "filter", "filter_alt")
        self.add_page(SortPage(cfg_model), "sort", "sort", icon_size=40)
        self.add_page(ConsolePanel(), "console", "terminal", icon_size=40, align_bottom=True)
        self.add_page(SettingsPage(), "settings", "settings", align_bottom=True)

        # Select first page by default
        if self.nav_panel.btn_group.buttons():
            self.nav_panel.btn_group.buttons()[0].click()

    def add_page(self,
                 widget: QWidget,
                 page_name: str,
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
