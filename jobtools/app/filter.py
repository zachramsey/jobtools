from PySide6.QtWidgets import QWidget, QVBoxLayout
from .custom_widgets import QHeader, QChipSelect, QCheckBoxSelect
from jobspy.model import JobType      # type: ignore


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
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout(self))

        # Wok model selector
        self.layout().addWidget(QHeader("Work Model", tooltip=WM_TT))
        self.wm_selector = QCheckBoxSelect(["Remote", "Onsite"])
        self.layout().addWidget(self.wm_selector)

        # Job type selector
        self.layout().addWidget(QHeader("Job Types", tooltip=JT_TT))
        self.jt_selector = QCheckBoxSelect([jt.name.replace("_", " ").title()
                                            for jt in JobType])
        self.layout().addWidget(self.jt_selector)

        # Title exclude editor
        self.layout().addWidget(QHeader("Title Term Exclusions", tooltip=TE_TT))
        self.te_editor = QChipSelect()
        self.layout().addWidget(self.te_editor)

        # Title require editor
        self.layout().addWidget(QHeader("Title Term Requirements", tooltip=TR_TT))
        self.tr_editor = QChipSelect()
        self.layout().addWidget(self.tr_editor)

        # Description exclude editor
        self.layout().addWidget(QHeader("Description Term Exclusions", tooltip=DE_TT))
        self.de_editor = QChipSelect()
        self.layout().addWidget(self.de_editor)

        # Description require editor
        self.layout().addWidget(QHeader("Description Term Requirements", tooltip=DR_TT))
        self.dr_editor = QChipSelect()
        self.layout().addWidget(self.dr_editor)

        # Push content to top
        self.layout().addStretch()

    def get_selected(self) -> dict:
        """ Get selected filter options. """
        return {
            "work_models": self.wm_selector.get_selected(),
            "job_types": self.jt_selector.get_selected(),
            "title_exclude": self.te_editor.get_selected(),
            "title_require": self.tr_editor.get_selected(),
            "descr_exclude": self.de_editor.get_selected(),
            "descr_require": self.dr_editor.get_selected(),
        }
    
    def get_config(self) -> dict:
        """ Access current filter configuration. """
        return {
            "work_models": self.wm_selector.get_selected(),
            "job_types": self.jt_selector.get_selected(),
            "title_exclude": {"selected": self.te_editor.get_selected(),
                              "available": self.te_editor.get_available()},
            "title_require": {"selected": self.tr_editor.get_selected(),
                              "available": self.tr_editor.get_available()},
            "descr_exclude": {"selected": self.de_editor.get_selected(),
                              "available": self.de_editor.get_available()},
            "descr_require": {"selected": self.dr_editor.get_selected(),
                              "available": self.dr_editor.get_available()},
        }
    
    def set_config(self, config: dict):
        """ Set filter configuration. """
        self.wm_selector.set_selected(config.get("work_models", []))
        self.jt_selector.set_selected(config.get("job_types", []))
        te = config.get("title_exclude", {})
        self.te_editor.set_selected(te.get("selected", []))
        self.te_editor.set_available(te.get("available", []))
        tr = config.get("title_require", {})
        self.tr_editor.set_selected(tr.get("selected", []))
        self.tr_editor.set_available(tr.get("available", []))
        de = config.get("descr_exclude", {})
        self.de_editor.set_selected(de.get("selected", []))
        self.de_editor.set_available(de.get("available", []))
        dr = config.get("descr_require", {})
        self.dr_editor.set_selected(dr.get("selected", []))
        self.dr_editor.set_available(dr.get("available", []))
    