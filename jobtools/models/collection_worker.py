import datetime as dt
import threading
import time
import traceback

import pandas as pd  # type: ignore
from jobspy import scrape_jobs  # type: ignore
from PySide6.QtCore import QObject, Signal, Slot
from requests.exceptions import RequestException  # type: ignore
from urllib3.exceptions import HTTPError

from . import ConfigModel, JobsDataModel


class CollectionWorker(QObject):
    """Worker for running job data collection in a separate thread."""

    finished = Signal(pd.DataFrame)
    error = Signal(str)

    def __init__(self, config_model: ConfigModel, cancel_event: threading.Event):
        super().__init__()
        self.data = pd.DataFrame()

        self.queries = config_model.get_value("queries") or None
        self.locations = config_model.get_value("locations_selected") or None
        self.sites = config_model.get_value("sites_selected") or None
        self.hours_old = config_model.get_value("hours_old") or None
        self.proxy = config_model.get_value("proxy") or None

        self.cancel_event = cancel_event

        self.max_retries = 3        # Maximum number of retries for failed requests
        self.backoff_base = 1.0     # Base delay in seconds for exponential backoff

    @staticmethod
    def get_elapsed(start, end) -> str:
        """Get formatted time difference between two timestamps."""
        return str(dt.timedelta(seconds=(end - start))).split(".")[0][-5:]

    @Slot()
    def run(self):
        """Run the job data collection process.

        Yields
        ------
        finished : str
            Emitted with the path to the generated CSV file upon completion.
        error : str
            Emitted with the error message if an exception occurs.
        """
        try:
            t_init = time.time()
            # Signal that collection has started
            JobsDataModel.logger.info("Starting job collection...")
            # Run collection
            for i_qry, query in enumerate(self.queries):
                for i_loc, location in enumerate(self.locations):
                    t_start = time.time()
                    jobs = pd.DataFrame()
                    for attempt in range(1, self.max_retries + 1):
                        try:
                            # Scrape jobs for the current query and location
                            jobs = scrape_jobs(
                                site_name=self.sites,
                                search_term=query,
                                google_search_term=None,
                                location=location,
                                distance=100,
                                is_remote=False,
                                job_type=None,
                                easy_apply=None,
                                results_wanted=10000,        # Arbitrarily large value
                                country_indeed="usa",
                                proxies=self.proxy,
                                ca_cert=None,
                                description_format="html",   # We convert to markdown later
                                linkedin_fetch_description=True,
                                linkedin_company_ids=None,
                                offset=0,
                                hours_old=self.hours_old,
                                enforce_annual_salary=False,
                                verbose=0,
                                user_agent=None
                            )
                            break  # Exit retry loop on success
                        except (RequestException, HTTPError) as e:
                            # Error occured during request
                            if self.cancel_event and self.cancel_event.is_set():
                                break
                            JobsDataModel.logger.warning(
                                f"Query {i_qry+1:02d}, Location {i_loc+1:02d}"
                                f" | Attempt {attempt} failed: {e}")
                            if attempt == self.max_retries:
                                # Max retries reached, log and skip
                                JobsDataModel.logger.error(
                                    f"Query {i_qry+1:02d}, Location {i_loc+1:02d}"
                                     " | Max retries reached. Skipping.")
                            else:
                                # Exponential backoff before retrying
                                time.sleep(self.backoff_base * (2 ** (attempt - 1)))
                    if jobs.empty:
                        # No jobs found, move to next request
                        JobsDataModel.logger.info(
                            f"Query {i_qry+1:02d}, Location {i_loc+1:02d}"
                             " | No jobs found")
                        continue
                    # Filter out jobs older than hours_old
                    datetime = pd.to_datetime(jobs["date_posted"])
                    cutoff = dt.datetime.now() - dt.timedelta(hours=self.hours_old)
                    cutoff = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
                    jobs = jobs[datetime >= cutoff]
                    JobsDataModel.logger.info(
                        f"Query {i_qry+1:02d}, Location {i_loc+1:02d}"
                        f" | Collected: {len(jobs):>5}"
                        f" | Elapsed: {self.get_elapsed(t_start, time.time())}")
                    # Append to main data
                    self.data = pd.concat([self.data, jobs], ignore_index=True)
                    self.data.reset_index(drop=True, inplace=True)
                    # Check for cancellation
                    if self.cancel_event and self.cancel_event.is_set():
                        break
                if self.cancel_event and self.cancel_event.is_set():
                    break
            JobsDataModel.logger.info(
                f"{"Summary":^21}"
                f" | Collected: {len(self.data):>5}"
                f" | Elapsed: {self.get_elapsed(t_init, time.time())}")
            # Emit finished signal
            time.sleep(1)  # Small delay to ensure UI updates
            if self.cancel_event and self.cancel_event.is_set():
                JobsDataModel.logger.info("Job collection cancelled by user.")
                self.finished.emit("")
            else:
                self.finished.emit(self.data)
        except Exception:
            self.error.emit(traceback.format_exc())
