from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QTextEdit, QVBoxLayout

from ..utils import clean_description
from .widgets import QWebImageLabel


class JobDetails(QDialog):
    """Popup dialog to show detailed job information."""

    def __init__(self, job_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Job Details")
        self.setLayout(QVBoxLayout(self))
        # Job Source Links
        source = QHBoxLayout()
        site_str = job_data.get("site", "Job Board").title()
        if job_url_str := job_data.get("job_url", ""):
            job_url_label = QLabel(f'<a href="{job_url_str}">{site_str} Posting</a>')
            job_url_label.setOpenExternalLinks(True)
        else:
            job_url_label = QLabel(site_str)
        source.addWidget(job_url_label)
        if job_url_direct_str := job_data.get("job_url_direct", ""):
            job_url_direct_label = QLabel(f'<a href="{job_url_direct_str}">Direct Posting</a>')
            job_url_direct_label.setOpenExternalLinks(True)
            source.addWidget(job_url_direct_label)
        source.addStretch()
        self.layout().addLayout(source)
        self.layout().addSpacing(10)
        # Date Posted
        date_posted_label = QLabel(job_data.get("date_posted", "Unknown Date"))
        self.layout().addWidget(date_posted_label)
        self.layout().addSpacing(10)
        # Job Title
        title_label = QLabel(f"<h2>{job_data.get('title', 'Unknown Job Title')}</h2>")
        title_label.setWordWrap(True)
        self.layout().addWidget(title_label)
        # Job Function
        if function_str := job_data.get("job_function"):
            if function_str != "other":
                function_label = QLabel(f"<i>{function_str}</i>")
                self.layout().addWidget(function_label)
        self.layout().addSpacing(10)
        # Company Name
        company_label = job_data.get("company", "Unknown Company")
        self.layout().addWidget(QLabel(company_label))
        self.layout().addSpacing(10)
        # Location and Work Model
        location_info = QHBoxLayout()
        location_label = QLabel(job_data.get("location", "Unknown Location"))
        location_info.addWidget(location_label)
        remote_label = QLabel("[Remote]" if job_data.get("is_remote", False) else "[On-site]")
        location_info.addWidget(remote_label)
        location_info.addStretch()
        self.layout().addLayout(location_info)
        self.layout().addSpacing(10)
        # Job Type
        if job_type := job_data.get("job_type"):
            type_label = QLabel(f"{job_type.title()}")
            self.layout().addWidget(type_label)
            self.layout().addSpacing(10)
        # Job Level
        if job_level := job_data.get("job_level"):
            if job_level != "not applicable":
                level_label = QLabel(f"{job_level.title()}")
                self.layout().addWidget(level_label)
                self.layout().addSpacing(10)
        # Compensation
        compensation_low = job_data.get("min_amount")
        compensation_high = job_data.get("max_amount")
        if compensation_low and compensation_high:
            compensation_str = f"{compensation_low:,.2f} - {compensation_high:,.2f}"
            compensation_str += f" {job_data.get("currency", "").upper()}"
            if interval := job_data.get("interval"):
                compensation_str += f"/{interval[:-2].replace('dai', 'day').capitalize()}"
            compensation_label = QLabel(compensation_str)
            self.layout().addWidget(compensation_label)
            self.layout().addSpacing(10)
        # Full Description
        if description := job_data.get("description"):
            description_view = QTextEdit(markdown=clean_description(description))
            description_view.setReadOnly(True)
            self.layout().addWidget(description_view)

    def layout(self) -> QVBoxLayout:
        return super().layout()  # type: ignore

    def showEvent(self, event):
        if self.parentWidget() is not None:
            # Set dialog size relative to parent
            scale = 0.9
            width = min(int(self.parentWidget().width() * scale), 800)
            height = int(self.parentWidget().height() * scale)
            self.setFixedSize(width, height)
            # Calculate center coordinates of parent
            par_geo = self.parentWidget().geometry()
            par_pos = self.parentWidget().mapToGlobal(QPoint(0, 0))
            center_x = par_pos.x() + (par_geo.width() // 2)
            center_y = par_pos.y() + (par_geo.height() // 2)
            # Center the dialog relative to parent
            dialog_x = center_x - (width // 2)
            dialog_y = center_y - (height // 2)
            self.move(dialog_x, dialog_y)
        super().showEvent(event)


class CompanyDetails(QDialog):
    """Popup dialog to show detailed company information."""

    def __init__(self, company_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Company Details")
        self.setLayout(QVBoxLayout(self))
        # Links
        links_layout = QHBoxLayout()
        if company_url := company_data.get("company_url"):
            site = company_data.get("site", "Job Board").title()
            company_url_label = QLabel(f'<a href="{company_url}">{site} Page</a>')
            company_url_label.setOpenExternalLinks(True)
            links_layout.addWidget(company_url_label)
        if company_url_direct := company_data.get("company_url_direct"):
            direct_label = QLabel(f'<a href="{company_url_direct}">Company Website</a>')
            direct_label.setOpenExternalLinks(True)
            links_layout.addWidget(direct_label)
        links_layout.addStretch()
        self.layout().addLayout(links_layout)
        self.layout().addSpacing(10)
        # Name and logo
        company_header = QHBoxLayout()
        if logo_url := company_data.get("company_logo"):
            logo_label = QWebImageLabel(logo_url)
            logo_label.setFixedSize(64, 64)
            logo_label.setScaledContents(True)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignBottom)
            company_header.addWidget(logo_label)
        name_label = QLabel(f"<h2>{company_data.get('company', 'Unknown Company')}</h2>")
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignmentFlag.AlignBottom)
        company_header.addWidget(name_label)
        self.layout().addLayout(company_header)
        # Industry
        if industry := company_data.get("company_industry"):
            industry_label = QLabel(f"<i>{industry}</i>")
            industry_label.setWordWrap(True)
            self.layout().addWidget(industry_label)
            self.layout().addSpacing(10)
        # Description
        if description := company_data.get("company_description"):
            description_view = QLabel(description)
            description_view.setWordWrap(True)
            self.layout().addWidget(description_view)
            self.layout().addSpacing(10)
        # Details
        num_employees = company_data.get("company_num_employees")
        revenue = company_data.get("company_revenue")
        if num_employees or revenue:
            if num_employees:
                employees_label = QLabel(f"<b>Employees</b>: {num_employees}")
                self.layout().addWidget(employees_label)
            if revenue:
                revenue_label = QLabel(f"<b>Revenue</b>: {revenue}")
                self.layout().addWidget(revenue_label)
            self.layout().addSpacing(10)
        if addresses := company_data.get("company_addresses"):
            for addr in addresses.splitlines():
                addr_label = QLabel(addr)
                self.layout().addWidget(addr_label)

    def layout(self) -> QVBoxLayout:
        return super().layout()  # type: ignore

    def showEvent(self, event):
        if self.parentWidget() is not None:
            # Set dialog size
            width = 400
            height = self.height()
            self.setFixedSize(width, height)
            # Calculate center coordinates of parent
            par_geo = self.parentWidget().geometry()
            par_pos = self.parentWidget().mapToGlobal(QPoint(0, 0))
            center_x = par_pos.x() + (par_geo.width() // 2)
            center_y = par_pos.y() + (par_geo.height() // 2)
            # Center the dialog relative to parent
            dialog_x = center_x - (width // 2)
            dialog_y = center_y - (height // 2)
            self.move(dialog_x, dialog_y)
        super().showEvent(event)
