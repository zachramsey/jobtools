from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QModelIndex, Qt, Slot
from jobspy.model import JobType    # type: ignore
from .custom_widgets import QHeader, QChipSelect, QCheckBoxSelect
from .model import ConfigModel


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
    def __init__(self, model: ConfigModel):
        super().__init__()
        self.setLayout(QVBoxLayout(self))
        self._model = model
        self._idcs: dict[str, QModelIndex] = {}
        self.defaults: dict = {}

        # Wok model selector
        self.layout().addWidget(QHeader("Work Model", tooltip=WM_TT))
        self.wm_selector = QCheckBoxSelect(["REMOTE", "ONSITE"])
        self.layout().addWidget(self.wm_selector)
        self.defaults["work_models"] = []

        # Job type selector
        self.layout().addWidget(QHeader("Job Types", tooltip=JT_TT))
        self.jt_selector = QCheckBoxSelect([jt.name for jt in JobType])
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
        root_index = self._model.register_page("filter", self.defaults)

        # Map property keys to model indices
        for row in range(self._model.rowCount(root_index)):
            idx = self._model.index(row, 0, root_index)
            key = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val_idx = self._model.index(row, 1, root_index)
            self._idcs[key] = val_idx

        # Connect view to data model
        self.wm_selector.selectionChanged.connect(
            lambda L: self._update_model("work_models", L))
        self.jt_selector.selectionChanged.connect(
            lambda L: self._update_model("job_types", L))
        self.te_editor.selectionChanged.connect(
            lambda L: self._update_model("title_exclude_selected", L))
        self.te_editor.availableChanged.connect(
            lambda L: self._update_model("title_exclude_available", L))
        self.tr_editor.selectionChanged.connect(
            lambda L: self._update_model("title_require_selected", L))
        self.tr_editor.availableChanged.connect(
            lambda L: self._update_model("title_require_available", L))
        self.de_editor.selectionChanged.connect(
            lambda L: self._update_model("descr_exclude_selected", L))
        self.de_editor.availableChanged.connect(
            lambda L: self._update_model("descr_exclude_available", L))
        self.dr_editor.selectionChanged.connect(
            lambda L: self._update_model("descr_require_selected", L))
        self.dr_editor.availableChanged.connect(
            lambda L: self._update_model("descr_require_available", L))
        
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
        # Work model selector
        idx = self._idcs.get("work_models")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["work_models"]
            if self.wm_selector.get_selected() != val:
                self.wm_selector.set_selected(val)
        # Job type selector
        idx = self._idcs.get("job_types")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["job_types"]
            if self.jt_selector.get_selected() != val:
                self.jt_selector.set_selected(val)
        # Title exclude editor
        idx = self._idcs.get("title_exclude_selected")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["title_exclude_selected"]
            if self.te_editor.get_selected() != val:
                self.te_editor.set_selected(val)
        idx = self._idcs.get("title_exclude_available")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["title_exclude_available"]
            if self.te_editor.get_available() != val:
                self.te_editor.set_available(val)
        # Title require editor
        idx = self._idcs.get("title_require_selected")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["title_require_selected"]
            if self.tr_editor.get_selected() != val:
                self.tr_editor.set_selected(val)
        idx = self._idcs.get("title_require_available")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["title_require_available"]
            if self.tr_editor.get_available() != val:
                self.tr_editor.set_available(val)
        # Description exclude editor
        idx = self._idcs.get("descr_exclude_selected")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["descr_exclude_selected"]
            if self.de_editor.get_selected() != val:
                self.de_editor.set_selected(val)
        idx = self._idcs.get("descr_exclude_available")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["descr_exclude_available"]
            if self.de_editor.get_available() != val:
                self.de_editor.set_available(val)
        # Description require editor
        idx = self._idcs.get("descr_require_selected")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["descr_require_selected"]
            if self.dr_editor.get_selected() != val:
                self.dr_editor.set_selected(val)
        idx = self._idcs.get("descr_require_available")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val = val if val is not None else self.defaults["descr_require_available"]
            if self.dr_editor.get_available() != val:
                self.dr_editor.set_available(val)
