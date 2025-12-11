from PySide6.QtCore import QAbstractTableModel, Qt, QObject, QThread, Signal, Slot
from threading import Event
import traceback
from ...jobsdata import JobsData


class CollectionWorker(QObject):
    """ Worker for running job data collection in a separate thread. """

    finished = Signal(str)
    error = Signal(str)

    def __init__(self, jobs_data: JobsData, config: dict, cancel_event: Event):
        super().__init__()
        self._jobs_data = jobs_data
        self._config = config.get("collect", {})
        self._cancel_event = cancel_event

    @Slot()
    def run(self):
        """ Run the job data collection process.

        Yields
        ------
        finished : str
            Emitted with the path to the generated CSV file upon completion.
        error : str
            Emitted with the error message if an exception occurs.
        """
        try:
            # Initialize JobsData
            self._jobs_data = self._jobs_data.from_csv(self._config.get("data_source", ""))
            self._jobs_data.logger.info("Starting job collection...")
            # Run collection and sorting for each query
            for query in self._config.get("queries", []):
                # Job collection
                _ = self._jobs_data.collect(
                    site_name=self._config.get("sites_selected", []),
                    search_term=query,
                    job_type=None,  # type: ignore
                    locations=self._config.get("locations_selected", []),
                    results_wanted=10000, # TODO: Make arbitrarily large "maximum" value configurable
                    proxy=self._config.get("proxy", ""),
                    hours_old=self._config.get("hours_old", 0),
                    cancel_event=self._cancel_event
                )
                # Check for cancellation
                if self._cancel_event and self._cancel_event.is_set():
                    self._jobs_data.logger.info("Job collection cancelled by user.")
                    break
                # Remove trivial duplicates
                self._jobs_data.deduplicate()
                # Save intermediate CSV
                csv_path = self._jobs_data.export_csv()
            if self._cancel_event and self._cancel_event.is_set():
                # Skip further processing if cancelled
                self.finished.emit("")
                return
            self.finished.emit(csv_path)
        except Exception:
            self.error.emit(traceback.format_exc())


class DataModel(QAbstractTableModel):
    """ Table model for displaying collected job data. """

    _worker: CollectionWorker
    """ Worker instance for job data collection. """
    _worker_thread: QThread
    """ QThread instance for running the worker. """
    _cancel_event: Event
    """ Event instance for cancelling the worker. """
    
    def __init__(self, jobs_data: JobsData|str = JobsData()):
        """ Initialize the data model with job data from CSV file. """
        super().__init__()
        if isinstance(jobs_data, JobsData):
            self._jobs_data = jobs_data
        elif isinstance(jobs_data, str):
            self._jobs_data = JobsData.from_csv(jobs_data)

    @property
    def jobs_data(self) -> JobsData:
        """ JobsData instance containing collected job data. """
        return self._jobs_data

    # --- QAbstractTableModel methods ---

    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self._jobs_data.data.iat[index.row(), index.column()])
        
    def rowCount(self, index):
        return self._jobs_data.data.shape[0]
    
    def columnCount(self, index):
        return self._jobs_data.data.shape[1]
    
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._jobs_data.data.columns[section])
            elif orientation == Qt.Orientation.Vertical:
                return str(self._jobs_data.data.index[section])

    def columnIndex(self, column_name: str) -> int:
        """ Get the index of a column by its name.

        Parameters
        ----------
        column_name : str
            The name of the column.

        Returns
        -------
        int
            The index of the column, or -1 if not found.
        """
        try:
            return self._jobs_data.data.columns.get_loc(column_name) # type: ignore
        except KeyError:
            return -1

    # --- Job data collection and processing ---

    @property
    def worker(self) -> CollectionWorker:
        """ Worker instance for job data collection. """
        return self._worker
    
    @property
    def worker_thread(self) -> QThread:
        """ QThread instance for running the worker. """
        return self._worker_thread
    
    @property
    def cancel_event(self) -> Event:
        """ Event instance for cancelling the worker. """
        return self._cancel_event
    
    def clear_cancel_event(self):
        """ Clear the cancel event reference. """
        self._cancel_event = None

    @classmethod
    def setup_collection(cls, config: dict) -> 'DataModel':
        """ Set up job data collection worker.

        Parameters
        ----------
        config : dict
            Configuration dictionary for job collection.

        Returns
        -------
        JobsDataController
            Configured JobsDataController instance.
        """
        # Initialize controller
        ctrl = cls()
        # Set up worker
        ctrl._cancel_event = Event()
        ctrl._worker = CollectionWorker(ctrl._jobs_data, config, ctrl._cancel_event)
        # Move worker to a separate thread
        ctrl._worker_thread = QThread()
        ctrl._worker.moveToThread(ctrl._worker_thread)
        # Connect signals and slots
        ctrl._worker_thread.started.connect(ctrl._worker.run)
        ctrl._worker_thread.finished.connect(ctrl._worker_thread.deleteLater)
        ctrl._worker.finished.connect(ctrl._worker_thread.quit)
        ctrl._worker.finished.connect(ctrl._worker.deleteLater)
        return ctrl
    
    def calc_keyword_score(self, keyword_value_map: dict[int, list[str]]):
        """ Calculate keyword scores based on the provided mapping.
        Add resulting 'keyword_score' and 'keywords' columns to the data. """
        self._jobs_data["keyword_score"], self._jobs_data["keywords"] = \
            self._jobs_data.keyword_score(keyword_value_map)

    def calc_degree_score(self, degree_values: tuple[int, int, int]):
        """ Calculate degree scores based on the provided values.
        Add resulting 'degree_score' column to the data. """
        self._jobs_data["degree_score"] = \
            self._jobs_data.degree_score(degree_values)

    def calc_location_score(self, location_order: list[str]):
        """ Calculate location scores based on the provided order.
        Add resulting 'location_score' column to the data. """
        self._jobs_data["location_score"] = \
            self._jobs_data.rank_order_score("state", location_order)
