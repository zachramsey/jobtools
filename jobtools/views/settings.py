from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox
from PySide6.QtCore import Qt, QModelIndex, Slot, QSize
from .widgets import QHeader
from ..models import ConfigModel
from ..utils import get_config_dir, get_icon


LC_TT = """Load a saved configuration from file.
Select a configuration from the dropdown and click 'Load' to apply it to the application."""

SC_TT = """Save the current configuration to file.
Enter a name for the configuration and click 'Save' to store it for future use."""


class SettingsPage(QWidget):
    """ """

    def __init__(self, config_model: ConfigModel):
        super().__init__()
        self._config_model = config_model
        self.setLayout(QVBoxLayout(self))

        # Load configuration
        self.layout().addWidget(QHeader("Load Configuration", tooltip=LC_TT))
        load_layout = QHBoxLayout()
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
        self.layout().addWidget(QHeader("Save Configuration", tooltip=SC_TT))
        save_layout = QHBoxLayout()
        self.config_edit = QLineEdit(placeholderText="Configuration name...")
        self.config_edit.setFixedWidth(300)
        save_layout.addWidget(self.config_edit)
        self.config_save = QPushButton("Save")
        self.config_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.config_save.clicked.connect(self._on_save_config)
        save_layout.addWidget(self.config_save)
        save_layout.addStretch()
        self.layout().addLayout(save_layout)

        # Push run button to bottom
        self.layout().addStretch()

    def layout(self) -> QVBoxLayout:
        """ Override layout to remove type-checking errors. """
        return super().layout() # type: ignore

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
