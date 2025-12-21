from jobspy.model import JobType  # type: ignore
from PySide6.QtCore import QModelIndex, Qt, Slot
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..models import ConfigModel, JobsDataModel
from .widgets import QCheckBoxSelect, QChipSelect, QHeader

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
    def __init__(self, config_model: ConfigModel, data_model: JobsDataModel):
        super().__init__()
        self._config_model = config_model
        self._data_model = data_model
        self._idcs: dict[str, QModelIndex] = {}
        self.defaults: dict = {}
        self.setLayout(QVBoxLayout(self))
        self.layout().setSpacing(20)

        # Work model selector
        wm_layout = QHBoxLayout()
        wm_header = QHeader("Work Model", tooltip=WM_TT)
        wm_header.setFixedWidth(200)
        wm_layout.addWidget(wm_header)
        self.wm_selector = QCheckBoxSelect(["remote", "onsite"])
        wm_layout.addWidget(self.wm_selector, 1)
        self.layout().addLayout(wm_layout)
        self.defaults["work_models"] = []

        # Job type selector
        jt_layout = QHBoxLayout()
        jt_header = QHeader("Job Types", tooltip=JT_TT)
        jt_header.setFixedWidth(200)
        jt_layout.addWidget(jt_header)
        self.jt_selector = QCheckBoxSelect([jt.value[0] for jt in JobType])
        jt_layout.addWidget(self.jt_selector, 1)
        self.layout().addLayout(jt_layout)
        self.defaults["job_types"] = []

        # Title exclude editor
        te_layout = QVBoxLayout()
        te_layout.setSpacing(0)
        te_header = QHeader("Title Term Exclusions", tooltip=TE_TT)
        te_layout.addWidget(te_header)
        self.te_editor = QChipSelect()
        te_layout.addWidget(self.te_editor)
        self.layout().addLayout(te_layout)
        self.defaults["title_exclude_selected"] = []
        self.defaults["title_exclude_available"] = []

        # Title require editor
        tr_layout = QVBoxLayout()
        tr_layout.setSpacing(0)
        tr_header = QHeader("Title Term Requirements", tooltip=TR_TT)
        tr_layout.addWidget(tr_header)
        self.tr_editor = QChipSelect()
        tr_layout.addWidget(self.tr_editor)
        self.layout().addLayout(tr_layout)
        self.defaults["title_require_selected"] = []
        self.defaults["title_require_available"] = []

        # Description exclude editor
        de_layout = QVBoxLayout()
        de_layout.setSpacing(0)
        de_header = QHeader("Description Term Exclusions", tooltip=DE_TT)
        de_layout.addWidget(de_header)
        self.de_editor = QChipSelect()
        de_layout.addWidget(self.de_editor)
        self.layout().addLayout(de_layout)
        self.defaults["descr_exclude_selected"] = []
        self.defaults["descr_exclude_available"] = []

        # Description require editor
        dr_layout = QVBoxLayout()
        dr_layout.setSpacing(0)
        dr_header = QHeader("Description Term Requirements", tooltip=DR_TT)
        dr_layout.addWidget(dr_header)
        self.dr_editor = QChipSelect()
        dr_layout.addWidget(self.dr_editor)
        self.layout().addLayout(dr_layout)
        self.defaults["descr_require_selected"] = []
        self.defaults["descr_require_available"] = []

        # Push content to top
        self.layout().addStretch()

        # Register page with config model
        root_index = self._config_model.register_page("filter", self.defaults)

        # Map keys to config model indices
        for row in range(self._config_model.rowCount(root_index)):
            idx = self._config_model.index(row, 0, root_index)
            key = self._config_model.data(idx, Qt.ItemDataRole.DisplayRole)
            val_idx = self._config_model.index(row, 1, root_index)
            self._idcs[key] = val_idx

        # Connect view to config model
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
        self._config_model.dataChanged.connect(self._on_config_changed)

    def layout(self) -> QVBoxLayout:
        """Override layout to remove type-checking errors."""
        return super().layout() # type: ignore

    def _update_config(self, key: str, value):
        """Update model data from view changes."""
        idx = self._idcs.get(key)
        if idx is not None:
            self._config_model.setData(idx, value, Qt.ItemDataRole.EditRole)

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
        # Work model selector
        val = self.__get_value("work_models", top_left)
        if val is not None:
            if val != self.wm_selector.get_selected():
                self.wm_selector.set_selected(val)
            val = [wm.upper() == "remote" for wm in val]
            self._data_model.set_filter("work_models", "is_remote", val)

        # Job type selector
        val = self.__get_value("job_types", top_left)
        if val is not None:
            if val != self.jt_selector.get_selected():
                self.jt_selector.set_selected(val)
            self._data_model.set_filter("job_types", "job_type", val)

        # Title exclude editor
        val = self.__get_value("title_exclude_available", top_left)
        if val is not None and val != self.te_editor.get_available():
            self.te_editor.set_available(val)
        val = self.__get_value("title_exclude_selected", top_left)
        if val is not None:
            if val != self.te_editor.get_selected():
                self.te_editor.set_selected(val)
            self._data_model.set_filter("title_exclude", "title", val, invert=True)

        # Title require editor
        val = self.__get_value("title_require_available", top_left)
        if val is not None and val != self.tr_editor.get_available():
            self.tr_editor.set_available(val)
        val = self.__get_value("title_require_selected", top_left)
        if val is not None:
            if val != self.tr_editor.get_selected():
                self.tr_editor.set_selected(val)
            self._data_model.set_filter("title_require", "title", val)

        # Description exclude editor
        val = self.__get_value("descr_exclude_available", top_left)
        if val is not None and val != self.de_editor.get_available():
            self.de_editor.set_available(val)
        val = self.__get_value("descr_exclude_selected", top_left)
        if val is not None:
            if val != self.de_editor.get_selected():
                self.de_editor.set_selected(val)
            self._data_model.set_filter("descr_exclude", "description", val, invert=True)

        # Description require editor
        val = self.__get_value("descr_require_available", top_left)
        if val is not None and val != self.dr_editor.get_available():
            self.dr_editor.set_available(val)
        val = self.__get_value("descr_require_selected", top_left)
        if val is not None:
            if val != self.dr_editor.get_selected():
                self.dr_editor.set_selected(val)
            self._data_model.set_filter("descr_require", "description", val)
