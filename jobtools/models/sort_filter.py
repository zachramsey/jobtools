from PySide6.QtCore import QSortFilterProxyModel, Qt
import re
from ..utils import build_regex


class SortFilterModel(QSortFilterProxyModel):
    """ A proxy model for sorting and filtering job val. """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._col_filters = set()
        self._sort_key_map = {}
        self._row_filters = {}

    #####################
    ##  Column Filters ##
    #####################

    def setColumnFilter(self, columns: list[str]):
        """ Set columns to be hidden in the view.

        Parameters
        ----------
        columns : list[str]
            List of column names to hide.
        """
        if self.sourceModel():
            for col in columns:
                if col in self.sourceModel().columns:  # type: ignore
                    col_idx = self.sourceModel().columnIndex(col)  # type: ignore
                    self._col_filters.add(col_idx)
        self.invalidateFilter()

    def clearColumnFilters(self):
        """ Clear all hidden columns. """
        self._col_filters.clear()
        self.invalidateFilter()

    def filterAcceptsColumn(self, source_column: int, source_parent) -> bool:
        if self._col_filters:
            is_filter = source_column in self._col_filters
            is_key = source_column in self._sort_key_map.values()
            return not (is_filter or is_key)
        return True
    
    #####################
    ##   Row Filters   ##
    #####################

    def setRowFilter(self, column: str, filter_type: str, filter_value, invert: bool = False):
        """ Add or update a filter for a specific column.

        Parameters
        ----------
        column : str
            The name of the column to filter.
        filter_type : str
            The type of filter (`regex`, `range`, `exact`).
        filter_value : str | tuple
            The value for the filter.
            - For `regex`, a string pattern or list of patterns.
            - For `range`, a tuple of (min, max).
            - For `exact`, the exact value to match.
        invert : bool, optional
            Whether to invert the filter logic. Default is False.
        """
        if filter_type == "regex" and isinstance(filter_value, list):
            filter_value = build_regex(filter_value)
        if not self.sourceModel():
            return
        col_idx = self.sourceModel().columnIndex(column)  # type: ignore
        # HACK: Use negative index for inverted filters;
        #       doesn't work with 0, but that's just col `id`
        col_idx *= 1 - (2 * int(invert))
        _filter = (filter_type, filter_value)
        if self._row_filters.get(col_idx) == _filter:
            return
        self._row_filters[col_idx] = _filter
        self.invalidateFilter()

    def removeRowFilter(self, column: str):
        """ Remove the filter for a specific column.

        Parameters
        ----------
        column : str
            The name of the column to remove the filter from.
        """
        if column in self._row_filters:
            col_idx = self.sourceModel().columnIndex(column)  # type: ignore
            del self._row_filters[col_idx]
            self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        for col_idx, (filter_type, filter_val) in self._row_filters.items():
            cell_idx = self.sourceModel().index(source_row, abs(col_idx), source_parent)
            cell_val = self.sourceModel().data(cell_idx, Qt.ItemDataRole.EditRole)
            if filter_type == "regex":
                accepts = bool(re.search(str(filter_val), str(cell_val), re.IGNORECASE))
            elif filter_type == "range":
                accepts = filter_val[0] <= float(cell_val) <= filter_val[1]
            elif filter_type == "exact":
                if not isinstance(filter_val, list):
                    filter_val = [filter_val]
                accepts = cell_val in filter_val
            if col_idx < 0:
                accepts = not accepts
            if not accepts:
                return False
        return True
    
    #####################
    ##     Sorting     ##
    #####################
    
    def setSortColumnMap(self, column_map: dict[str, str]):
        """ Set the mapping between displayed column
        and their corresponding sorting key column.

        Parameters
        ----------
        column_map : dict[str, str]
            Dictionary mapping view column names to key column names.
        """
        self._sort_key_map.clear()
        for view_col_name, key_col_name in column_map.items():
            view_col_idx = self.sourceModel().columnIndex(view_col_name) # type: ignore
            key_col_idx = self.sourceModel().columnIndex(key_col_name)   # type: ignore
            self._sort_key_map[view_col_idx] = key_col_idx
    
    def lessThan(self, left, right) -> bool:
        left_col = left.column()
        if left_col in self._sort_key_map:
            # Use the corresponding key column for sorting
            key_col = self._sort_key_map[left_col]
            left = left.siblingAtColumn(key_col)
            right = right.siblingAtColumn(key_col)
        try:
            # Try to use the data value for sorting
            left_val = self.sourceModel().data(left, Qt.ItemDataRole.EditRole)
            right_val = self.sourceModel().data(right, Qt.ItemDataRole.EditRole)
            return left_val < right_val
        except Exception:
            # Fallback to display value if data value comparison fails
            left_val = self.sourceModel().data(left, Qt.ItemDataRole.DisplayRole)
            right_val = self.sourceModel().data(right, Qt.ItemDataRole.DisplayRole)
            return left_val < right_val

    def update_keyword_sort(self, kw_value_map: dict[int, list[str]]):
        """ Update keyword score in the source model. """
        self.sourceModel().keyword_score(               # type: ignore
            kw_value_map, inplace=True)
        self.sourceModel().standard_ordering()          # type: ignore

    def update_degree_sort(self, degree_values: tuple[int, int, int]):
        """ Update degree score in the source model. """
        self.sourceModel().degree_score(                # type: ignore
            degree_values, inplace=True)
        self.sourceModel().standard_ordering()          # type: ignore

    def update_location_sort(self, location_order: list[str]):
        """ Update location score in the source model. """
        self.sourceModel().rank_order_score(            # type: ignore
            "state", location_order, "location_score")
        self.sourceModel().standard_ordering()          # type: ignore

    def update_site_sort(self, site_order: list[str]):
        """ Update site score in the source model. """
        self.sourceModel().rank_order_score(            # type: ignore
            "site", site_order, "site_score")
        self.sourceModel().standard_ordering()          # type: ignore
