import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox
from PySide6.QtCore import Qt, QModelIndex, QObject, Signal, Slot, QThread, QUrl
from PySide6.QtGui import QDesktopServices
import traceback
from .custom_widgets import QHeader
from .model import ConfigModel
from .utils import get_config_dir
from ..utils.logger import JDLogger


SC_TT = """"""

LC_TT = """"""


class CollectionWorker(QObject):
    """ Worker for running job data collection in a separate thread. """

    finished = Signal(str)
    error = Signal(str)

    def __init__(self, config: dict):
        super().__init__()
        self._config = config

    @Slot()
    def run(self):
        """ Run the job data collection process. """
        try:
            jobs = ConfigModel().run_collection(self._config)
            jobs = ConfigModel.run_filter(self._config, jobs)
            html_path = ConfigModel.run_export(self._config, jobs)
            self.finished.emit(html_path)
        except Exception:
            self.error.emit(traceback.format_exc())


class RunnerPage(QWidget):
    """ Page for running JobTools operations. """

    def __init__(self, model: ConfigModel):
        super().__init__()
        self._model = model
        self._config_dir = get_config_dir()
        self.worker_thread = None
        self.setLayout(QVBoxLayout(self))

        # Current configuration name and save
        self.layout().addWidget(QHeader("Save Configuration", tooltip=SC_TT))
        save_layout = QHBoxLayout()
        self.config_name = QLineEdit(placeholderText="Configuration name...")
        self.config_name.setFixedWidth(300)
        save_layout.addWidget(self.config_name)
        self.config_save = QPushButton("Save")
        self.config_save.setCursor(Qt.CursorShape.PointingHandCursor)
        save_layout.addWidget(self.config_save)
        save_layout.addStretch()
        self.layout().addLayout(save_layout)
        self.config_save.clicked.connect(self._on_save_config)

        # Configuration file selector
        self.layout().addWidget(QHeader("Load Configuration", tooltip=LC_TT))
        self.config_load = QComboBox()
        self.config_load.setFixedWidth(300)
        self.config_load.addItems([""]+self._model.get_saved_config_names())
        self.layout().addWidget(self.config_load)
        self.config_load.currentTextChanged.connect(self._on_load_config)

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

    def _on_save_config(self):
        """ Save current configuration to file. """
        config_name = self.config_name.text().strip()
        if not config_name:
            return
        config_name = config_name.replace(" ", "_").lower()
        config_path = os.path.join(self._config_dir, f"{config_name}.json")
        self._model.save_to_file(config_path)
        # Update config load selector
        self.config_load.clear()
        self.config_load.addItems([""]+self._model.get_saved_config_names())

    def _on_load_config(self, config_name: str):
        """ Load configuration from file. """
        config_name = config_name.strip()
        if not config_name:
            return
        config_name = config_name.replace(" ", "_").lower()
        config_path = os.path.join(self._config_dir, f"{config_name}.json")
        self.config_name.setText(config_name)
        self._model.load_from_file(config_path)
        self._model.dataChanged.emit(QModelIndex(), QModelIndex())

    def _on_run_collect(self):
        """ Trigger job data collection. """
        # Update UI
        self.run.setText("Cancel")
        self.run.setProperty("class", "danger")
        # Get current configuration
        config = self._model.get_config_dict()
        # Set up worker and thread
        self.worker_thread = QThread()
        self.worker = CollectionWorker(config)
        self.worker.moveToThread(self.worker_thread)
        # Connect signals
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker.finished.connect(self._on_collection_finished)
        self.worker.error.connect(self._on_collection_error)
        # Start thread
        self.worker_thread.start()

    # TODO: Doesn't work
    def _on_run_cancel(self):
        """ Handle run cancellation. """
        self.run.setText("Collect Jobs")
        self.run.setProperty("class", "")
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.requestInterruption()
            self.worker_thread.quit()

    @Slot()
    def _on_run_clicked(self):
        """ Handle run button click. """
        # if self.run.text() == "Collect Jobs":
        self._on_run_collect()
        # else:
        #     self._on_run_cancel()

    @Slot(str)
    def _on_collection_finished(self, html_path: str):
        """ Handle completion of job data collection. """
        self.run.setText("Collect Jobs")
        self.run.setProperty("class", "")
        # Open the generated HTML file
        if html_path and os.path.isfile(html_path):
            abs_path = os.path.abspath(html_path)
            url = QUrl.fromLocalFile(abs_path)
            if not QDesktopServices.openUrl(url):
                JDLogger().error(f"Failed to open the HTML file: {abs_path}")
        else:
            JDLogger().warning("No HTML file was generated.")

    @Slot(str)
    def _on_collection_error(self, error_msg: str):
        """ Handle errors during job data collection. """
        self.run.setEnabled(True)
        self.run.setText("Collect Jobs")
        raise RuntimeError(f"Job data collection failed: {error_msg}")
