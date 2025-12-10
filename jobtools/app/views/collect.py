from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QRadioButton, QLineEdit, QSpinBox)
from PySide6.QtCore import QModelIndex, Qt, Signal, Slot
from ..models.config_model import ConfigModel
from ..custom_widgets import QHeader, QPlainTextListEdit, QChipSelect


P_TT = """Optional proxy server for web requests.\n
Highly recommended! The job collector makes many requests in
a short period, which may lead to IP blocking without a proxy."""

DS_TT = """Select the source of job data to load.\n
None - starts a fresh collection.
Archive - loads previously collected data.
Latest - fetches the most recent data available.
Manual - allows specifying a custom subdirectory path."""

S_TT = """Select which job sites to collect data from."""

L_TT = """Locations to search for jobs in.\n
Accepts cities, states/provinces, countries, and combinations thereof. """

Q_TT = """List of search queries to use when collecting job data.
Each query will be used to perform a separate search on each selected job site.\n
Boolean operators (AND, OR, NOT), quotation marks for
exact phrases, and parentheses for grouping are supported.
Example: "software engineer" AND (python OR java) NOT intern"""


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
            btn.setFixedWidth(max_width)
        # Manual path input
        self.path_input = QLineEdit()
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
    def __init__(self, model: ConfigModel):
        super().__init__()
        self.setLayout(QVBoxLayout(self))
        self._model = model
        self._idcs: dict[str, QModelIndex] = {}
        self.defaults: dict = {}
        
        # Proxy editor
        self.layout().addWidget(QHeader("Proxy Server", tooltip=P_TT))
        self.p_editor = QLineEdit(placeholderText="user:pass@host:port")
        self.layout().addWidget(self.p_editor)
        self.defaults["proxy"] = ""

        # Data source selection
        self.layout().addWidget(QHeader("Data Source", tooltip=DS_TT))
        self.ds_selector = DataSourceSelector()
        self.layout().addWidget(self.ds_selector)
        self.defaults["data_source"] = ""

        # Site selection
        self.layout().addWidget(QHeader("Job Sites", tooltip=S_TT))
        available = ["LinkedIn", "Indeed"]
        self.s_selector = QChipSelect(base_items=available,
                                      enable_creator=False)
        self.layout().addWidget(self.s_selector)
        self.defaults["sites_selected"] = []
        self.defaults["sites_available"] = available

        # Locations editor
        self.layout().addWidget(QHeader("Locations"))
        self.l_editor = QChipSelect()
        self.layout().addWidget(self.l_editor)
        self.defaults["locations_selected"] = []
        self.defaults["locations_available"] = []

        # Query editor   
        self.layout().addWidget(QHeader("Search Queries", tooltip=Q_TT))
        self.q_editor = QPlainTextListEdit()
        self.layout().addWidget(self.q_editor)
        self.defaults["queries"] = []

        # Hours old editor
        self.layout().addWidget(QHeader("Data Freshness (Hours Old)"))
        self.h_editor = QSpinBox(value=24, minimum=1, maximum=8760)
        self.h_editor.setFixedWidth(100)
        self.layout().addWidget(self.h_editor)
        self.defaults["hours_old"] = 24

        # Push content to top
        self.layout().addStretch()

        # Register page with model
        root_index = self._model.register_page("collect", self.defaults)

        # Map property keys to model indices
        for row in range(self._model.rowCount(root_index)):
            idx = self._model.index(row, 0, root_index)
            key = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val_idx = self._model.index(row, 1, root_index)
            self._idcs[key] = val_idx

        # Connect view to data model
        self.p_editor.textChanged.connect(
            lambda t: self._update_model("proxy", t))
        self.ds_selector.sourceChanged.connect(
            lambda t: self._update_model("data_source", t))
        self.s_selector.selectionChanged.connect(
            lambda L: self._update_model("sites_selected", L))
        self.s_selector.availableChanged.connect(
            lambda L: self._update_model("sites_available", L))
        self.l_editor.selectionChanged.connect(
            lambda L: self._update_model("locations_selected", L))
        self.l_editor.availableChanged.connect(
            lambda L: self._update_model("locations_available", L))
        self.q_editor.itemsChanged.connect(
            lambda L: self._update_model("queries", L))
        self.h_editor.valueChanged.connect(
            lambda n: self._update_model("hours_old", n))
        
        # Connect model to view updates
        self._model.dataChanged.connect(self._data_changed)

        # Trigger initial data load
        self._data_changed(QModelIndex(), QModelIndex())

    def layout(self) -> QVBoxLayout:
        """ Override layout to remove type-checking errors. """
        return super().layout() # type: ignore

    def _update_model(self, key: str, value):
        """ Update model data from view changes. """
        if key in self._idcs:
            self._model.setData(self._idcs[key], value, Qt.ItemDataRole.EditRole)

    def __get_value(self, key: str, top_left: QModelIndex):
        """ Helper to get model value for a key if in changed range. """
        idx = self._idcs.get(key)
        if idx is None or (top_left.isValid() and top_left != idx):
            return self.defaults[key]
        val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
        return val if val is not None else self.defaults[key]

    @Slot(QModelIndex, QModelIndex)
    def _data_changed(self, top_left: QModelIndex, bottom_right: QModelIndex):
        """ Update view when model data changes. """
        # Proxy
        idx = self._idcs.get("proxy")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["proxy"]
            if self.p_editor.text().strip() != val:
                self.p_editor.setText(val)
        # Data source
        idx = self._idcs.get("data_source")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["data_source"]
            if self.ds_selector.get_source() != val:
                self.ds_selector.set_source(val)
        # Sites
        idx = self._idcs.get("sites_selected")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["sites_selected"]
            if self.s_selector.get_selected() != val:
                self.s_selector.set_selected(val)
        idx = self._idcs.get("sites_available")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["sites_available"]
            if self.s_selector.get_available() != val:
                self.s_selector.set_available(val)
        # Locations
        idx = self._idcs.get("locations_selected")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self.__get_value("locations_selected", top_left)
            val = val if val is not None else self.defaults["locations_selected"]
            if self.l_editor.get_selected() != val:
                self.l_editor.set_selected(val)
        idx = self._idcs.get("locations_available")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self.__get_value("locations_available", top_left)
            val = val if val is not None else self.defaults["locations_available"]
            if self.l_editor.get_available() != val:
                self.l_editor.set_available(val)
        # Queries
        idx = self._idcs.get("queries")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["queries"]
            if self.q_editor.get_items() != val:
                self.q_editor.set_items(val)
        # Hours old
        idx = self._idcs.get("hours_old")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["hours_old"]
            if self.h_editor.value() != val:
                self.h_editor.setValue(val)
