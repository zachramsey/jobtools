import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QComboBox
from PySide6.QtCore import Qt, QModelIndex, Slot, QObject, Signal, QThread, QSize
from threading import Event
import traceback
from .widgets import QHeader
from ..models import ConfigModel, JobsDataModel
from ..utils import get_config_dir, get_icon


SC_TT = """"""

LC_TT = """"""


class CollectionWorker(QObject):
    """ Worker for running job data collection in a separate thread. """

    finished = Signal(str)
    error = Signal(str)

    def __init__(self, data_model: JobsDataModel, config: dict, cancel_event: Event):
        super().__init__()
        self._data_model = data_model
        self._config = config.get("collect", {})
        self._cancel_event = cancel_event

    @Slot()
    def run(self):
        """ Run the job data collection process.

        Yields
        ------
        finished : str
            Emitted with the path to the generated CSV file upon completion.
        error : str
            Emitted with the error message if an exception occurs.
        """
        try:
            # Initialize JobsData
            source = self._config.get("data_source", "")
            if source:
                self._data_model.load_data(source)
            self._data_model.logger.info("Starting job collection...")
            # Run collection and sorting for each query
            for query in self._config.get("queries", []):
                # Job collection
                _ = self._data_model.collect(
                    site_name=self._config.get("sites_selected", []),
                    search_term=query,
                    job_type=None,  # type: ignore
                    locations=self._config.get("locations_selected", []),
                    results_wanted=10000, # TODO: Make arbitrarily large "maximum" value configurable
                    proxy=self._config.get("proxy", ""),
                    hours_old=self._config.get("hours_old", 0),
                    cancel_event=self._cancel_event
                )
                # Check for cancellation
                if self._cancel_event and self._cancel_event.is_set():
                    self._data_model.logger.info("Job collection cancelled by user.")
                    break
                # Save intermediate CSV
                csv_path = self._data_model.export_csv()
            # Add final data to archive
            self._data_model.update_archive()
            # Emit finished signal
            if self._cancel_event and self._cancel_event.is_set():
                self.finished.emit("")
            else:
                self.finished.emit(str(csv_path))
        except Exception:
            self.error.emit(traceback.format_exc())


class RunnerPage(QWidget):
    """ Page for running JobTools operations. """

    def __init__(self, config_model: ConfigModel, data_model: JobsDataModel):
        super().__init__()
        self._config_model = config_model
        self._data_model = data_model
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

        # Run data collection
        self.run_btn = QPushButton("Collect Jobs")
        self.layout().addWidget(self.run_btn)
        self.run_btn.clicked.connect(self._on_run_clicked)
        self.run_btn.setFixedWidth(200)
        self.run_btn.setStyleSheet("margin-bottom: 20px;")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)

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
        config_path = os.path.join(get_config_dir(), f"{config_name}.json")
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
        config_path = os.path.join(get_config_dir(), f"{config_name}.json")
        self._config_model.save_to_file(config_path)
        # Update config selector
        temp = self.config_select.currentText()
        self.config_select.clear()
        self.config_select.addItems([""]+self._config_model.get_saved_config_names())
        self.config_select.setCurrentText(temp)

    @Slot()
    def _on_run_clicked(self):
        """ Handle run button click. """
        if self.run_btn.text() == "Collect Jobs":
            # Update UI
            self.run_btn.setText("Cancel")
            self.run_btn.setProperty("class", "danger")
            self.run_btn.style().unpolish(self.run_btn)
            self.run_btn.style().polish(self.run_btn)
            # Setup data collection worker
            self._cancel_event = Event()
            self.worker = CollectionWorker(self._data_model,
                                      self._config_model.get_config_dict(),
                                      self._cancel_event)
            self.worker_thread = QThread()
            self.worker.moveToThread(self.worker_thread)
            # Connect signals and slots
            self.worker_thread.started.connect(self.worker.run)
            self.worker_thread.finished.connect(self.worker_thread.deleteLater)
            self.worker.finished.connect(self.worker_thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            # Connect worker signals to callbacks
            self.worker.finished.connect(self._on_collection_finished)
            self.worker.error.connect(self._on_collection_error)
            # Start thread
            self.worker_thread.start()
        else:
            # Signal cancellation
            if self._cancel_event:
                self._cancel_event.set()
            self.run_btn.setText("Canceling...")
            self.run_btn.setEnabled(False)

    @Slot(str)
    def _on_collection_finished(self, csv_path: str):
        """ Handle completion of job data collection. """
        self.run_btn.setText("Collect Jobs")
        self.run_btn.setProperty("class", "")
        self.run_btn.style().unpolish(self.run_btn)
        self.run_btn.style().polish(self.run_btn)
        self.run_btn.setEnabled(True)
        self._cancel_event = None

    @Slot(str)
    def _on_collection_error(self, error_msg: str):
        """ Handle errors during job data collection. """
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Collect Jobs")
        raise RuntimeError(f"Job data collection failed: {error_msg}")
