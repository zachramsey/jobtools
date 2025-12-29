from threading import Event

import pandas as pd  # type: ignore
from PySide6.QtCore import QModelIndex, Qt, QThread, Slot
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSpinBox, QVBoxLayout, QWidget

from ..models import ConfigModel, JobsDataModel
from ..models.collection_worker import CollectionWorker
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


class CollectPage(QWidget):
    def __init__(self, config_model: ConfigModel, data_model: JobsDataModel):
        super().__init__()
        self._cfg_model = config_model
        self._data_model = data_model
        defaults: dict = {}

        self.setLayout(QVBoxLayout(self))
        self.layout().setSpacing(20)

        # Site selection
        s_layout = QHBoxLayout()
        s_header = QHeader("Job Sites", tooltip=S_TT)
        s_header.setFixedWidth(200)
        s_layout.addWidget(s_header)
        available = ["LinkedIn", "Indeed"]
        self.s_selector = QChipSelect(base_items=available, enable_creator=False)
        s_layout.addWidget(self.s_selector, 1)
        self.layout().addLayout(s_layout)
        defaults["sites_selected"] = []
        defaults["sites_available"] = available

        # Locations editor
        l_layout = QHBoxLayout()
        l_header = QHeader("Locations", tooltip=L_TT)
        l_header.setFixedWidth(200)
        l_layout.addWidget(l_header)
        self.l_editor = QChipSelect()
        l_layout.addWidget(self.l_editor, 1)
        self.layout().addLayout(l_layout)
        defaults["locations_selected"] = []
        defaults["locations_available"] = []

        # Query editor
        q_layout = QVBoxLayout()
        q_layout.setSpacing(0)
        q_layout.addWidget(QHeader("Search Queries", tooltip=Q_TT))
        self.q_editor = QPlainTextListEdit()
        q_layout.addWidget(self.q_editor)
        self.layout().addLayout(q_layout)
        defaults["queries"] = []

        # Hours old editor
        h_layout = QVBoxLayout()
        h_layout.setSpacing(0)
        h_header = QHeader("Data Freshness (Hours Old)")
        h_layout.addWidget(h_header)
        self.h_editor = QSpinBox(value=24, minimum=1, maximum=8760)
        self.h_editor.setFixedWidth(100)
        h_layout.addWidget(self.h_editor)
        self.layout().addLayout(h_layout)
        defaults["hours_old"] = 24

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
        self._cfg_model.register_page("collect", defaults)

        # Connect view to config model
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
        # Sites
        val = self._cfg_model.get_value("sites_selected", top_left)
        if val is not None and val != self.s_selector.get_selected():
            self.s_selector.set_selected(val)
        val = self._cfg_model.get_value("sites_available", top_left)
        if val is not None and val != self.s_selector.get_available():
            self.s_selector.set_available(val)

        # Locations
        val = self._cfg_model.get_value("locations_selected", top_left)
        if val is not None and val != self.l_editor.get_selected():
            self.l_editor.set_selected(val)
        val = self._cfg_model.get_value("locations_available", top_left)
        if val is not None and val != self.l_editor.get_available():
            self.l_editor.set_available(val)

        # Queries
        val = self._cfg_model.get_value("queries", top_left)
        if val is not None and val != self.q_editor.get_items():
            self.q_editor.set_items(val)

        # Hours old
        val = self._cfg_model.get_value("hours_old", top_left)
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
            self.worker = CollectionWorker(self._cfg_model, self._cancel_event)
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
            self._data_model.collectStarted.emit()
            self.worker_thread.start()
        else:
            # Signal cancellation
            if self._cancel_event:
                self._cancel_event.set()
            self.run_btn.setText("Canceling...")
            self.run_btn.setEnabled(False)

    @Slot(str)
    def _on_collection_finished(self, jobs_data: pd.DataFrame):
        """Handle completion of job data collection."""
        self.run_btn.setText("Collect Jobs")
        self.run_btn.setProperty("class", "")
        self.run_btn.style().unpolish(self.run_btn)
        self.run_btn.style().polish(self.run_btn)
        self.run_btn.setEnabled(True)
        self._cancel_event = None
        self._data_model.update(jobs_data)
        self._data_model.collectFinished.emit()

    @Slot(str)
    def _on_collection_error(self, error_msg: str):
        """Handle errors during job data collection."""
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Collect Jobs")
        raise RuntimeError(f"Job data collection failed: {error_msg}")
