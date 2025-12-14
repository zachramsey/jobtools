from pathlib import Path
from PySide6.QtCore import Qt, Slot, QUrl
from PySide6.QtGui import QPalette, QDesktopServices
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QTableView, QComboBox, QPushButton,
                               QHeaderView, QStyledItemDelegate)
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


class HyperlinkDelegate(QStyledItemDelegate):
    """ Delegate to render clickable hyperlinks in a QTableView. """

    def paint(self, painter, option, index):
        """ Paint the cell with hyperlink style. """
        painter.save()
        url = index.data(Qt.ItemDataRole.UserRole + 1)
        if url:
            option.font.setUnderline(True)
            link_color = option.palette.color(QPalette.ColorRole.Link)
            painter.setPen(link_color)
            painter.setFont(option.font)
            painter.drawText(
                option.rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                index.data()
            )
        else:
            super().paint(painter, option, index)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        """ Handle click events to open hyperlinks. """
        if event.type() == event.Type.MouseButtonRelease:
            url = index.data(Qt.ItemDataRole.UserRole + 1)
            if url:
                QDesktopServices.openUrl(QUrl(url))
                return True
        return super().editorEvent(event, model, option, index)


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
        self.table_view = QTableView()
        self.table_view.setModel(self._data_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        self.table_view.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setAlternatingRowColors(True)
        bg_color = blend_colors(ThemeColor.SECONDARY_DARK, ThemeColor.SECONDARY, 0.7)
        alt_color = blend_colors(ThemeColor.SECONDARY_DARK, ThemeColor.SECONDARY_LIGHT, 0.7)
        self.table_view.setStyleSheet(f"QTableView {{ background-color: {bg_color}; alternate-background-color: {alt_color}; }}")
        self.table_view.setShowGrid(False)
        self.table_view.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.table_view.setItemDelegateForColumn(self._data_model.columnIndex("site"),  # type: ignore
                                                 HyperlinkDelegate(self.table_view))
        self.layout().addWidget(self.table_view)

    def layout(self) -> QVBoxLayout:
        """ Get layout as QVBoxLayout. """
        return super().layout()  # type: ignore
    
    def _setup_data_model(self, data_path: Path):
        """ Setup the data model from the given data path. """
        self._data_model = JobsDataModel(data_path)
        sort_cfg = self._config_model.get_config_dict().get("sort", {})
        loc_order = sort_cfg.get("location_order_selected", [])
        deg_vals = sort_cfg.get("degree_values", [])
        kw_val_map = {int(terms_key.split("_")[-1]): sort_cfg[terms_key]
                          for terms_key in sort_cfg if terms_key.startswith("terms_selected_")}
        site_order = sort_cfg.get("sites_selected", [])
        self._data_model.prioritize(loc_order, deg_vals, kw_val_map,
                                    site_order, drop_intermediate=False)

    @Slot(int)
    def _on_load_data_source(self):
        """ Load selected data source into the data model. """
        data_path = self.data_selector.currentData()
        if data_path.exists():
            self._setup_data_model(data_path)
            