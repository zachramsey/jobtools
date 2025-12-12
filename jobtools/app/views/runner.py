import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox
from PySide6.QtCore import Qt, QModelIndex, Slot
from ..custom_widgets import QHeader
from ..models.config_model import ConfigModel
from ..models.data_model import DataModel
from ..models.data_worker import collect_jobs
from ..utils import get_config_dir


SC_TT = """"""

LC_TT = """"""


class RunnerPage(QWidget):
    """ Page for running JobTools operations. """

    _data_model: DataModel
    """ Controller for job data operations. """

    def __init__(self, config_model: ConfigModel):
        super().__init__()
        self._config_model = config_model
        self._config_dir = get_config_dir()
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

        # Run data collection
        self.run = QPushButton("Collect Jobs")
        self.layout().addWidget(self.run)
        self.run.clicked.connect(self._on_run_clicked)
        self.run.setFixedWidth(200)
        self.run.setStyleSheet("margin-bottom: 20px;")
        self.run.setCursor(Qt.CursorShape.PointingHandCursor)

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
        config_path = os.path.join(self._config_dir, f"{config_name}.json")
        self._config_model.load_from_file(config_path)
        self._config_model.dataChanged.emit(QModelIndex(), QModelIndex())
        # Update config edit box
        self.config_edit.setText(config_name)

    @Slot()
    def _on_save_config(self):
        """ Save current configuration to file. """
        config_name = self.config_edit.text().strip()
        if not config_name:
            return
        config_name = config_name.replace(" ", "_").lower()
        config_path = os.path.join(self._config_dir, f"{config_name}.json")
        self._config_model.save_to_file(config_path)
        # Update config selector
        temp = self.config_select.currentText()
        self.config_select.clear()
        self.config_select.addItems([""]+self._config_model.get_saved_config_names())
        self.config_select.setCurrentText(temp)

    @Slot()
    def _on_run_clicked(self):
        """ Handle run button click. """
        if self.run.text() == "Collect Jobs":
            # Update UI
            self.run.setText("Cancel")
            self.run.setProperty("class", "danger")
            self.run.style().unpolish(self.run)
            self.run.style().polish(self.run)
            # Setup data collection worker
            self._cancel_event = collect_jobs(self._config_model.get_config_dict(),
                                              self._on_collection_finished,
                                              self._on_collection_error)
        else:
            # Signal cancellation
            if self._cancel_event:
                self._cancel_event.set()
            self.run.setText("Canceling...")
            self.run.setEnabled(False)

    @Slot(str)
    def _on_collection_finished(self, csv_path: str):
        """ Handle completion of job data collection. """
        self.run.setText("Collect Jobs")
        self.run.setProperty("class", "")
        self.run.style().unpolish(self.run)
        self.run.style().polish(self.run)
        self.run.setEnabled(True)
        self._cancel_event = None

    @Slot(str)
    def _on_collection_error(self, error_msg: str):
        """ Handle errors during job data collection. """
        self.run.setEnabled(True)
        self.run.setText("Collect Jobs")
        raise RuntimeError(f"Job data collection failed: {error_msg}")
