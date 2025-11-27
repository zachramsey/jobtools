from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton, QSpinBox, QLineEdit
from PySide6.QtCore import Slot
from .custom_widgets import QPlainTextListEdit


class ProxyEdit(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout(self))
        # Section label
        self.layout().addWidget(QLabel("<h3>Proxy</h3>"))
        # Proxy input
        self.proxy_editor = QLineEdit("Edit proxy...")
        self.layout().addWidget(self.proxy_editor)

    def get_proxy(self) -> str:
        """ Access current proxy string. """
        return self.proxy_editor.text().strip()


class DataSourceSelect(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout(self))
        # Section label
        self.layout().addWidget(QLabel("<h3>Data Load Options</h3>"))
        # Radio buttons for data source selection
        radio_layout = QHBoxLayout()
        self.radio_none = QRadioButton("None")
        radio_layout.addWidget(self.radio_none)
        self.radio_none.setChecked(True)
        self.radio_global = QRadioButton("Global CSV")
        radio_layout.addWidget(self.radio_global)
        self.radio_recent = QRadioButton("Recent CSV")
        radio_layout.addWidget(self.radio_recent)
        self.radio_manual = QRadioButton("Manual")
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Subdirectory path...")
        self.path_input.setEnabled(False)
        self.radio_manual.toggled.connect(self.path_input.setEnabled)
        radio_layout.addWidget(self.radio_manual)
        radio_layout.addWidget(self.path_input)
        self.layout().addLayout(radio_layout)
    
    def get_data_source(self) -> str:
        """ Access selected data source string. """
        if self.radio_none.isChecked():
            return ""
        elif self.radio_global.isChecked():
            return "global"
        elif self.radio_recent.isChecked():
            return "recent"
        elif self.radio_manual.isChecked():
            return self.path_input.text().strip()
        else:
            return ""
    

class QueryEdit(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout(self))
        # Section label
        self.layout().addWidget(QLabel("<h3>Search Queries</h3>"))
        # Query editor
        self.query_editor = QPlainTextListEdit()
        self.layout().addWidget(self.query_editor)

    def get_queries(self) -> list[str]:
        """ Access current list of queries. """
        return self.query_editor.get_items()


class DegreeValueSelect(QWidget):
    def __init__(self):
        super().__init__()
        # Define preset degree values
        self.no_values = (0, 0, 0)
        self.ba_values = (5, -3, -3)
        self.ma_values = (0, 5, -3)
        self.phd_values = (0, 0, 5)
        # Layout for degree value spin boxes
        values_layout = QHBoxLayout()
        self.spin_ba = QSpinBox(prefix="BA: ", minimum=-10, maximum=10, value=0)
        self.spin_ba.valueChanged.connect(lambda val: self.set_degree_value(0, val))
        values_layout.addWidget(self.spin_ba)
        self.spin_ma = QSpinBox(prefix="MA: ", minimum=-10, maximum=10, value=0)
        self.spin_ma.valueChanged.connect(lambda val: self.set_degree_value(1, val))
        values_layout.addWidget(self.spin_ma)
        self.spin_phd = QSpinBox(prefix="PhD: ", minimum=-10, maximum=10, value=0)
        self.spin_phd.valueChanged.connect(lambda val: self.set_degree_value(2, val))
        values_layout.addWidget(self.spin_phd)
        # Radio buttons for preset degree options
        radio_layout = QHBoxLayout()
        self.radio_none = QRadioButton("None")
        self.radio_none.setChecked(True)
        self.radio_none.clicked.connect(lambda: self.set_degree_values(*self.no_values))
        radio_layout.addWidget(self.radio_none)
        self.radio_bachelors = QRadioButton("Bachelors")
        self.radio_bachelors.clicked.connect(lambda: self.set_degree_values(*self.ba_values))
        radio_layout.addWidget(self.radio_bachelors)
        self.radio_masters = QRadioButton("Masters")
        self.radio_masters.clicked.connect(lambda: self.set_degree_values(*self.ma_values))
        radio_layout.addWidget(self.radio_masters)
        self.radio_phd = QRadioButton("Doctorate")
        self.radio_phd.clicked.connect(lambda: self.set_degree_values(*self.phd_values))
        radio_layout.addWidget(self.radio_phd)
        self.radio_manual = QRadioButton("Manual")
        radio_layout.addWidget(self.radio_manual)
        # Section label
        label = QLabel("<h3>Degree Preference & Score Values</h3>")
        # Combine radio buttons and spin boxes
        input_layout = QHBoxLayout()
        input_layout.addLayout(radio_layout)
        input_layout.addLayout(values_layout)
        # Set main layout
        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(label)
        self.layout().addLayout(input_layout)
        self.layout().addStretch()
                             
    @property
    def _degree_values(self) -> tuple[int, int, int]:
        """ Access current degree values. """
        return (self.spin_ba.value(),
                self.spin_ma.value(),
                self.spin_phd.value())
    
    @_degree_values.setter
    def _degree_values(self, values: tuple[int, int, int]):
        """ Set degree values and update radio buttons. """
        if values == self.no_values:
            self.radio_none.setChecked(True)
        elif values == self.ba_values:
            self.radio_bachelors.setChecked(True)
        elif values == self.ma_values:
            self.radio_masters.setChecked(True)
        elif values == self.phd_values:
            self.radio_phd.setChecked(True)
        else:
            self.radio_manual.setChecked(True)
        self.spin_ba.setValue(values[0])
        self.spin_ma.setValue(values[1])
        self.spin_phd.setValue(values[2])

    @Slot(int, int)
    def set_degree_value(self, level: int, value: int):
        """ Set individual degree value and update radio buttons. """
        ba, ma, phd = self._degree_values
        if level == 0:
            ba = value
        elif level == 1:
            ma = value
        elif level == 2:
            phd = value
        self._degree_values = (ba, ma, phd)
    
    @Slot(int, int, int)
    def set_degree_values(self, ba: int, ma: int, phd: int):
        """ Set all degree values and update radio buttons. """
        if ba is None:    
            ba = self.spin_ba.value()
        if ma is None:    
            ma = self.spin_ma.value()
        if phd is None:    
            phd = self.spin_phd.value()
        self._degree_values = (ba, ma, phd)

    def get_degree_values(self) -> tuple[int, int, int]:
        """ Access current degree values. """
        return self._degree_values


class CollectorPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout(self))
        # Proxy editor
        self.proxy_editor = ProxyEdit()
        self.layout().addWidget(self.proxy_editor)
        # Data source selection
        self.load_options = DataSourceSelect()
        self.layout().addWidget(self.load_options)
        # Query editor   
        self.query_editor = QueryEdit()
        self.layout().addWidget(self.query_editor)
        # Degree value selection
        self.degree_options = DegreeValueSelect()
        self.layout().addWidget(self.degree_options)
        # Push content to top
        self.layout().addStretch()

    def get_proxy(self) -> str:
        """ Access current proxy string. """
        return self.proxy_editor.get_proxy()
    
    def get_data_source(self) -> str:
        """ Access selected data source string. """
        return self.load_options.get_data_source()

    def get_queries(self) -> list[str]:
        """ Access current list of queries. """
        return self.query_editor.get_queries()
    
    def get_degree_values(self) -> tuple[int, int, int]:
        """ Access current degree values. """
        return self.degree_options.get_degree_values()
