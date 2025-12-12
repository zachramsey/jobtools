from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from ...jobsdata import JobsData


class DataModel(QAbstractTableModel):
    """ Table model for displaying collected job data. """
    
    def __init__(self, jobs_data: JobsData|str = JobsData()):
        """ Initialize the data model with job data from CSV file. """
        super().__init__()
        if isinstance(jobs_data, JobsData):
            self._jobs = jobs_data
        elif isinstance(jobs_data, str):
            self._jobs = JobsData.from_csv(jobs_data)

    @property
    def columns(self) -> list[str]:
        return self._jobs._df.columns.tolist()  # type: ignore
        
    def rowCount(self, parent=QModelIndex()) -> int:
        return self._jobs._df.shape[0]
    
    def columnCount(self, parent=QModelIndex()) -> int:
        return self._jobs._df.shape[1]
    
    def columnIndex(self, column_name: str) -> int:
        return int(self._jobs._df.columns.get_loc(column_name))  # type: ignore
    
    def data(self, index, role):
        if index.isValid():
            val = self._jobs._df.iloc[index.row(), index.column()]
            try:
                val = val.item()
            except AttributeError:
                pass
            if role == Qt.ItemDataRole.DisplayRole:
                return str(val)
            elif role == Qt.ItemDataRole.EditRole:
                return val
        return None
    
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._jobs._df.columns[section])
            # elif orientation == Qt.Orientation.Vertical:
            #     return str(self._jobs._df.index[section])
        return None
    
    def calc_keyword_score(self, keyword_value_map: dict[int, list[str]]):
        """ Calculate keyword scores based on the provided mapping.
        Add resulting 'keyword_score' and 'keywords' columns to the data. """
        self._jobs["keyword_score"], self._jobs["keywords"] = \
            self._jobs.keyword_score(keyword_value_map)

    def calc_degree_score(self, degree_values: tuple[int, int, int]):
        """ Calculate degree scores based on the provided values.
        Add resulting 'degree_score' column to the data. """
        self._jobs["degree_score"] = \
            self._jobs.degree_score(degree_values)

    def calc_location_score(self, location_order: list[str]):
        """ Calculate location scores based on the provided order.
        Add resulting 'location_score' column to the data. """
        self._jobs["location_score"] = \
            self._jobs.rank_order_score("state", location_order)
        
    def calc_site_score(self, site_order: list[str]):
        """ Calculate site scores based on the provided order.
        Add resulting 'site_score' column to the data. """
        self._jobs["site_score"] = \
            self._jobs.rank_order_score("site", site_order)
