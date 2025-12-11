import os
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableView, QComboBox, QPushButton
from ..custom_widgets import QHeader
from ..models.config_model import ConfigModel
from ..models.data_model import DataModel
from ..models.sort_filter_model import SortFilterModel
from ..utils import get_data_sources


class DataPage(QWidget):
    """ Page for displaying collected job data. """

    def __init__(self,
                 config_model: ConfigModel,
                 sort_filter_model: SortFilterModel):
        super().__init__()
        self.setLayout(QVBoxLayout(self))
        self._config_model = config_model
        self._proxy_model = sort_filter_model

        # Setup proxy model
        self._proxy_model.setSortRole(Qt.ItemDataRole.EditRole)
        self._proxy_model.setDynamicSortFilter(True)
        self._proxy_model.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive) 
        self._proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy_model.setDisplayColumns(["date_posted", "state", "company",
                                             "title", "has_ba", "has_ma",
                                             "has_phd", "degree_score",
                                             "keywords", "site"])
        self._proxy_model.setSortColumnMap({"date_posted": "date_posted",
                                            "state": "location_score",
                                            "keywords": "keyword_score"})

        # Data source selector
        self.layout().addWidget(QHeader("Data Source"))
        data_selector_layout = QHBoxLayout()
        self.data_selector = QComboBox()
        self.data_selector.setFixedWidth(300)
        data_sources = get_data_sources()
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
        self.data_view = QTableView()
        self.data_view.setModel(self._proxy_model)
        self.data_view.setSortingEnabled(True)
        self.layout().addWidget(self.data_view)

    def layout(self) -> QVBoxLayout:
        """ Get layout as QVBoxLayout. """
        return super().layout()  # type: ignore
    
    @Slot(int)
    def _on_load_data_source(self):
        """ Load selected data source into the data model. """
        # index = self.data_selector.currentIndex()
        # data_path = self.data_selector.itemData(index)
        data_path = self.data_selector.currentData()
        if isinstance(data_path, str) and os.path.exists(data_path):
            data_model = DataModel(data_path)
            sort_cfg = self._config_model.get_config_dict().get("sort", {})
            # Calculate keyword scores
            kw_val_map = {int(terms_key.split("_")[-1]): sort_cfg[terms_key]
                          for terms_key in sort_cfg if terms_key.startswith("terms_selected_")}
            data_model.calc_keyword_score(kw_val_map)
            # Calculate degree scores
            deg_vals = sort_cfg.get("degree_values", [])
            data_model.calc_degree_score(deg_vals)
            # Calculate location scores
            loc_order = sort_cfg.get("location_order_selected", [])
            data_model.calc_location_score(loc_order)
            # Update proxy model
            self._proxy_model.setSourceModel(data_model)
            self.data_view.resizeColumnsToContents()
