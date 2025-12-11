from PySide6.QtCore import QSortFilterProxyModel, Qt
import re
from ...utils.patterns import build_regex


class SortFilterModel(QSortFilterProxyModel):
    """ A proxy model for sorting and filtering job val. """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hidden_columns = set()
        self._sort_column_map = {}
        self._filters = {}

    def setHiddenColumns(self, columns: list[str]):
        """ Set the columns to be hidden in the view.

        Parameters
        ----------
        columns : list[str]
            List of column names to hide.
        """
        self._hidden_columns.clear()
        for col_name in columns:
            col_idx = self.sourceModel().columnIndex(col_name)  # type: ignore
            if col_idx != -1:
                self._hidden_columns.add(col_idx)

    def setDisplayColumns(self, columns: list[str]):
        """ Set the columns to be displayed in the view.

        Parameters
        ----------
        columns : list[str]
            List of column names to display.

        Notes
        -----
        Sets hidden columns by exclusion from the full set of columns.  
        See also: `setHiddenColumns`.
        """
        all_columns = set(range(self.sourceModel().columnCount(None)))  # type: ignore
        self._hidden_columns = all_columns
        for col_name in columns:
            col_idx = self.sourceModel().columnIndex(col_name)  # type: ignore
            if col_idx != -1 and col_idx in self._hidden_columns:
                self._hidden_columns.remove(col_idx)

    def update_kw_score(self, keyword_value_map: dict[int, list[str]]):
        """ Update keyword score in the source model. """
        self.sourceModel().calc_keyword_score(keyword_value_map)  # type: ignore

    def update_degree_score(self, degree_values: tuple[int, int, int]):
        """ Update degree score in the source model. """
        self.sourceModel().calc_degree_score(degree_values)  # type: ignore

    def update_location_score(self, location_order: list[str]):
        """ Update location score in the source model. """
        self.sourceModel().calc_location_score(location_order)  # type: ignore

    def setSortColumnMap(self, column_map: dict[str, str]):
        """ Set the mapping between displayed column
        and their corresponding sorting key column.

        Parameters
        ----------
        column_map : dict[str, str]
            Dictionary mapping view column names to key column names.
        """
        self._sort_column_map.clear()
        for view_col, key_col in column_map.items():
            view_idx = self.sourceModel().columnIndex(view_col) # type: ignore
            key_idx = self.sourceModel().columnIndex(key_col)   # type: ignore
            if view_idx != -1 and key_idx != -1:
                self._sort_column_map[view_idx] = key_idx

    def setFilter(self, column: str, filter_type: str, filter_value, invert: bool = False):
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
        col_idx = self.sourceModel().columnIndex(column)        # type: ignore
        if col_idx != -1:
            if filter_type == "regex" and isinstance(filter_value, list):
                filter_value = build_regex(filter_value)
            self._filters[col_idx] = (filter_type, filter_value, invert)
            self.invalidateFilter()

    def removeFilter(self, column: str):
        """ Remove the filter for a specific column.

        Parameters
        ----------
        column : str
            The name of the column to remove the filter from.
        """
        col_idx = self.sourceModel().columnIndex(column)        # type: ignore
        if col_idx != -1 and col_idx in self._filters:
            del self._filters[col_idx]
            self.invalidateFilter()

    def filterAcceptsColumn(self, source_column: int, source_parent) -> bool:
        if source_column in self._hidden_columns:
            return False
        return True
    
    def lessThan(self, left, right) -> bool:
        if left.column() in self._sort_column_map:
            # Handle key-based sorting
            key_column = self._sort_column_map[left.column()]
            left_key = left.siblingAtColumn(key_column)
            right_key = right.siblingAtColumn(key_column)
            left_val = self.sourceModel().data(left_key, Qt.ItemDataRole.EditRole)
            right_val = self.sourceModel().data(right_key, Qt.ItemDataRole.EditRole)
            return left_val < right_val
        return super().lessThan(left, right)

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        if not self._filters:
            return True
        source_model = self.sourceModel()
        for col_idx, (filter_type, filter_val, invert) in self._filters.items():
            idx = source_model.index(source_row, col_idx, source_parent)
            val = source_model.data(idx, Qt.ItemDataRole.EditRole)
            result = False
            try:
                if filter_type == "regex":
                    result = re.search(str(filter_val), str(val),
                                       re.IGNORECASE) is not None
                elif filter_type == "range":
                    min_val, max_val = filter_val
                    result = min_val <= float(val) <= max_val
                elif filter_type == "exact":
                    result = val == filter_val
                return not result if invert else result
            except Exception:
                return False
        return True
