from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QRadioButton,
                               QLineEdit)
from PySide6.QtCore import QModelIndex, Qt, Signal, Slot
from .model import ConfigModel
from .custom_widgets import QHeader, QPlainTextListEdit, QChipSelect


P_TT = """Optional proxy server for web requests.\n
Highly recommended! The job collector makes many requests in
a short period, which may lead to IP blocking without a proxy."""

DS_TT = """Select the source of job data to load.\n
None - starts a fresh collection.
Archive - loads previously collected data.
Latest - fetches the most recent data available.
Manual - allows specifying a custom subdirectory path."""

S_TT = """Select which job sites to collect data from."""

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
        self._idcs: dict[str, QModelIndex] = {}                             # type: ignore
        defaults: dict = {}
        
        # Proxy editor
        self.layout().addWidget(QHeader("Proxy Server", tooltip=P_TT))      # type: ignore
        self.p_editor = QLineEdit(placeholderText="user:pass@host:port")
        self.layout().addWidget(self.p_editor)                              # type: ignore
        defaults["proxy"] = ""

        # Data source selection
        self.layout().addWidget(QHeader("Data Source", tooltip=DS_TT))      # type: ignore
        self.ds_selector = DataSourceSelector()
        self.layout().addWidget(self.ds_selector)                           # type: ignore
        defaults["data_source"] = ""

        # Site selection
        self.layout().addWidget(QHeader("Job Sites", tooltip=S_TT))         # type: ignore
        self.s_selector = QChipSelect(base_items=["LinkedIn", "Indeed"],
                                     enable_creator=False)
        self.layout().addWidget(self.s_selector)                            # type: ignore
        defaults["sites"] = []

        # Query editor   
        self.layout().addWidget(QHeader("Search Queries", tooltip=Q_TT))    # type: ignore
        self.q_editor = QPlainTextListEdit()
        self.layout().addWidget(self.q_editor)                              # type: ignore
        defaults["queries"] = []

        # Push content to top
        self.layout().addStretch()                                          # type: ignore

        # Register page with model
        root_index = self._model.register_page("collect", defaults)

        # Map property keys to model indices
        for row in range(self._model.rowCount(root_index)):
            idx = self._model.index(row, 0, root_index)
            key = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val_idx = self._model.index(row, 1, root_index)
            self._idcs[key] = val_idx

        # Connect view to data model
        self.p_editor.textChanged.connect(
            lambda text: self._update_model("proxy", text.strip()))
        self.ds_selector.sourceChanged.connect(
            lambda source: self._update_model("data_source", source))
        self.s_selector.selectionChanged.connect(
            lambda sites: self._update_model("sites", sites[0]))
        self.q_editor.itemsChanged.connect(
            lambda queries: self._update_model("queries", queries))
        
        # Connect model to view updates
        self._model.dataChanged.connect(self._data_changed)

        # Trigger initial data load
        self._data_changed(QModelIndex(), QModelIndex())

    def _update_model(self, key: str, value):
        """ Update model data from view changes. """
        if key in self._idcs:
            self._model.setData(self._idcs[key], value, Qt.ItemDataRole.EditRole)

    @Slot(QModelIndex, QModelIndex)
    def _data_changed(self, top_left: QModelIndex, bottom_right: QModelIndex):
        """ Update view when model data changes. """
        # Proxy
        idx = self._idcs.get("proxy")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            if self.p_editor.text().strip() != val:
                self.p_editor.setText(val)
        # Data source
        idx = self._idcs.get("data_source")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            if self.ds_selector.get_source() != val:
                self.ds_selector.set_source(val)
        # Sites
        idx = self._idcs.get("sites")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            if self.s_selector.get_selected() != val:
                self.s_selector.set_selected(val)
        # Queries
        idx = self._idcs.get("queries")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            if self.q_editor.get_items() != val:
                self.q_editor.set_items(val)
