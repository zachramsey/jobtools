from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QRadioButton, QSpinBox
from PySide6.QtCore import Slot
from .custom_widgets import QHeader, QChipSelect
from ..utils.location_parser import NAME_TO_ABBR


DV_TT = """Adjust sorting values based on degree levels.\n
Higher values increase the ranking of jobs requiring the corresponding degree.
You can select preset options or manually set values for each degree level."""

LO_TT = """Define the order of preferred job locations.
Jobs located in higher-priority locations will receive better sorting values."""

HE_TT = """Terms whose presence in job listings will significantly
adjust sorting values to favor those listings."""

ME_TT = """Terms whose presence in job listings will moderately
adjust sorting values to favor those listings."""

LE_TT = """Terms whose presence in job listings will slightly
adjust sorting values to favor those listings."""

NE_TT = """Terms whose presence in job listings will not adjust
sorting values. These terms are tracked for reference only."""

DE_TT = """Terms whose presence in job listings will decrease
sorting values to disfavor those listings."""


class DegreeValueSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QHBoxLayout(self))
        # Define preset degree values
        self.no_values = (0, 0, 0)
        self.ba_values = (5, -3, -3)
        self.ma_values = (0, 5, -3)
        self.phd_values = (0, 0, 5)
        # Layout for degree value spin boxes
        self.values_layout = QHBoxLayout()
        self.spin_ba = self.setup_spin_box("BA", 0)
        self.values_layout.addWidget(self.spin_ba)
        self.spin_ma = self.setup_spin_box("MA", 1)
        self.values_layout.addWidget(self.spin_ma)
        self.spin_phd = self.setup_spin_box("PhD", 2)
        self.values_layout.addWidget(self.spin_phd)
        # Radio buttons for preset degree options
        self.radio_layout = QHBoxLayout()
        self.radio_none = self.setup_radio_button("None", self.no_values)
        self.radio_none.setChecked(True)
        self.radio_layout.addWidget(self.radio_none)
        self.radio_bachelors = self.setup_radio_button("Bachelors", self.ba_values)
        self.radio_layout.addWidget(self.radio_bachelors)
        self.radio_masters = self.setup_radio_button("Masters", self.ma_values)
        self.radio_layout.addWidget(self.radio_masters)
        self.radio_phd = self.setup_radio_button("Doctorate", self.phd_values)
        self.radio_layout.addWidget(self.radio_phd)
        self.radio_manual = self.setup_radio_button("Manual", (None, None, None))
        self.radio_layout.addWidget(self.radio_manual)
        # Set widths to the maximum of the radio buttons
        radio_buttons = [self.radio_none, self.radio_bachelors, self.radio_masters,
                         self.radio_phd, self.radio_manual]
        max_width = max([btn.sizeHint().width() for btn in radio_buttons])
        for btn in radio_buttons:
            btn.setFixedWidth(max_width)
        # Main layout
        self.layout().addLayout(self.radio_layout)
        self.layout().addLayout(self.values_layout)
        self.layout().addStretch()

    def setup_spin_box(self, label: str, level: int) -> QSpinBox:
        """ Create and configure a spin box for degree values. """
        spin_box = QSpinBox(prefix=f"{label}: ", minimum=-10, maximum=10, value=0)
        spin_box.valueChanged.connect(lambda val: self.__set_value(level, val))
        spin_box.setFixedWidth(100)
        return spin_box
    
    def setup_radio_button(self, label: str, values: tuple[int, int, int]) -> QRadioButton:
        """ Create and configure a radio button for preset degree values. """
        radio_btn = QRadioButton(label)
        if values != (None, None, None):
            radio_btn.clicked.connect(lambda: self.__set_values(*values))
        return radio_btn

    def get_values(self) -> tuple[int, int, int]:
        """ Access current degree values. """
        return (self.spin_ba.value(),
                self.spin_ma.value(),
                self.spin_phd.value())

    def set_values(self, ba: int, ma: int, phd: int):
        """ Set degree values and update radio buttons. """
        values = (ba, ma, phd)
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
        self.spin_ba.setValue(ba)
        self.spin_ma.setValue(ma)
        self.spin_phd.setValue(phd)

    @Slot()
    def __set_value(self, level: int, value: int):
        """ Set individual degree value and update radio buttons. """
        ba, ma, phd = self.get_values()
        if level == 0:
            ba = value
        elif level == 1:
            ma = value
        elif level == 2:
            phd = value
        self.set_values(ba, ma, phd)
    
    @Slot()
    def __set_values(self, ba: int|None, ma: int|None, phd: int|None):
        """ Set all degree values and update radio buttons. """
        if ba is None:    
            ba = self.spin_ba.value()
        if ma is None:    
            ma = self.spin_ma.value()
        if phd is None:    
            phd = self.spin_phd.value()
        self.set_values(ba, ma, phd)
    

class SortPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout(self))

        # Degree value selection
        self.layout().addWidget(QHeader("Degree Value Adjustments", tooltip=DV_TT))
        self.dv_selector = DegreeValueSelector()
        self.layout().addWidget(self.dv_selector)

        # Location order selection
        self.layout().addWidget(QHeader("Location Order", tooltip=LO_TT))
        state_abbr = [abbr.upper() for abbr in NAME_TO_ABBR.values()]
        self.lo_selector = QChipSelect(base_items=state_abbr,
                                       enable_creator=False)
        self.layout().addWidget(self.lo_selector)

        # Term emphasis selections
        levels = {3: ("High Emphasis Terms (+3)", HE_TT),
                  2: ("Medium Emphasis Terms (+2)", ME_TT),
                  1: ("Low Emphasis Terms (+1)", LE_TT),
                  0: ("Unemphasized Terms (+0)", NE_TT),
                  -1: ("Deemphasized Terms (-1)", DE_TT)}
        self.te_selectors: dict[int, QChipSelect] = {}    # type: ignore
        for value, (label, tooltip) in levels.items():
            self.layout().addWidget(QHeader(label, tooltip=tooltip))
            selector = QChipSelect()
            self.te_selectors[value] = selector
            self.layout().addWidget(selector)

        # Push content to top
        self.layout().addStretch()

    def get_selected(self) -> dict:
        """ Get selected sort options. """
        return {
            "degree_values": self.dv_selector.get_values(),
            "location_order": self.lo_selector.get_selected(),
            "term_emphasis": {val: sel.get_selected()
                              for val, sel in self.te_selectors.items()}
        }
    
    def get_config(self) -> dict:
        """ Access current sort configuration. """
        return {
            "degree_values": self.dv_selector.get_values(),
            "location_order": self.lo_selector.get_selected(),
            "term_emphasis": {val: {"selected": sel.get_selected(),
                                   "available": sel.get_available()}
                              for val, sel in self.te_selectors.items()}
        }
    
    def set_config(self, config: dict):
        """ Set sort configuration. """
        dv = config.get("degree_values", (0, 0, 0))
        self.dv_selector.set_values(*dv)
        lo = config.get("location_order", [])
        self.lo_selector.set_selected(lo)
        te = config.get("term_emphasis", {})
        for val, sel in self.te_selectors.items():
            term_cfg = te.get(val, {})
            sel.set_selected(term_cfg.get("selected", []))
            sel.set_available(term_cfg.get("available", []))
