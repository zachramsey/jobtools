from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QRadioButton, QLineEdit
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
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout(self))
        # Section label
        header = QHeader("Data Source", tooltip=DS_TT)
        self.layout().addWidget(header)
        # Radio buttons for data source selection
        radio_layout = QHBoxLayout()
        self.radio_none = QRadioButton("None")
        radio_layout.addWidget(self.radio_none)
        self.radio_none.setChecked(True)
        self.radio_archive = QRadioButton("Archive")
        radio_layout.addWidget(self.radio_archive)
        self.radio_latest = QRadioButton("Latest")
        radio_layout.addWidget(self.radio_latest)
        self.radio_manual = QRadioButton("Manual")
        # Set widths to the maximum of the radio buttons
        radio_buttons = [self.radio_none, self.radio_archive,
                         self.radio_latest, self.radio_manual]
        max_width = max([btn.sizeHint().width() for btn in radio_buttons])
        for btn in radio_buttons:
            btn.setFixedWidth(max_width)
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Subdirectory path...")
        self.path_input.setEnabled(False)
        self.radio_manual.toggled.connect(self.path_input.setEnabled)
        radio_layout.addWidget(self.radio_manual)
        radio_layout.addWidget(self.path_input)
        radio_layout.addStretch()
        self.layout().addLayout(radio_layout)

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
        if source == "":
            self.radio_none.setChecked(True)
        elif source == "archive":
            self.radio_archive.setChecked(True)
        elif source == "latest":
            self.radio_latest.setChecked(True)
        else:
            self.radio_manual.setChecked(True)
            self.path_input.setText(source)


class CollectorPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout(self))
        
        # Proxy editor
        self.layout().addWidget(QHeader("Proxy Server", tooltip=P_TT))
        self.p_editor = QLineEdit(placeholderText="user:pass@host:port")
        self.layout().addWidget(self.p_editor)

        # Data source selection
        self.layout().addWidget(QHeader("Data Source", tooltip=DS_TT))
        self.ds_selector = DataSourceSelector()
        self.layout().addWidget(self.ds_selector)

        # Site selection
        self.layout().addWidget(QHeader("Job Sites", tooltip=S_TT))
        self.s_selector = QChipSelect(base_items=["LinkedIn", "Indeed"],
                                     enable_creator=False)
        self.layout().addWidget(self.s_selector)

        # Query editor   
        self.layout().addWidget(QHeader("Search Queries", tooltip=Q_TT))
        self.q_editor = QPlainTextListEdit()
        self.layout().addWidget(self.q_editor)

        # Push content to top
        self.layout().addStretch()

    def get_selected(self) -> dict:
        """ Get selected collector options. """
        return {
            "proxy": self.p_editor.text().strip(),
            "data_source": self.ds_selector.get_source(),
            "sites": self.s_selector.get_selected(),
            "queries": self.q_editor.get_items(),
        }
    
    def get_config(self) -> dict:
        """ Access current collector configuration. """
        return {
            "proxy": self.p_editor.text().strip(),
            "data_source": self.ds_selector.get_source(),
            "sites": self.s_selector.get_selected(),
            "queries": self.q_editor.get_items(),
        }
    
    def set_config(self, config: dict):
        """ Set collector configuration. """
        self.p_editor.setText(config.get("proxy", ""))
        self.ds_selector.set_source(config.get("data_source", ""))
        self.s_selector.set_selected(config.get("sites", []))
        self.q_editor.set_items(config.get("queries", []))
