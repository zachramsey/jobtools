from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QModelIndex, Qt, Slot
from jobspy.model import JobType    # type: ignore
from .widgets import QHeader, QChipSelect, QCheckBoxSelect
from ..models import ConfigModel, JobsDataModel


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
        self.setLayout(QVBoxLayout(self))
        self._config_model = config_model
        self._data_model = data_model
        self._idcs: dict[str, QModelIndex] = {}
        self.defaults: dict = {}

        # Wok model selector
        self.layout().addWidget(QHeader("Work Model", tooltip=WM_TT))
        self.wm_selector = QCheckBoxSelect(["remote", "onsite"])
        self.layout().addWidget(self.wm_selector)
        self.defaults["work_models"] = []

        # Job type selector
        self.layout().addWidget(QHeader("Job Types", tooltip=JT_TT))
        self.jt_selector = QCheckBoxSelect([jt.value[0] for jt in JobType])
        self.layout().addWidget(self.jt_selector)
        self.defaults["job_types"] = []

        # Title exclude editor
        self.layout().addWidget(
            QHeader("Title Term Exclusions", tooltip=TE_TT))    
        self.te_editor = QChipSelect()
        self.layout().addWidget(self.te_editor)
        self.defaults["title_exclude_selected"] = []
        self.defaults["title_exclude_available"] = []

        # Title require editor
        self.layout().addWidget(
            QHeader("Title Term Requirements", tooltip=TR_TT))
        self.tr_editor = QChipSelect()
        self.layout().addWidget(self.tr_editor)
        self.defaults["title_require_selected"] = []
        self.defaults["title_require_available"] = []

        # Description exclude editor
        self.layout().addWidget(
            QHeader("Description Term Exclusions", tooltip=DE_TT))
        self.de_editor = QChipSelect()
        self.layout().addWidget(self.de_editor)
        self.defaults["descr_exclude_selected"] = []
        self.defaults["descr_exclude_available"] = []

        # Description require editor
        self.layout().addWidget(
            QHeader("Description Term Requirements", tooltip=DR_TT))
        self.dr_editor = QChipSelect()
        self.layout().addWidget(self.dr_editor)
        self.defaults["descr_require_selected"] = []
        self.defaults["descr_require_available"] = []

        # Push content to top
        self.layout().addStretch()

        # Register page with model
        root_index = self._config_model.register_page("filter", self.defaults)

        # Map property keys to model indices
        for row in range(self._config_model.rowCount(root_index)):
            idx = self._config_model.index(row, 0, root_index)
            key = self._config_model.data(idx, Qt.ItemDataRole.DisplayRole)
            val_idx = self._config_model.index(row, 1, root_index)
            self._idcs[key] = val_idx

        # Connect view to config model
        self.wm_selector.selectionChanged.connect(
            lambda L: self._update_config("work_models", L))
        self.jt_selector.selectionChanged.connect(
            lambda L: self._update_config("job_types", L))
        self.te_editor.selectionChanged.connect(
            lambda L: self._update_config("title_exclude_selected", L))
        self.te_editor.availableChanged.connect(
            lambda L: self._update_config("title_exclude_available", L))
        self.tr_editor.selectionChanged.connect(
            lambda L: self._update_config("title_require_selected", L))
        self.tr_editor.availableChanged.connect(
            lambda L: self._update_config("title_require_available", L))
        self.de_editor.selectionChanged.connect(
            lambda L: self._update_config("descr_exclude_selected", L))
        self.de_editor.availableChanged.connect(
            lambda L: self._update_config("descr_exclude_available", L))
        self.dr_editor.selectionChanged.connect(
            lambda L: self._update_config("descr_require_selected", L))
        self.dr_editor.availableChanged.connect(
            lambda L: self._update_config("descr_require_available", L))
        
        # Connect config model to view updates
        self._config_model.dataChanged.connect(self._on_config_changed)

    def layout(self) -> QVBoxLayout:
        """ Override layout to remove type-checking errors. """
        return super().layout() # type: ignore

    def _update_config(self, key: str, value):
        """ Update model data from view changes. """
        idx = self._idcs.get(key)
        if idx is not None:
            self._config_model.setData(idx, value, Qt.ItemDataRole.EditRole)

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
