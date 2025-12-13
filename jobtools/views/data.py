from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableView, QComboBox, QPushButton, QHeaderView
from .widgets import QHeader
from ..models import ConfigModel, DataModel, SortFilterModel
from ..utils.utils import get_data_sources


DEFAULT_HIDDEN = ['id', 'job_url_direct', 'salary_source', 'interval',
                  'min_amount', 'max_amount', 'currency', 'job_level',
                  'job_function', 'listing_type', 'emails', 'description',
                  'company_industry', 'company_url', 'company_logo',
                  'company_url_direct', 'company_addresses',
                  'company_num_employees', 'company_revenue',
                  'company_description', 'skills', 'experience_range',
                  'company_rating', 'company_reviews_count', 'vacancy_count',
                  'work_from_home_type', 'location', 'city', 'job_url']

DEFAULT_DISPLAY = ['site', 'title', 'company', 'date_posted',
                   'job_type', 'is_remote', 'state', 'has_ba', 'has_ma',
                   'has_phd', 'keyword_score', 'keywords', 'degree_score',
                   'location_score']


class DataPage(QWidget):
    """ Page for displaying collected job data. """

    def __init__(self,
                 config_model: ConfigModel,
                 sort_filter_model: SortFilterModel):
        super().__init__()
        self.setLayout(QVBoxLayout(self))
        self._config_model = config_model
        self._sort_filter_model = sort_filter_model

        # Setup proxy model
        self._sort_filter_model.setSortRole(Qt.ItemDataRole.EditRole)
        self._sort_filter_model.setDynamicSortFilter(True)
        self._sort_filter_model.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive) 
        self._sort_filter_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        # Data source selector
        self.layout().addWidget(QHeader("Data Source"))
        data_selector_layout = QHBoxLayout()
        self.data_selector = QComboBox()
        self.data_selector.setFixedWidth(300)
        data_sources = get_data_sources()
        for name, path in data_sources.items():
            self.data_selector.addItem(name, path)
        self.data_selector.setCurrentIndex(1)
        data_selector_layout.addWidget(self.data_selector)
        self.data_load = QPushButton("Load Data")
        self.data_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.data_load.clicked.connect(self._on_load_data_source)
        data_selector_layout.addWidget(self.data_load)
        data_selector_layout.addStretch()
        self.layout().addLayout(data_selector_layout)

        # Data table view
        self.data_view = QTableView()
        self.data_view.setModel(self._sort_filter_model)
        self.data_view.setSortingEnabled(True)
        self.data_view.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        self.data_view.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.data_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.data_view.verticalHeader().setVisible(False)
        self.data_view.setAlternatingRowColors(True)
        self.data_view.setShowGrid(False)
        self.layout().addWidget(self.data_view)

        # Load data source on startup
        self._on_load_data_source()

    def layout(self) -> QVBoxLayout:
        """ Get layout as QVBoxLayout. """
        return super().layout()  # type: ignore
    
    @Slot(int)
    def _on_load_data_source(self):
        """ Load selected data source into the data model. """
        data_path = self.data_selector.currentData()
        if data_path.exists():
            data_model = DataModel(data_path)
            sort_cfg = self._config_model.get_config_dict().get("sort", {})
            # Calculate score columns
            kw_val_map = {int(terms_key.split("_")[-1]): sort_cfg[terms_key]
                          for terms_key in sort_cfg if terms_key.startswith("terms_selected_")}
            data_model.calc_keyword_score(kw_val_map)
            deg_vals = sort_cfg.get("degree_values", [])
            data_model.calc_degree_score(deg_vals)
            loc_order = sort_cfg.get("location_order_selected", [])
            data_model.calc_location_score(loc_order)
            site_order = sort_cfg.get("sites_selected", [])
            data_model.calc_site_score(site_order)
            # Configure proxy model
            self._sort_filter_model.setSourceModel(data_model)
            self._sort_filter_model.setColumnFilter(DEFAULT_HIDDEN)
            self._sort_filter_model.setSortColumnMap({"state": "location_score",
                                                "keywords": "keyword_score"})
