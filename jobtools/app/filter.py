from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QModelIndex, Qt, Slot
from jobspy.model import JobType      # type: ignore
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
        self._idcs: dict[str, QModelIndex] = {}                         # type: ignore
        defaults: dict = {}

        # Wok model selector
        self.layout().addWidget(QHeader("Work Model", tooltip=WM_TT))   # type: ignore
        self.wm_selector = QCheckBoxSelect(["Remote", "Onsite"])
        self.layout().addWidget(self.wm_selector)                       # type: ignore
        defaults["work_models"] = []

        # Job type selector
        self.layout().addWidget(QHeader("Job Types", tooltip=JT_TT))    # type: ignore
        self.jt_selector = QCheckBoxSelect([jt.name.replace("_", " ").title()
                                            for jt in JobType])
        self.layout().addWidget(self.jt_selector)                       # type: ignore
        defaults["job_types"] = []

        # Title exclude editor
        self.layout().addWidget(                                        # type: ignore
            QHeader("Title Term Exclusions", tooltip=TE_TT))    
        self.te_editor = QChipSelect()
        self.layout().addWidget(self.te_editor)                         # type: ignore
        defaults["title_exclude"] = ([], [])

        # Title require editor
        self.layout().addWidget(                                        # type: ignore
            QHeader("Title Term Requirements", tooltip=TR_TT))
        self.tr_editor = QChipSelect()
        self.layout().addWidget(self.tr_editor)                         # type: ignore
        defaults["title_require"] = ([], [])

        # Description exclude editor
        self.layout().addWidget(                                        # type: ignore
            QHeader("Description Term Exclusions", tooltip=DE_TT))
        self.de_editor = QChipSelect()
        self.layout().addWidget(self.de_editor)                         # type: ignore
        defaults["descr_exclude"] = ([], [])

        # Description require editor
        self.layout().addWidget(                                        # type: ignore
            QHeader("Description Term Requirements", tooltip=DR_TT))
        self.dr_editor = QChipSelect()
        self.layout().addWidget(self.dr_editor)                         # type: ignore
        defaults["descr_require"] = ([], [])

        # Push content to top
        self.layout().addStretch()                                      # type: ignore

        # Register page with model
        root_index = self._model.register_page("filter", defaults)

        # Map property keys to model indices
        for row in range(self._model.rowCount(root_index)):
            idx = self._model.index(row, 0, root_index)
            key = self._model.data(idx, Qt.ItemDataRole.DisplayRole)
            val_idx = self._model.index(row, 1, root_index)
            self._idcs[key] = val_idx

        # Connect view to data model
        self.wm_selector.selectionChanged.connect(
            lambda sel: self._update_model("work_models", sel))
        self.jt_selector.selectionChanged.connect(
            lambda sel: self._update_model("job_types", sel))
        self.te_editor.selectionChanged.connect(
            lambda sel: self._update_model("title_exclude", sel))
        self.tr_editor.selectionChanged.connect(
            lambda sel: self._update_model("title_require", sel))
        self.de_editor.selectionChanged.connect(
            lambda sel: self._update_model("descr_exclude", sel))
        self.dr_editor.selectionChanged.connect(
            lambda sel: self._update_model("descr_require", sel))
        
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
        # Work model selector
        idx = self._idcs.get("work_models")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.EditRole)
            if self.wm_selector.get_selected() != val:
                self.wm_selector.set_selected(val)
        # Job type selector
        idx = self._idcs.get("job_types")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.EditRole)
            if self.jt_selector.get_selected() != val:
                self.jt_selector.set_selected(val)
        # Title exclude editor
        idx = self._idcs.get("title_exclude")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.EditRole)
            selected, available = val if val is not None else ([], [])
            if self.te_editor.get_selected() != selected:
                self.te_editor.set_selected(selected)
            if self.te_editor.get_available() != available:
                self.te_editor.set_available(available)
        # Title require editor
        idx = self._idcs.get("title_require")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.EditRole)
            selected, available = val if val is not None else ([], [])
            if self.tr_editor.get_selected() != selected:
                self.tr_editor.set_selected(selected)
            if self.tr_editor.get_available() != available:
                self.tr_editor.set_available(available)
        # Description exclude editor
        idx = self._idcs.get("descr_exclude")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.EditRole)
            selected, available = val if val is not None else ([], [])
            if self.de_editor.get_selected() != selected:
                self.de_editor.set_selected(selected)
            if self.de_editor.get_available() != available:
                self.de_editor.set_available(available)
        # Description require editor
        idx = self._idcs.get("descr_require")
        if idx is not None and (not top_left.isValid() or top_left == idx):
            val = self._model.data(idx, Qt.ItemDataRole.EditRole)
            selected, available = val if val is not None else ([], [])
            if self.dr_editor.get_selected() != selected:
                self.dr_editor.set_selected(selected)
            if self.dr_editor.get_available() != available:
                self.dr_editor.set_available(available)
