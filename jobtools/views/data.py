from pathlib import Path
from PySide6.QtCore import Qt, Slot, QUrl
from PySide6.QtGui import QDesktopServices, QCursor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QTableView, QComboBox, QPushButton,
                               QHeaderView)
from .widgets import QHeader
from ..models import ConfigModel, JobsDataModel
from ..utils import get_data_dir, get_data_sources, ThemeColor, blend_colors


UNUSED_COLUMNS = ['id', 'job_url_direct', 'salary_source', 'interval',
                  'min_amount', 'max_amount', 'currency', 'job_level',
                  'job_function', 'listing_type', 'emails', 'description',
                  'company_industry', 'company_url', 'company_logo',
                  'company_url_direct', 'company_addresses',
                  'company_num_employees', 'company_revenue',
                  'company_description', 'skills', 'experience_range',
                  'company_rating', 'company_reviews_count', 'vacancy_count',
                  'work_from_home_type', 'location', 'city']


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


class DataPage(QWidget):
    """ Page for displaying collected job data. """

    def __init__(self,
                 config_model: ConfigModel,
                 data_model: JobsDataModel):
        super().__init__()
        self.setLayout(QVBoxLayout(self))
        self._config_model = config_model
        self._data_model = data_model

        # Initialize data model with dummy data
        self._setup_data_model(get_data_dir() / "dummy_jobs_data.csv")
        self._data_model.set_visible_columns([
            "date_posted", "state", "company", "title",
            "has_ba", "has_ma", "has_phd", "keywords","site", 
        ])
        self._data_model.set_column_labels({
            "date_posted": "Posted", "state": "Loc",
            "has_ba": "BA", "has_ma": "MA", "has_phd": "PhD"
        })

        # Data source selector
        self.layout().addWidget(QHeader("Data Source"))
        data_selector_layout = QHBoxLayout()
        self.data_selector = QComboBox()
        self.data_selector.setFixedWidth(300)
        data_sources = get_data_sources()
        self.data_selector.addItem("Select Data Source...", Path())
        for name, path in data_sources.items():
            self.data_selector.addItem(name, path)
        data_selector_layout.addWidget(self.data_selector)
        self.data_load = QPushButton("Load Data")
        self.data_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.data_load.clicked.connect(self._on_load_data_source)
        data_selector_layout.addWidget(self.data_load)
        data_selector_layout.addStretch()
        self.layout().addLayout(data_selector_layout)

        # Data table view
        self.table_view = HoverTableView()
        self.table_view.setModel(self._data_model)
        # self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        self.table_view.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setProperty("class", "data-table")
        self.table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setAlternatingRowColors(True)
        bg_color = blend_colors(ThemeColor.SECONDARY_DARK, ThemeColor.SECONDARY, 0.7)
        alt_color = blend_colors(ThemeColor.SECONDARY_DARK, ThemeColor.SECONDARY_LIGHT, 0.7)
        self.table_view.setProperty("class", "data-table")
        self.table_view.setStyleSheet(f"QTableView {{ background-color: {bg_color}; alternate-background-color: {alt_color}; }}")
        self.table_view.setShowGrid(False)
        self.table_view.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.table_view.setWordWrap(True)
        self.table_view.clicked.connect(self._on_open_job_url)
        self.layout().addWidget(self.table_view)

    def layout(self) -> QVBoxLayout:
        """ Get layout as QVBoxLayout. """
        return super().layout()  # type: ignore
    
    def _setup_data_model(self, data_path: Path):
        """ Setup the data model from the given data path. """
        self._data_model.load_data(data_path)
        cfg = self._config_model.get_config_dict()
        # Apply current sorting configuration
        sort_cfg = cfg.get("sort", {})
        loc_order = sort_cfg.get("location_order_selected", [])
        deg_vals = sort_cfg.get("degree_values", [])
        kw_val_map = {int(terms_key.split("_")[-1]): sort_cfg[terms_key]
                          for terms_key in sort_cfg if terms_key.startswith("terms_selected_")}
        site_order = sort_cfg.get("sites_selected", [])
        self._data_model.prioritize(loc_order, deg_vals, kw_val_map,
                                    site_order, drop_intermediate=False)
        # Apply current filter configuration
        filter_cfg = cfg.get("filter", {})
        work_models = filter_cfg.get("work_models", [])
        work_models = [wm.upper() == "remote" for wm in work_models]
        self._data_model.filter_data("is_remote", work_models)
        job_types = filter_cfg.get("job_types", [])
        self._data_model.filter_data("job_type", job_types)
        title_excl = filter_cfg.get("title_exclude_selected", [])
        self._data_model.filter_data("title", title_excl, invert=True)
        title_req = filter_cfg.get("title_require_selected", [])
        self._data_model.filter_data("title", title_req)
        descr_excl = filter_cfg.get("descr_exclude_selected", [])
        self._data_model.filter_data("description", descr_excl, invert=True)
        descr_req = filter_cfg.get("descr_require_selected", [])
        self._data_model.filter_data("description", descr_req)

    @Slot(int)
    def _on_load_data_source(self):
        """ Load selected data source into the data model. """
        data_path = self.data_selector.currentData()
        if data_path.exists():
            self._setup_data_model(data_path)

    @Slot()
    def _on_open_job_url(self, index):
        """ Open the job posting URL for the given model index. """
        url = self._data_model.get_index_url(index)
        if url:
            QDesktopServices.openUrl(QUrl(url))
            