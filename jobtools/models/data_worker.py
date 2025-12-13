from PySide6.QtCore import QObject, Signal, Slot, QThread
from threading import Event
import traceback
from typing import Callable
from ..jobsdata import JobsData


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


def collect_jobs(config: dict,
                 finished_callback: Callable,
                 error_callback: Callable) -> Event:
    """ Start job data collection in a separate thread.

    Parameters
    ----------
    config : dict
        Configuration dictionary for job data collection.
    finished_callback : Callable
        Callback function to be called upon completion.
    error_callback : Callable
        Callback function to be called in case of an error.

    Returns
    -------
    Event
        Event object to signal cancellation of the job data collection process.
    """
    jobs_data = JobsData()
    cancel_event = Event()
    worker = CollectionWorker(jobs_data, config, cancel_event)
    # Move worker to a separate thread
    worker_thread = QThread()
    worker.moveToThread(worker_thread)
    # Connect signals and slots
    worker_thread.started.connect(worker.run)
    worker_thread.finished.connect(worker_thread.deleteLater)
    worker.finished.connect(worker_thread.quit)
    worker.finished.connect(worker.deleteLater)
    # Connect worker signals to callbacks
    worker.finished.connect(finished_callback)
    worker.error.connect(error_callback)
    # Start thread
    worker_thread.start()
    return cancel_event


# class CalculationWorker(QObject):
#     """ Worker for running calculations in a separate thread. """

#     finished = Signal(object)
#     error = Signal(str)

#     def __init__(self, calc_func: Callable, *args, **kwargs):
#         super().__init__()
#         self._calc_func = calc_func
#         self._args = args
#         self._kwargs = kwargs

#     @Slot()
#     def run(self):
#         """ Run the calculation.

#         Yields
#         ------
#         finished : None
#             Emitted upon completion of the calculation.
#         error : str
#             Emitted with the error message if an exception occurs.
#         """
#         try:
#             result = self._calc_func(*self._args, **self._kwargs)
#             self.finished.emit(result)
#         except Exception:
#             self.error.emit(traceback.format_exc())


# def run_calculation(finished_callback: Callable,
#                    error_callback: Callable,
#                    calc_func: Callable,
#                    *args, **kwargs):
#     """ Start a calculation in a separate thread.

#     Parameters
#     ----------
#     finished_callback : Callable
#         Callback function to be called upon completion.
#     error_callback : Callable
#         Callback function to be called in case of an error.
#     calc_func : Callable
#         The function to be executed for the calculation.
#     *args : tuple
#         Positional arguments for the calculation function.
#     **kwargs : dict
#         Keyword arguments for the calculation function.
#     """
#     worker = CalculationWorker(calc_func, *args, **kwargs)
#     # Move worker to a separate thread
#     worker_thread = QThread()
#     worker.moveToThread(worker_thread)
#     # Connect signals and slots
#     worker_thread.started.connect(worker.run)
#     worker_thread.finished.connect(worker_thread.deleteLater)
#     worker.finished.connect(worker_thread.quit)
#     worker.finished.connect(worker.deleteLater)
#     # Connect worker signals to callbacks
#     worker.finished.connect(finished_callback)
#     worker.error.connect(error_callback)
#     # Start thread
#     worker_thread.start()
