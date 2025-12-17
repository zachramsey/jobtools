from PySide6.QtWidgets import (QWidget, QHBoxLayout, QGridLayout,
                               QRadioButton, QLineEdit, QSpinBox, QPushButton)
from PySide6.QtCore import QModelIndex, Qt, Signal, Slot, QObject, QThread
from threading import Event
import traceback
from ..models import ConfigModel, JobsDataModel
from .widgets import QHeader, QPlainTextListEdit, QChipSelect


P_TT = """Optional proxy server for web requests.

Highly recommended!

The job collector makes many requests in a short
period, which may trigger anti-bot protections on
job sites. Using a proxy will distribute these
requests and help avoid IP blocking."""

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
        except Exception:
            self.error.emit(traceback.format_exc())


class DataSourceSelector(QWidget):
    """ Widget for selecting data source. """

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
        self.path_input.setFixedWidth(400)
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
        """ Emit current source when selection changes. """
        self.sourceChanged.emit(self.get_source())

    def get_source(self) -> str:
        """ Data source selection. """
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
        """ Set data source selection. """
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

        self.setLayout(QGridLayout(self))
        self.layout().setHorizontalSpacing(50)

        # Proxy editor
        self.layout().addWidget(QHeader("Proxy Server", tooltip=P_TT), 0, 0)
        self.p_editor = QLineEdit(placeholderText="user:pass@host:port")
        self.p_editor.setMinimumWidth(400)
        self.p_editor.setMaximumWidth(800)
        self.layout().addWidget(self.p_editor, 1, 0)
        self.defaults["proxy"] = ""

        # Data source selection
        self.layout().addWidget(QHeader("Data Source", tooltip=DS_TT), 0, 1)
        self.ds_selector = DataSourceSelector()
        self.layout().addWidget(self.ds_selector, 1, 1)
        self.defaults["data_source"] = ""

        self.__add_spacer(2)

        # Site selection
        self.layout().addWidget(QHeader("Job Sites", tooltip=S_TT), 3, 0)
        available = ["LinkedIn", "Indeed"]
        self.s_selector = QChipSelect(base_items=available,
                                      enable_creator=False)
        self.s_selector.setMinimumWidth(400)
        self.s_selector.setMaximumWidth(800)
        self.layout().addWidget(self.s_selector, 4, 0)
        self.defaults["sites_selected"] = []
        self.defaults["sites_available"] = available

        # Locations editor
        self.layout().addWidget(QHeader("Locations", tooltip=L_TT), 3, 1)
        self.l_editor = QChipSelect()
        self.layout().addWidget(self.l_editor, 4, 1)
        self.defaults["locations_selected"] = []
        self.defaults["locations_available"] = []

        self.__add_spacer(5)

        # Query editor   
        self.layout().addWidget(QHeader("Search Queries", tooltip=Q_TT), 5, 0, 1, 2)
        self.q_editor = QPlainTextListEdit()
        self.layout().addWidget(self.q_editor, 6, 0, 1, 2)
        self.defaults["queries"] = []

        self.__add_spacer(7)

        # Hours old editor
        self.layout().addWidget(QHeader("Data Freshness (Hours Old)"), 8, 0, 1, 2)
        self.h_editor = QSpinBox(value=24, minimum=1, maximum=8760)
        self.h_editor.setFixedWidth(100)
        self.layout().addWidget(self.h_editor, 9, 0, 1, 2)
        self.defaults["hours_old"] = 24

        self.__add_spacer(10)

        # Run data collection
        self.run_btn = QPushButton("Collect Jobs")
        self.layout().addWidget(self.run_btn, 11, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignBottom)
        self.layout().setRowStretch(11, 1)
        self.run_btn.clicked.connect(self._on_run_clicked)
        self.run_btn.setFixedWidth(200)
        self.run_btn.setStyleSheet("margin-bottom: 20px;")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Register page with model
        root_index = self._config_model.register_page("collect", self.defaults)

        # Map property keys to model indices
        for row in range(self._config_model.rowCount(root_index)):
            idx = self._config_model.index(row, 0, root_index)
            key = self._config_model.data(idx, Qt.ItemDataRole.DisplayRole)
            val_idx = self._config_model.index(row, 1, root_index)
            self._idcs[key] = val_idx

        # Connect view to data model
        self.p_editor.textChanged.connect(
            lambda t: self._update_config("proxy", t))
        self.ds_selector.sourceChanged.connect(
            lambda t: self._update_config("data_source", t))
        self.s_selector.selectionChanged.connect(
            lambda L: self._update_config("sites_selected", L))
        self.s_selector.availableChanged.connect(
            lambda L: self._update_config("sites_available", L))
        self.l_editor.selectionChanged.connect(
            lambda L: self._update_config("locations_selected", L))
        self.l_editor.availableChanged.connect(
            lambda L: self._update_config("locations_available", L))
        self.q_editor.itemsChanged.connect(
            lambda L: self._update_config("queries", L))
        self.h_editor.valueChanged.connect(
            lambda n: self._update_config("hours_old", n))
        
        # Connect model to view updates
        self._config_model.dataChanged.connect(self._on_config_changed)

    def __add_spacer(self, row: int):
        """ Add a vertical spacer at the given row. """
        spacer = QWidget()
        spacer.setFixedHeight(20)
        self.layout().addWidget(spacer, row, 0, 1, 2)

    def layout(self) -> QGridLayout:
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
