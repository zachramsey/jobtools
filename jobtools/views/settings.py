from PySide6.QtCore import QModelIndex, QSize, Qt, QUrl, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from ..models import ConfigModel, JobsDataModel
from ..utils import get_config_dir, get_data_dir, get_icon
from .widgets import QHeader

LC_TT = """Load a saved configuration from file.
Select a configuration from the dropdown and click 'Load' to apply it to the application."""

SC_TT = """Save the current configuration to file.
Enter a name for the configuration and click 'Save' to store it for future use."""

P_TT = """Optional proxy server for web requests.

Highly recommended!

The job collector makes many requests in a short
period, which may trigger anti-bot protections on
job sites. Using a proxy will distribute these
requests and help avoid IP blocking."""


class SettingsPage(QWidget):
    def __init__(self, config_model: ConfigModel, data_model: JobsDataModel):
        super().__init__()
        self._cfg_model = config_model
        self._data_model = data_model
        defaults: dict = {}

        self.setLayout(QVBoxLayout(self))
        self.layout().setSpacing(20)

        # Open directories
        dir_layout = QHBoxLayout()
        dir_header = QHeader("Open Directory")
        dir_header.setFixedWidth(250)
        dir_layout.addWidget(dir_header)
        self.config_dir_btn = QPushButton("Configs")
        self.config_dir_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.config_dir_btn.clicked.connect(lambda: self._on_open_dir(str(get_config_dir())))
        dir_layout.addWidget(self.config_dir_btn)
        self.data_dir_btn = QPushButton("Data")
        self.data_dir_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.data_dir_btn.clicked.connect(lambda: self._on_open_dir(str(get_data_dir())))
        dir_layout.addWidget(self.data_dir_btn)
        dir_layout.addStretch()
        self.layout().addLayout(dir_layout)

        # Load configuration
        load_layout = QHBoxLayout()
        load_header = QHeader("Load Configuration", tooltip=LC_TT)
        load_header.setFixedWidth(250)
        load_layout.addWidget(load_header)
        self.config_select = QComboBox()
        self.config_select.setFixedWidth(300)
        self.config_select.addItems([""]+self._cfg_model.get_saved_config_names())
        load_layout.addWidget(self.config_select)
        self.config_load = QPushButton("Load")
        self.config_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.config_load.clicked.connect(self._on_load_config)
        load_layout.addWidget(self.config_load)
        self.config_refresh = QPushButton()
        self.config_refresh.setIcon(get_icon("refresh"))
        self.config_refresh.setIconSize(QSize(24, 24))
        self.config_refresh.setStyleSheet("border: none; padding: 5px;")
        self.config_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.config_refresh.setToolTip("Refresh Data Sources")
        self.config_refresh.clicked.connect(self._on_refresh_configs)
        load_layout.addWidget(self.config_refresh)
        load_layout.addStretch()
        self.layout().addLayout(load_layout)

        # Save configuration
        save_layout = QHBoxLayout()
        save_header = QHeader("Save Configuration", tooltip=SC_TT)
        save_header.setFixedWidth(250)
        save_layout.addWidget(save_header)
        self.config_edit = QLineEdit(placeholderText="Configuration name...")
        self.config_edit.setFixedWidth(300)
        save_layout.addWidget(self.config_edit)
        self.config_save = QPushButton("Save")
        self.config_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.config_save.clicked.connect(self._on_save_config)
        save_layout.addWidget(self.config_save)
        save_layout.addStretch()
        self.layout().addLayout(save_layout)

        # Proxy editor
        proxy_layout = QHBoxLayout()
        proxy_header = QHeader("Proxy Server", tooltip=P_TT)
        proxy_header.setFixedWidth(250)
        proxy_layout.addWidget(proxy_header)
        self.p_editor = QLineEdit(placeholderText="user:pass@host:port")
        self.p_editor.setFixedWidth(800)
        proxy_layout.addWidget(self.p_editor)
        proxy_layout.addStretch()
        self.layout().addLayout(proxy_layout)
        defaults["proxy"] = ""

        # Push content to top
        self.layout().addStretch()

        # Register page with config model
        self._cfg_model.register_page("settings", defaults)

        # Connect view to config model
        self.p_editor.textChanged.connect(
            lambda t: self._update_config("proxy", t))

        # Connect config model to view updates
        self._cfg_model.dataChanged.connect(self._on_config_changed)

    def layout(self) -> QVBoxLayout:
        """Override layout to remove type-checking errors."""
        return super().layout() # type: ignore

    def _update_config(self, key: str, value):
        """Update model data from view changes."""
        if key in self._cfg_model.idcs:
            self._cfg_model.setData(self._cfg_model.idcs[key], value, Qt.ItemDataRole.EditRole)

    @Slot(QModelIndex, QModelIndex)
    def _on_config_changed(self, top_left: QModelIndex, bottom_right: QModelIndex):
        """Update view when model data changes."""
        # Proxy
        val = self._cfg_model.get_value("proxy", top_left)
        if val is not None and val != self.p_editor.text().strip():
            self.p_editor.setText(val)

    @Slot(str)
    def _on_open_dir(self, directory: str):
        """Open the specified directory in the system file explorer."""
        url = QUrl.fromLocalFile(directory)
        if not QDesktopServices.openUrl(url):
            self._data_model.logger.error(f"Failed to open directory: {directory}")

    @Slot(str)
    def _on_load_config(self):
        """Load configuration from file."""
        config_name = self.config_select.currentText().strip()
        if not config_name:
            return
        config_name = config_name.replace(" ", "_").lower()
        config_path = get_config_dir() / f"{config_name}.json"
        # Temporarily disconnect to avoid triggering updates
        self._cfg_model.dataChanged.disconnect(self._data_model._on_config_changed)
        # Load config and update data model
        self._cfg_model.load_from_file(config_path)
        self._data_model.init_config()
        # Reconnect signal
        self._cfg_model.dataChanged.connect(self._data_model._on_config_changed)
        # Update config edit box
        self.config_edit.setText(config_name)

    @Slot()
    def _on_refresh_configs(self):
        """Refresh the list of saved configurations."""
        temp = self.config_select.currentText()
        self.config_select.clear()
        self.config_select.addItems([""]+self._cfg_model.get_saved_config_names())
        self.config_select.setCurrentText(temp)

    @Slot()
    def _on_save_config(self):
        """Save current configuration to file."""
        config_name = self.config_edit.text().strip()
        if not config_name:
            return
        config_name = config_name.replace(" ", "_").lower()
        config_path = get_config_dir() / f"{config_name}.json"
        self._cfg_model.save_to_file(config_path)
        # Update config selector
        temp = self.config_select.currentText()
        self.config_select.clear()
        self.config_select.addItems([""]+self._cfg_model.get_saved_config_names())
        self.config_select.setCurrentText(temp)
