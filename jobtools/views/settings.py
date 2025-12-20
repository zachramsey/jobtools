from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox
from PySide6.QtCore import Qt, QModelIndex, Slot, QSize
from .widgets import QHeader
from ..models import ConfigModel, JobsDataModel
from ..utils import get_config_dir, get_icon


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
    """ """

    def __init__(self, config_model: ConfigModel, data_model: JobsDataModel):
        super().__init__()
        self._config_model = config_model
        self._data_model = data_model
        self._idcs: dict[str, QModelIndex] = {}
        self.defaults: dict = {}
        self.setLayout(QVBoxLayout(self))
        self.layout().setSpacing(20)

        # Load configuration
        load_layout = QHBoxLayout()
        load_header = QHeader("Load Configuration", tooltip=LC_TT)
        load_header.setFixedWidth(250)
        load_layout.addWidget(load_header)
        self.config_select = QComboBox()
        self.config_select.setFixedWidth(300)
        self.config_select.addItems([""]+self._config_model.get_saved_config_names())
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
        self.defaults["proxy"] = ""

        # Push content to top
        self.layout().addStretch()

        # Register page with config model
        root_index = self._config_model.register_page("settings", self.defaults)

        # Map keys to config model indices
        for row in range(self._config_model.rowCount(root_index)):
            idx = self._config_model.index(row, 0, root_index)
            key = self._config_model.data(idx, Qt.ItemDataRole.DisplayRole)
            val_idx = self._config_model.index(row, 1, root_index)
            self._idcs[key] = val_idx

        # Connect view to config model
        self.p_editor.textChanged.connect(
            lambda t: self._update_config("proxy", t))
        
        # Connect config model to view updates
        self._config_model.dataChanged.connect(self._on_config_changed)

    def layout(self) -> QVBoxLayout:
        """ Override layout to remove type-checking errors. """
        return super().layout() # type: ignore
    
    def _update_config(self, key: str, value):
        """ Update model data from view changes. """
        if key in self._idcs:
            self._config_model.setData(self._idcs[key], value, Qt.ItemDataRole.EditRole)
    
    def __get_value(self, key: str, top_left: QModelIndex):
        """ Get value from model for a specific key. """
        idx = self._idcs.get(key)
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._config_model.data(idx, Qt.ItemDataRole.DisplayRole)
            if val is None:
                val = self.defaults[key]
            return val
        return None

    @Slot(QModelIndex, QModelIndex)
    def _on_config_changed(self, top_left: QModelIndex, bottom_right: QModelIndex):
        """ Update view when model data changes. """
        # Proxy
        val = self.__get_value("proxy", top_left)
        if val is not None and val != self.p_editor.text().strip():
            self.p_editor.setText(val)

    @Slot(str)
    def _on_load_config(self):
        """ Load configuration from file. """
        config_name = self.config_select.currentText().strip()
        if not config_name:
            return
        config_name = config_name.replace(" ", "_").lower()
        config_path = get_config_dir() / f"{config_name}.json"
        self._config_model.load_from_file(config_path)
        self._config_model.dataChanged.emit(QModelIndex(), QModelIndex())
        # Update config edit box
        self.config_edit.setText(config_name)

    @Slot()
    def _on_refresh_configs(self):
        """ Refresh the list of saved configurations. """
        temp = self.config_select.currentText()
        self.config_select.clear()
        self.config_select.addItems([""]+self._config_model.get_saved_config_names())
        self.config_select.setCurrentText(temp)

    @Slot()
    def _on_save_config(self):
        """ Save current configuration to file. """
        config_name = self.config_edit.text().strip()
        if not config_name:
            return
        config_name = config_name.replace(" ", "_").lower()
        config_path = get_config_dir() / f"{config_name}.json"
        self._config_model.save_to_file(config_path)
        # Update config selector
        temp = self.config_select.currentText()
        self.config_select.clear()
        self.config_select.addItems([""]+self._config_model.get_saved_config_names())
        self.config_select.setCurrentText(temp)
