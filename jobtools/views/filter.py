from jobspy.model import JobType  # type: ignore
from PySide6.QtCore import QModelIndex, Qt, Slot
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..models import ConfigModel
from .widgets import QCheckBoxSelect, QChipSelect, QHeader

MA_TT = """Maximum age of job postings to display.\n
Jobs older than this value will be filtered out."""

DL_TT = """Degree level required for job postings to display.\n
None - no degree filtering; all jobs included.
Bachelor - filter jobs in favor of Bachelor's degree.
Master - filter jobs in favor of Master's degree.
Doctorate - filter jobs in favor of Doctorate degree."""

WM_TT = """Select which work models to include in results.\n
Remote - jobs that can be done entirely remotely.
Onsite - jobs that require presence at a specific location."""

JT_TT = """Select which job types to include in results.\n
Full Time - standard full-time employment positions.
Part Time - positions with reduced hours compared to full-time.
Contract - temporary positions for a specific project or duration.
Temporary - short-term positions, often seasonal or project-based.
Internship - positions for students or trainees to gain work experience.
Per Diem - jobs paid by the day, often in healthcare or education.
Nights - positions that primarily require night shifts.
Other - any job types that do not fit into the standard categories.
Summer - seasonal positions typically available during the summer months.
Volunteer - unpaid positions for charitable or non-profit work."""

TE_TT = """Terms whose presence in job titles will exclude a job from results.
Accepts single words, multi-word phrases, and regular expressions."""

TR_TT = """Terms whose absence in job titles will exclude a job from results.
Accepts single words, multi-word phrases, and regular expressions."""

DE_TT = """Terms whose presence in job descriptions will exclude a job from results.
Accepts single words, multi-word phrases, and regular expressions."""

DR_TT = """Terms whose absence in job descriptions will exclude a job from results.
Accepts single words, multi-word phrases, and regular expressions."""


class FilterPage(QWidget):
    def __init__(self, config_model: ConfigModel):
        super().__init__()
        self._cfg_model = config_model
        defaults: dict = {}

        self.setLayout(QVBoxLayout(self))
        self.layout().setSpacing(10)

        # Maximum age selector
        ma_layout = QHBoxLayout()
        ma_header = QHeader("Maximum Posting Age:", tooltip=MA_TT)
        ma_header.setFixedWidth(200)
        ma_layout.addWidget(ma_header)
        self.ma_selector = QSpinBox(suffix=" days", minimum=1)
        ma_layout.addWidget(self.ma_selector)
        ma_layout.addStretch()
        self.layout().addLayout(ma_layout)
        defaults["max_age_days"] = 1

        # Degree level selector
        dl_layout = QHBoxLayout()
        dl_header = QHeader("Degree Level", tooltip=DL_TT)
        dl_header.setFixedWidth(200)
        dl_layout.addWidget(dl_header)
        self.dl_selector = QButtonGroup(self)
        for level in ["none", "bachelor", "master", "doctorate"]:
            btn = QRadioButton(level.title())
            self.dl_selector.addButton(btn)
            dl_layout.addWidget(btn)
        self.dl_selector.buttons()[0].setChecked(True)
        dl_layout.addStretch()
        self.layout().addLayout(dl_layout)
        defaults["degree_level"] = "none"

        # Work model selector
        wm_layout = QHBoxLayout()
        wm_header = QHeader("Work Model", tooltip=WM_TT)
        wm_header.setFixedWidth(200)
        wm_layout.addWidget(wm_header)
        self.wm_selector = QCheckBoxSelect(["remote", "onsite"])
        wm_layout.addWidget(self.wm_selector, 1)
        self.layout().addLayout(wm_layout)
        defaults["work_models"] = []

        # Job type selector
        jt_layout = QHBoxLayout()
        jt_header = QHeader("Job Types", tooltip=JT_TT)
        jt_header.setFixedWidth(200)
        jt_layout.addWidget(jt_header)
        self.jt_selector = QCheckBoxSelect([jt.value[0] for jt in JobType])
        jt_layout.addWidget(self.jt_selector, 1)
        self.layout().addLayout(jt_layout)
        defaults["job_types"] = []

        # Title exclude editor
        te_layout = QVBoxLayout()
        te_layout.setSpacing(0)
        te_header = QHeader("Title Term Exclusions", tooltip=TE_TT)
        te_layout.addWidget(te_header)
        self.te_editor = QChipSelect()
        te_layout.addWidget(self.te_editor)
        self.layout().addLayout(te_layout)
        defaults["title_exclude_selected"] = []
        defaults["title_exclude_available"] = []

        # Title require editor
        tr_layout = QVBoxLayout()
        tr_layout.setSpacing(0)
        tr_header = QHeader("Title Term Requirements", tooltip=TR_TT)
        tr_layout.addWidget(tr_header)
        self.tr_editor = QChipSelect()
        tr_layout.addWidget(self.tr_editor)
        self.layout().addLayout(tr_layout)
        defaults["title_require_selected"] = []
        defaults["title_require_available"] = []

        # Description exclude editor
        de_layout = QVBoxLayout()
        de_layout.setSpacing(0)
        de_header = QHeader("Description Term Exclusions", tooltip=DE_TT)
        de_layout.addWidget(de_header)
        self.de_editor = QChipSelect()
        de_layout.addWidget(self.de_editor)
        self.layout().addLayout(de_layout)
        defaults["descr_exclude_selected"] = []
        defaults["descr_exclude_available"] = []

        # Description require editor
        dr_layout = QVBoxLayout()
        dr_layout.setSpacing(0)
        dr_header = QHeader("Description Term Requirements", tooltip=DR_TT)
        dr_layout.addWidget(dr_header)
        self.dr_editor = QChipSelect()
        dr_layout.addWidget(self.dr_editor)
        self.layout().addLayout(dr_layout)
        defaults["descr_require_selected"] = []
        defaults["descr_require_available"] = []

        # Push content to top
        self.layout().addStretch()

        # Register page with config model
        self._cfg_model.register_page("filter", defaults)

        # Connect view to config model
        self.ma_selector.valueChanged.connect(
            lambda val: self._update_config("max_age_days", val))
        self.dl_selector.buttonClicked.connect(
            lambda btn: self._update_config("degree_level", btn.text().lower()))
        self.wm_selector.selectionChanged.connect(
            lambda sel: self._update_config("work_models", sel))
        self.jt_selector.selectionChanged.connect(
            lambda sel: self._update_config("job_types", sel))
        self.te_editor.selectionChanged.connect(
            lambda sel: self._update_config("title_exclude_selected", sel))
        self.te_editor.availableChanged.connect(
            lambda avl: self._update_config("title_exclude_available", avl))
        self.tr_editor.selectionChanged.connect(
            lambda sel: self._update_config("title_require_selected", sel))
        self.tr_editor.availableChanged.connect(
            lambda avl: self._update_config("title_require_available", avl))
        self.de_editor.selectionChanged.connect(
            lambda sel: self._update_config("descr_exclude_selected", sel))
        self.de_editor.availableChanged.connect(
            lambda avl: self._update_config("descr_exclude_available", avl))
        self.dr_editor.selectionChanged.connect(
            lambda sel: self._update_config("descr_require_selected", sel))
        self.dr_editor.availableChanged.connect(
            lambda avl: self._update_config("descr_require_available", avl))

        # Connect config model to view updates
        self._cfg_model.dataChanged.connect(self._on_config_changed)

    def layout(self) -> QVBoxLayout:
        """Override layout to remove type-checking errors."""
        return super().layout() # type: ignore

    def _update_config(self, key: str, value):
        """Update model data from view changes."""
        idx = self._cfg_model.idcs.get(key)
        if idx is not None:
            self._cfg_model.setData(idx, value, Qt.ItemDataRole.EditRole)

    @Slot(QModelIndex, QModelIndex)
    def _on_config_changed(self, top_left: QModelIndex, bottom_right: QModelIndex):
        """Update view when model data changes."""
        # Maximum age selector
        val = self._cfg_model.get_value("max_age_days", top_left)
        if val is not None and val != self.ma_selector.value():
            self.ma_selector.setValue(val)

        # Degree level selector
        val = self._cfg_model.get_value("degree_level", top_left)
        if val is not None:
            for btn in self.dl_selector.buttons():
                if btn.text().lower() == val and not btn.isChecked():
                    btn.setChecked(True)
                    break

        # Work model selector
        val = self._cfg_model.get_value("work_models", top_left)
        if val is not None:
            if val != self.wm_selector.get_selected():
                self.wm_selector.set_selected(val)

        # Job type selector
        val = self._cfg_model.get_value("job_types", top_left)
        if val is not None:
            if val != self.jt_selector.get_selected():
                self.jt_selector.set_selected(val)

        # Title exclude editor
        val = self._cfg_model.get_value("title_exclude_available", top_left)
        if val is not None and val != self.te_editor.get_available():
            self.te_editor.set_available(val)
        val = self._cfg_model.get_value("title_exclude_selected", top_left)
        if val is not None:
            if val != self.te_editor.get_selected():
                self.te_editor.set_selected(val)

        # Title require editor
        val = self._cfg_model.get_value("title_require_available", top_left)
        if val is not None and val != self.tr_editor.get_available():
            self.tr_editor.set_available(val)
        val = self._cfg_model.get_value("title_require_selected", top_left)
        if val is not None:
            if val != self.tr_editor.get_selected():
                self.tr_editor.set_selected(val)

        # Description exclude editor
        val = self._cfg_model.get_value("descr_exclude_available", top_left)
        if val is not None and val != self.de_editor.get_available():
            self.de_editor.set_available(val)
        val = self._cfg_model.get_value("descr_exclude_selected", top_left)
        if val is not None:
            if val != self.de_editor.get_selected():
                self.de_editor.set_selected(val)

        # Description require editor
        val = self._cfg_model.get_value("descr_require_available", top_left)
        if val is not None and val != self.dr_editor.get_available():
            self.dr_editor.set_available(val)
        val = self._cfg_model.get_value("descr_require_selected", top_left)
        if val is not None:
            if val != self.dr_editor.get_selected():
                self.dr_editor.set_selected(val)
