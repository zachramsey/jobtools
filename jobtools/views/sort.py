from PySide6.QtCore import QModelIndex, Qt, Signal, Slot
from PySide6.QtWidgets import QHBoxLayout, QRadioButton, QSpinBox, QVBoxLayout, QWidget

from ..models import ConfigModel
from ..utils.location_parser import NAME_TO_ABBR
from .widgets import QChipSelect, QHeader

DV_TT = """Adjust sorting values based on degree levels.

Higher values increase the ranking of jobs requiring the corresponding degree.

The value for each degree level may be set manually or a preset may be
selected whose values weight the job ordering toward that degree level."""

LO_TT = """Define the order of preferred job locations.

Jobs located in higher-priority locations will receive better sorting values."""

PT_TT = """Terms whose presence in job listings will
adjust sorting values to favor those listings."""

UT_TT = """Terms whose presence in job listings will not adjust
sorting values. These terms are tracked for reference only."""

DT_TT = """Terms whose presence in job listings will decrease
sorting values to disfavor those listings."""


class DegreeValueSelector(QWidget):
    """Widget for selecting degree values."""

    valuesChanged = Signal(int, int, int)
    """ Signal emitted when the degree values change. """

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

        # Connect signals
        for btn in radio_buttons:
            btn.toggled.connect(self._on_change)
        for spin_box in [self.spin_ba, self.spin_ma, self.spin_phd]:
            spin_box.valueChanged.connect(self._on_change)

    @Slot()
    def _on_change(self):
        """Emit current degree values when changed."""
        self.valuesChanged.emit(*self.get_values())

    def setup_spin_box(self, label: str, level: int) -> QSpinBox:
        """Create and configure a spin box for degree values."""
        spin_box = QSpinBox(prefix=f"{label}: ", minimum=-10, maximum=10, value=0)
        spin_box.valueChanged.connect(lambda val: self.__set_value(level, val))
        spin_box.setFixedWidth(100)
        return spin_box

    def setup_radio_button(self, label: str, values: tuple[int, int, int]) -> QRadioButton:
        """Create and configure a radio button for preset degree values."""
        radio_btn = QRadioButton(label)
        if values != (None, None, None):
            radio_btn.clicked.connect(lambda: self.__set_values(*values))
        return radio_btn

    def get_values(self) -> tuple[int, int, int]:
        """Access current degree values."""
        return (self.spin_ba.value(),
                self.spin_ma.value(),
                self.spin_phd.value())

    def set_values(self, ba: int, ma: int, phd: int):
        """Set degree values and update radio buttons."""
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
        """Set individual degree value and update radio buttons."""
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
        """Set all degree values and update radio buttons."""
        if ba is None:
            ba = self.spin_ba.value()
        if ma is None:
            ma = self.spin_ma.value()
        if phd is None:
            phd = self.spin_phd.value()
        self.set_values(ba, ma, phd)


class SortPage(QWidget):
    def __init__(self, config_model: ConfigModel):
        super().__init__()
        self._cfg_model = config_model
        defaults: dict = {}

        self.setLayout(QVBoxLayout(self))
        self.layout().setSpacing(20)

        # Degree value selection
        dv_layout = QHBoxLayout()
        dv_header = QHeader("Degree Values", tooltip=DV_TT)
        dv_header.setFixedWidth(200)
        dv_layout.addWidget(dv_header)
        self.dv_selector = DegreeValueSelector()
        dv_layout.addWidget(self.dv_selector, 1)
        self.layout().addLayout(dv_layout)
        defaults["degree_values"] = (0, 0, 0)

        # Location order selection
        lo_layout = QVBoxLayout()
        lo_layout.setSpacing(0)
        lo_header = QHeader("Location Order", tooltip=LO_TT)
        lo_layout.addWidget(lo_header)
        available = [abbr.upper() for abbr in NAME_TO_ABBR.values()]
        self.lo_selector = QChipSelect(base_items=available, enable_creator=False)
        lo_layout.addWidget(self.lo_selector)
        self.layout().addLayout(lo_layout)
        defaults["location_order_selected"] = []
        defaults["location_order_available"] = available

        # Prioritized terms selection
        pt_layout = QVBoxLayout()
        pt_layout.setSpacing(0)
        pt_layout.addWidget(QHeader("Prioritized Terms", tooltip=PT_TT))
        self.pt_selector = QChipSelect()
        pt_layout.addWidget(self.pt_selector)
        self.layout().addLayout(pt_layout)
        defaults["prioritized_terms_selected"] = []
        defaults["prioritized_terms_available"] = []

        # Unprioritized terms selection
        ut_layout = QVBoxLayout()
        ut_layout.setSpacing(0)
        ut_layout.addWidget(QHeader("Unprioritized Terms", tooltip=UT_TT))
        self.ut_selector = QChipSelect()
        ut_layout.addWidget(self.ut_selector)
        self.layout().addLayout(ut_layout)
        defaults["unprioritized_terms_selected"] = []
        defaults["unprioritized_terms_available"] = []

        # Deprioritized terms selection
        dt_layout = QVBoxLayout()
        dt_layout.setSpacing(0)
        dt_layout.addWidget(QHeader("Deprioritized Terms", tooltip=DT_TT))
        self.dt_selector = QChipSelect()
        dt_layout.addWidget(self.dt_selector)
        self.layout().addLayout(dt_layout)
        defaults["deprioritized_terms_selected"] = []
        defaults["deprioritized_terms_available"] = []

        # Push content to top
        self.layout().addStretch()

        # Register page with config model
        self._cfg_model.register_page("sort", defaults)

        # Connect view to config model
        self.dv_selector.valuesChanged.connect(
            lambda ba, ma, phd: self._update_config("degree_values", (ba, ma, phd)))
        self.lo_selector.selectionChanged.connect(
            lambda sel: self._update_config("location_order_selected", sel))
        self.lo_selector.availableChanged.connect(
            lambda avl: self._update_config("location_order_available", avl))
        self.pt_selector.selectionChanged.connect(
            lambda sel: self._update_config("prioritized_terms_selected", sel))
        self.pt_selector.availableChanged.connect(
            lambda avl: self._update_config("prioritized_terms_available", avl))
        self.ut_selector.selectionChanged.connect(
            lambda sel: self._update_config("unprioritized_terms_selected", sel))
        self.ut_selector.availableChanged.connect(
            lambda avl: self._update_config("unprioritized_terms_available", avl))
        self.dt_selector.selectionChanged.connect(
            lambda sel: self._update_config("deprioritized_terms_selected", sel))
        self.dt_selector.availableChanged.connect(
            lambda avl: self._update_config("deprioritized_terms_available", avl))

        # Connect config model to view updates
        self._cfg_model.dataChanged.connect(self._on_config_changed)

    def layout(self) -> QVBoxLayout:
        """Override layout to remove type-checking errors."""
        return super().layout() # type: ignore

    def _update_config(self, key: str, value):
        """Update config model from view changes."""
        idx = self._cfg_model.idcs.get(key)
        if idx is not None:
            self._cfg_model.setData(idx, value, Qt.ItemDataRole.EditRole)

    @Slot(QModelIndex, QModelIndex)
    def _on_config_changed(self, top_left: QModelIndex, bottom_right: QModelIndex):
        """Update view when config model changes."""
        # Degree values
        val = self._cfg_model.get_value("degree_values", top_left)
        if val is not None and val != self.dv_selector.get_values():
            self.dv_selector.set_values(*val)

        # Location order
        val = self._cfg_model.get_value("location_order_available", top_left)
        if val is not None and val != self.lo_selector.get_available():
            self.lo_selector.set_available(val)
        val = self._cfg_model.get_value("location_order_selected", top_left)
        if val is not None and val != self.lo_selector.get_selected():
            self.lo_selector.set_selected(val)

        # Prioritized terms
        val = self._cfg_model.get_value("prioritized_terms_available", top_left)
        if val is not None and val != self.pt_selector.get_available():
            self.pt_selector.set_available(val)
        val = self._cfg_model.get_value("prioritized_terms_selected", top_left)
        if val is not None and val != self.pt_selector.get_selected():
            self.pt_selector.set_selected(val)

        # Unprioritized terms
        val = self._cfg_model.get_value("unprioritized_terms_available", top_left)
        if val is not None and val != self.ut_selector.get_available():
            self.ut_selector.set_available(val)
        val = self._cfg_model.get_value("unprioritized_terms_selected", top_left)
        if val is not None and val != self.ut_selector.get_selected():
            self.ut_selector.set_selected(val)

        # Deprioritized terms
        val = self._cfg_model.get_value("deprioritized_terms_available", top_left)
        if val is not None and val != self.dt_selector.get_available():
            self.dt_selector.set_available(val)
        val = self._cfg_model.get_value("deprioritized_terms_selected", top_left)
        if val is not None and val != self.dt_selector.get_selected():
            self.dt_selector.set_selected(val)
