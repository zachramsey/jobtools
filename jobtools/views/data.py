from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt, QUrl, Slot
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..models import ConfigModel, JobsDataModel
from ..utils import ThemeColor, blend_colors, clean_description, get_data_sources, get_icon
from .widgets import QWebImageLabel

UNUSED_COLUMNS = ["id", "job_url_direct", "salary_source", "interval",
                  "min_amount", "max_amount", "currency", "job_level",
                  "job_function", "listing_type", "emails", "description",
                  "company_industry", "company_url", "company_logo",
                  "company_url_direct", "company_addresses",
                  "company_num_employees", "company_revenue",
                  "company_description", "skills", "experience_range",
                  "company_rating", "company_reviews_count", "vacancy_count",
                  "work_from_home_type", "location", "city"]


class HoverTableView(QTableView):
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        # Find which index the mouse is currently over
        pos = event.position().toPoint()
        index = self.indexAt(pos)
        # Change cursor if hovering over a linkable cell
        if index.isValid() and index.data(Qt.ItemDataRole.UserRole + 1):
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().mouseMoveEvent(event)


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


class DataPage(QWidget):
    """Page for displaying collected job data."""

    def __init__(self,
                 config_model: ConfigModel,
                 data_model: JobsDataModel):
        super().__init__()
        self.setLayout(QVBoxLayout(self))
        self._config_model = config_model
        self._data_model = data_model

        # Initialize data model with dummy data
        self._setup_data_model(self._data_model._foobar_path)
        self._data_model.set_visible_columns([
            "is_favorite", "date_posted", "state", "company", "title",
            "has_ba", "has_ma", "has_phd", "keywords", "site",
        ])
        self._data_model.set_column_labels({
            "is_favorite": "",
            "date_posted": "Date Posted   ",
            "state": "State ",
            "company": "Company ",
            "title": "Title  ",
            "has_ba": "BA ",
            "has_ma": "MA ",
            "has_phd": "PhD"
        })

        # Data source selector
        data_selector_layout = QHBoxLayout()
        self.data_selector = QComboBox()
        self.data_selector.setFixedWidth(300)
        self._special_sources = {
            "Select Data Source...": self._data_model._foobar_path / "jobs_data.csv",
            "Favorites": self._data_model._fav_path / "jobs_data.csv",
            "Archive": self._data_model._arch_path / "jobs_data.csv"
        }
        for name, path in self._special_sources.items():
            self.data_selector.addItem(name, path)
        for name, path in get_data_sources().items():
            self.data_selector.addItem(name, path)
        data_selector_layout.addWidget(self.data_selector)
        self.data_load = QPushButton("Load Data")
        self.data_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.data_load.clicked.connect(self._on_load_data_source)
        data_selector_layout.addWidget(self.data_load)
        self.data_refresh = QPushButton()
        self.data_refresh.setIcon(get_icon("refresh"))
        self.data_refresh.setIconSize(QSize(24, 24))
        self.data_refresh.setStyleSheet("border: none; padding: 5px;")
        self.data_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.data_refresh.setToolTip("Refresh Data Sources")
        self.data_refresh.clicked.connect(self._on_refresh_data_sources)
        data_selector_layout.addWidget(self.data_refresh)
        data_selector_layout.addStretch()
        self.layout().addLayout(data_selector_layout)

        # HACK: This is a stupid workaround to update the data model after collection.
        #       Seems like the data should update automatically, since it is loaded
        #       from the same JobsDataModel instance. Will investigate later.
        self._data_model.collectFinished.connect(self._setup_data_model)

        # Data table view
        self.table_view = HoverTableView()
        self.table_view.setModel(self._data_model)
        # self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        self.table_view.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setProperty("class", "data-table")
        bg_color = blend_colors(ThemeColor.SECONDARY_DARK, ThemeColor.SECONDARY, 0.7)
        alt_color = blend_colors(ThemeColor.SECONDARY_DARK, ThemeColor.SECONDARY_LIGHT, 0.7)
        self.table_view.setStyleSheet(f"QTableView {{ background-color: {bg_color}; \
                                                      alternate-background-color: {alt_color}; }}")
        self.table_view.setShowGrid(False)
        self.table_view.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.table_view.setWordWrap(True)
        self.table_view.clicked.connect(self._on_clickable)
        self.layout().addWidget(self.table_view)

    def layout(self) -> QVBoxLayout:
        """Get layout as QVBoxLayout."""
        return super().layout()  # type: ignore

    def _setup_data_model(self, data_path: Path):
        """Set up the data model from the given data path."""
        self._data_model.load_data(data_path)
        cfg = self._config_model.get_config_dict()
        # Apply current sorting configuration
        sort_cfg = cfg.get("sort", {})
        loc_order = sort_cfg.get("location_order_selected", [])
        deg_vals = sort_cfg.get("degree_values", [])
        kw_val_map = {int(terms_key.split("_")[-1]): sort_cfg[terms_key]
                          for terms_key in sort_cfg if terms_key.startswith("terms_selected_")}
        site_order = sort_cfg.get("sites_selected", [])
        self._data_model.update_rank_order_score("state", loc_order, "location_score")
        self._data_model.update_degree_score(deg_vals)
        self._data_model.update_keyword_score(kw_val_map)
        self._data_model.update_rank_order_score("site", site_order, "site_score")
        self._data_model.standard_ordering()
        # Apply current filter configuration
        filter_cfg = cfg.get("filter", {})
        work_models = filter_cfg.get("work_models", [])
        work_models = [wm.upper() == "remote" for wm in work_models]
        self._data_model.set_filter("work_models", "is_remote", work_models)
        job_types = filter_cfg.get("job_types", [])
        self._data_model.set_filter("job_types", "job_type", job_types)
        title_excl = filter_cfg.get("title_exclude_selected", [])
        self._data_model.set_filter("title_exclude", "title", title_excl, invert=True)
        title_req = filter_cfg.get("title_require_selected", [])
        self._data_model.set_filter("title_require", "title", title_req)
        descr_excl = filter_cfg.get("descr_exclude_selected", [])
        self._data_model.set_filter("descr_exclude", "description", descr_excl, invert=True)
        descr_req = filter_cfg.get("descr_require_selected", [])
        self._data_model.set_filter("descr_require", "description", descr_req)

    @Slot(int)
    def _on_load_data_source(self):
        """Load selected data source into the data model."""
        data_path = self.data_selector.currentData()
        if data_path.exists():
            self._setup_data_model(data_path)

    @Slot()
    def _on_refresh_data_sources(self):
        """Refresh the list of available data sources."""
        current_text = self.data_selector.currentText()
        self.data_selector.clear()
        for name, path in self._special_sources.items():
            self.data_selector.addItem(name, path)
        for name, path in get_data_sources().items():
            self.data_selector.addItem(name, path)
        # Restore previous selection if possible
        index = self.data_selector.findText(current_text)
        if index >= 0:
            self.data_selector.setCurrentIndex(index)

    @Slot()
    def _on_clickable(self, index):
        """Handle clicks on clickable cells."""
        col = self._data_model.columns[index.column()]
        if col == "is_favorite":
            self._data_model.toggle_favorite(index)
        elif col == "company":
            company_data = self._data_model.get_job_data(index)
            details_dialog = CompanyDetails(company_data, parent=self.table_view)
            details_dialog.exec()
        elif col == "title":
            job_data = self._data_model.get_job_data(index)
            details_dialog = JobDetails(job_data, parent=self.table_view)
            details_dialog.exec()
        elif col == "site":
            url = self._data_model.get_index_url(index)
            if url:
                QDesktopServices.openUrl(QUrl(url))
