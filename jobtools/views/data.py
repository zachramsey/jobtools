from PySide6.QtCore import QModelIndex, QSize, Qt, QUrl, Slot
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..models import ConfigModel, JobsDataModel
from ..utils import ThemeColor, blend_colors, get_icon
from .details import CompanyDetails, JobDetails


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
    """Page for displaying collected job data."""

    def __init__(self,
                 config_model: ConfigModel,
                 data_model: JobsDataModel):
        super().__init__()
        self._cfg_model = config_model
        self._data_model = data_model
        defaults: dict = {}

        self.setLayout(QVBoxLayout(self))
        self.layout().setSpacing(10)

        # Configure data model
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

        # Controls layout
        data_control_layout = QHBoxLayout()

        self.data_refresh = QPushButton()
        self.data_refresh.setIcon(get_icon("refresh"))
        self.data_refresh.setIconSize(QSize(24, 24))
        self.data_refresh.setStyleSheet("border: none; padding: 5px;")
        self.data_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.data_refresh.setToolTip("Refresh Data Sources")
        self.data_refresh.clicked.connect(self._data_model.update_filters)
        data_control_layout.addWidget(self.data_refresh)

        self.toggle_favorites = QCheckBox("Favorites")
        data_control_layout.addWidget(self.toggle_favorites)
        defaults["display_favorites"] = False
        data_control_layout.addStretch()
        self.layout().addLayout(data_control_layout)

        # Data table view
        self.table_view = HoverTableView()
        self.table_view.setModel(self._data_model)

        # self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setStyleSheet("QTableView::item { padding: 5px; }")
        self.table_view.horizontalHeader().setStyleSheet("""
            QHeaderView { font-weight: bold; }
            QHeaderView::section { padding-left: 10px; padding-right: 10px; }
        """)
        bg_color = blend_colors(ThemeColor.SECONDARY_DARK, ThemeColor.SECONDARY, 0.7)
        alt_color = blend_colors(ThemeColor.SECONDARY_DARK, ThemeColor.SECONDARY_LIGHT, 0.7)
        self.table_view.setStyleSheet(f"QTableView {{ background-color: {bg_color}; \
                                                      alternate-background-color: {alt_color}; }}")
        self.table_view.setShowGrid(False)
        self.table_view.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.table_view.setWordWrap(True)
        self.table_view.clicked.connect(self._on_clickable)
        self.layout().addWidget(self.table_view)

        # Register page with config model
        self._cfg_model.register_page("data", defaults)

        # Connect view to config model
        self.toggle_favorites.stateChanged.connect(
            lambda state: self._update_config("display_favorites", bool(state)))

        # Connect config model to view updates
        self._cfg_model.dataChanged.connect(self._on_config_changed)

    def layout(self) -> QVBoxLayout:
        """Get layout as QVBoxLayout."""
        return super().layout()  # type: ignore

    def _update_config(self, key: str, value):
        """Update model data from view changes."""
        if key in self._cfg_model.idcs:
            self._cfg_model.setData(self._cfg_model.idcs[key], value, Qt.ItemDataRole.EditRole)

    @Slot(QModelIndex)
    def _on_clickable(self, index):
        """Handle clicks on clickable cells."""
        col = self._data_model.columns[index.column()]
        if col == "is_favorite":
            self._data_model.toggle_favorite(index)
        elif col == "company":
            company_data = self._data_model.get_company_data(index)
            details_dialog = CompanyDetails(company_data, parent=self.table_view)
            details_dialog.exec()
        elif col == "title":
            job_data = self._data_model.get_job_data(index)
            details_dialog = JobDetails(job_data, parent=self.table_view)
            details_dialog.exec()
        elif col == "site":
            url = self._data_model.get_job_data(index).get("job_url", "")
            if url:
                QDesktopServices.openUrl(QUrl(url))

    @Slot(QModelIndex, QModelIndex)
    def _on_config_changed(self, top_left: QModelIndex, bottom_right: QModelIndex):
        """Update data model when config model changes."""
        # Favorites filter
        val = self._cfg_model.get_value("display_favorites", top_left)
        if val is not None and val != self.toggle_favorites.isChecked():
            self.toggle_favorites.setChecked(val)
