import traceback
from threading import Event

from PySide6.QtCore import QModelIndex, QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QRadioButton, QSpinBox, QVBoxLayout, QWidget

from ..models import ConfigModel, JobsDataModel
from .widgets import QChipSelect, QHeader, QPlainTextListEdit

DS_TT = """Select the source of job data to load.

None - starts a fresh collection.
Archive - loads previously collected data.
Latest - fetches the most recent data available.
Manual - allows specifying a custom subdirectory path."""

S_TT = """Select which job sites to collect data from.

Note that the total number of queries will increase
proportionally with the number of sites selected."""

L_TT = """Select locations to search for jobs in.

Note that the total number of queries will increase
proportionally with the number of locations specified.

Accepts cities, states/provinces, countries,
and combinations thereof."""

Q_TT = """List of search strings to use when collecting job data.

Note that the total number of queries will increase
proportionally with the number of search strings specified.

Boolean operators (AND, OR, NOT), quotation marks for
exact phrases, and parentheses for grouping are supported.

Example: "software engineer" AND (python OR java) NOT intern"""


class CollectionWorker(QObject):
    """Worker for running job data collection in a separate thread."""

    finished = Signal(str)
    error = Signal(str)

    def __init__(self, data_model: JobsDataModel, config: dict, cancel_event: Event):
        super().__init__()
        self._data_model = data_model
        self._config: dict = config.get("collect", {})
        self._config.update(config.get("settings", {}))
        print(self._config)
        self._cancel_event = cancel_event

    @Slot()
    def run(self):
        """Run the job data collection process.

        Yields
        ------
        finished : str
            Emitted with the path to the generated CSV file upon completion.
        error : str
            Emitted with the error message if an exception occurs.
        """
        try:
            # Signal that collection has started
            self._data_model.collectStarted.emit()
            # Initialize JobsData
            source = self._config.get("data_source", "")
            if source:
                self._data_model.load_data(source)
            self._data_model.logger.info("Starting job collection...")
            # Run collection and sorting for each query
            for query in self._config.get("queries", []):
                # Job collection
                self._data_model.collect(
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
                self._data_model.collectFinished.emit(str(csv_path))
        except Exception:
            self.error.emit(traceback.format_exc())


class DataSourceSelector(QWidget):
    """Widget for selecting data source."""

    sourceChanged = Signal(str)
    """ Signal emitted when the data source selection changes. """

    def __init__(self):
        super().__init__()
        self.setLayout(QHBoxLayout(self))
        # Radio buttons for data source selection
        self.radio_none = QRadioButton("None")
        self.layout().addWidget(self.radio_none)
        self.radio_none.setChecked(True)
        self.radio_archive = QRadioButton("Archive")
        self.layout().addWidget(self.radio_archive)
        self.radio_latest = QRadioButton("Latest")
        self.layout().addWidget(self.radio_latest)
        self.radio_manual = QRadioButton("Manual")
        # Set widths to the maximum of the radio buttons
        radio_buttons = [self.radio_none, self.radio_archive,
                         self.radio_latest, self.radio_manual]
        max_width = max([btn.sizeHint().width() for btn in radio_buttons])
        for btn in radio_buttons:
            btn.setFixedWidth(max_width + 10)
        # Manual path input
        self.path_input = QLineEdit()
        self.path_input.setFixedWidth(200)
        self.path_input.setPlaceholderText("Subdirectory path...")
        self.path_input.setEnabled(False)
        self.radio_manual.toggled.connect(self.path_input.setEnabled)
        # Assemble radio layout
        self.layout().addWidget(self.radio_manual)
        self.layout().addWidget(self.path_input)
        self.layout().addStretch()
        # Connect signals
        for btn in radio_buttons:
            btn.toggled.connect(self._on_change)
        self.path_input.textChanged.connect(self._on_change)

    @Slot()
    def _on_change(self):
        """Emit current source when selection changes."""
        self.sourceChanged.emit(self.get_source())

    def get_source(self) -> str:
        """Get data source selection."""
        if self.radio_none.isChecked():
            return ""
        elif self.radio_archive.isChecked():
            return "archive"
        elif self.radio_latest.isChecked():
            return "latest"
        elif self.radio_manual.isChecked():
            return self.path_input.text().strip()
        else:
            return ""

    def set_source(self, source: str):
        """Set data source selection."""
        # Prevent signal emission during update
        self.blockSignals(True)
        if source == "":
            self.radio_none.setChecked(True)
        elif source == "archive":
            self.radio_archive.setChecked(True)
        elif source == "latest":
            self.radio_latest.setChecked(True)
        else:
            self.radio_manual.setChecked(True)
            self.path_input.setText(source)
        self.blockSignals(False)


class CollectPage(QWidget):
    def __init__(self, config_model: ConfigModel, data_model: JobsDataModel):
        super().__init__()
        self._config_model = config_model
        self._data_model = data_model
        self._idcs: dict[str, QModelIndex] = {}
        self.defaults: dict = {}
        self.setLayout(QVBoxLayout(self))
        self.layout().setSpacing(20)

        # Data source selection
        ds_layout = QHBoxLayout()
        ds_header = QHeader("Data Source", tooltip=DS_TT)
        ds_header.setFixedWidth(200)
        ds_layout.addWidget(ds_header)
        self.ds_selector = DataSourceSelector()
        ds_layout.addWidget(self.ds_selector, 1)
        self.layout().addLayout(ds_layout)
        self.defaults["data_source"] = ""

        # Site selection
        s_layout = QHBoxLayout()
        s_header = QHeader("Job Sites", tooltip=S_TT)
        s_header.setFixedWidth(200)
        s_layout.addWidget(s_header)
        available = ["LinkedIn", "Indeed"]
        self.s_selector = QChipSelect(base_items=available, enable_creator=False)
        s_layout.addWidget(self.s_selector, 1)
        self.layout().addLayout(s_layout)
        self.defaults["sites_selected"] = []
        self.defaults["sites_available"] = available

        # Locations editor
        l_layout = QHBoxLayout()
        l_header = QHeader("Locations", tooltip=L_TT)
        l_header.setFixedWidth(200)
        l_layout.addWidget(l_header)
        self.l_editor = QChipSelect()
        l_layout.addWidget(self.l_editor, 1)
        self.layout().addLayout(l_layout)
        self.defaults["locations_selected"] = []
        self.defaults["locations_available"] = []

        # Query editor
        q_layout = QVBoxLayout()
        q_layout.setSpacing(0)
        q_layout.addWidget(QHeader("Search Queries", tooltip=Q_TT))
        self.q_editor = QPlainTextListEdit()
        q_layout.addWidget(self.q_editor)
        self.layout().addLayout(q_layout)
        self.defaults["queries"] = []

        # Hours old editor
        h_layout = QVBoxLayout()
        h_layout.setSpacing(0)
        h_header = QHeader("Data Freshness (Hours Old)")
        h_layout.addWidget(h_header)
        self.h_editor = QSpinBox(value=24, minimum=1, maximum=8760)
        self.h_editor.setFixedWidth(100)
        h_layout.addWidget(self.h_editor)
        self.layout().addLayout(h_layout)
        self.defaults["hours_old"] = 24

        # Push collect button to bottom
        self.layout().addStretch()

        # Run data collection
        self.run_btn = QPushButton("Collect Jobs")
        self.layout().addWidget(self.run_btn)
        self.run_btn.clicked.connect(self._on_run_clicked)
        self.run_btn.setFixedWidth(200)
        self.run_btn.setStyleSheet("margin-bottom: 20px;")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Register page with config model
        root_index = self._config_model.register_page("collect", self.defaults)

        # Map keys to config model indices
        for row in range(self._config_model.rowCount(root_index)):
            idx = self._config_model.index(row, 0, root_index)
            key = self._config_model.data(idx, Qt.ItemDataRole.DisplayRole)
            val_idx = self._config_model.index(row, 1, root_index)
            self._idcs[key] = val_idx

        # Connect view to config model
        self.ds_selector.sourceChanged.connect(
            lambda text: self._update_config("data_source", text))
        self.s_selector.selectionChanged.connect(
            lambda sel: self._update_config("sites_selected", sel))
        self.s_selector.availableChanged.connect(
            lambda avl: self._update_config("sites_available", avl))
        self.l_editor.selectionChanged.connect(
            lambda sel: self._update_config("locations_selected", sel))
        self.l_editor.availableChanged.connect(
            lambda avl: self._update_config("locations_available", avl))
        self.q_editor.itemsChanged.connect(
            lambda items: self._update_config("queries", items))
        self.h_editor.valueChanged.connect(
            lambda vals: self._update_config("hours_old", vals))

        # Connect config model to view updates
        self._config_model.dataChanged.connect(self._on_config_changed)

    def layout(self) -> QVBoxLayout:
        """Override layout to remove type-checking errors."""
        return super().layout() # type: ignore

    def _update_config(self, key: str, value):
        """Update model data from view changes."""
        if key in self._idcs:
            self._config_model.setData(self._idcs[key], value, Qt.ItemDataRole.EditRole)

    def __get_value(self, key: str, top_left: QModelIndex):
        """Get value from model for a specific key."""
        idx = self._idcs.get(key)
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._config_model.data(idx, Qt.ItemDataRole.DisplayRole)
            if val is None:
                val = self.defaults[key]
            return val
        return None

    @Slot(QModelIndex, QModelIndex)
    def _on_config_changed(self, top_left: QModelIndex, bottom_right: QModelIndex):
        """Update view when model data changes."""
        # Data source
        val = self.__get_value("data_source", top_left)
        if val is not None and val != self.ds_selector.get_source():
            self.ds_selector.set_source(val)

        # Sites
        val = self.__get_value("sites_selected", top_left)
        if val is not None and val != self.s_selector.get_selected():
            self.s_selector.set_selected(val)
            self._data_model.update_rank_order_score("site", val, "site_score")
            self._data_model.standard_ordering()
        val = self.__get_value("sites_available", top_left)
        if val is not None and val != self.s_selector.get_available():
            self.s_selector.set_available(val)

        # Locations
        val = self.__get_value("locations_selected", top_left)
        if val is not None and val != self.l_editor.get_selected():
            self.l_editor.set_selected(val)
        val = self.__get_value("locations_available", top_left)
        if val is not None and val != self.l_editor.get_available():
            self.l_editor.set_available(val)

        # Queries
        val = self.__get_value("queries", top_left)
        if val is not None and val != self.q_editor.get_items():
            self.q_editor.set_items(val)

        # Hours old
        val = self.__get_value("hours_old", top_left)
        if val is not None and val != self.h_editor.value():
            self.h_editor.setValue(val)

    @Slot()
    def _on_run_clicked(self):
        """Handle run button click."""
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
        """Handle completion of job data collection."""
        self.run_btn.setText("Collect Jobs")
        self.run_btn.setProperty("class", "")
        self.run_btn.style().unpolish(self.run_btn)
        self.run_btn.style().polish(self.run_btn)
        self.run_btn.setEnabled(True)
        self._cancel_event = None

    @Slot(str)
    def _on_collection_error(self, error_msg: str):
        """Handle errors during job data collection."""
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Collect Jobs")
        raise RuntimeError(f"Job data collection failed: {error_msg}")
