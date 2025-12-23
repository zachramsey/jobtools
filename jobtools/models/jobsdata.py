import datetime as dt
import multiprocessing as mp
import os
import queue
import re
import threading
import time
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd  # type: ignore
from jobspy import desired_order, scrape_jobs  # type: ignore
from markdownify import (  # type: ignore
    ATX,
    SPACES,
    UNDERSCORE,
    MarkdownConverter,  # type: ignore
)
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor, QFont

from ..utils import HTMLBuilder, JDLogger, build_regex, get_data_dir, get_data_sources, parse_degrees, parse_location


class JobsDataModel(QAbstractTableModel):
    """Wrapper around jobspy API to collect and process job postings."""

    collectStarted = Signal()       # noqa: N815
    collectFinished = Signal(str)   # noqa: N815

    _logger = JDLogger()
    _converter = MarkdownConverter(
        bullets="*", default_title=True, escape_misc=False,
        heading_style=ATX, newline_style=SPACES, strong_em_symbol=UNDERSCORE
    )

    def __init__(self, data: pd.DataFrame|Path|str = pd.DataFrame()):
        """Initialize the job collector.

        Parameters
        ----------
        data : pd.DataFrame|Path|str, optional
            Initial data to populate the JobsData instance.
            - *DataFrame* : use the provided DataFrame as initial data.
            - *Path* : load data from the specified CSV file.
            - *"latest"* : load data from the most recent run.
            - *"favorites"* : load data from the favorites data path.
            - *"archive"* : load data from the archive data path.
        """
        super().__init__()

        # Specialized data sources
        self._foobar_path = get_data_dir() / "foobar"   # Placeholder data path
        self._arch_path = get_data_dir() / "archive"
        os.makedirs(self._arch_path, exist_ok=True)
        self._fav_path = get_data_dir() / "favorites"
        os.makedirs(self._fav_path, exist_ok=True)
        self._fav_df = pd.DataFrame()

        # Internal data
        self._load_path = Path()
        self._new_path = Path()
        self.__get_new_path()
        self.collectStarted.connect(self.__get_new_path)
        self._modified = False

        # Dynamic view of internal data
        self.columns: list[str] = []
        self._col_len_thresh: dict[str, int] = {}
        self._header_labels: dict[str, str] = {}
        self._filter_masks: dict[str, pd.Series] = {}
        self._sort_column = None
        self._sort_order = Qt.SortOrder.AscendingOrder

        # Initialize data
        if isinstance(data, pd.DataFrame):
            self.__pre_load()
            self._df = data.copy()
            self.__prep_data()
            self.__post_load()
            self._logger.info(f"Initialized {len(self._df)} jobs from DataFrame.")
        else:
            self.load_data(data)

        # Visible columns
        self.columns = self._df.columns.tolist()

    def __len__(self) -> int:
        """Get the number of collected job postings."""
        return len(self._df)

    def __getattr__(self, name):
        """Delegate attribute access to the underlying DataFrame."""
        return getattr(self._df, name)

    def __getitem__(self, key):
        """Get item(s) from the underlying DataFrame."""
        result = self._df[key]
        if isinstance(result, pd.DataFrame):
            jobs = JobsDataModel(data=result)
            jobs._new_path = self._new_path
            jobs._load_path = self._load_path
            jobs._modified = self._modified
            return jobs
        return result

    def __setitem__(self, key, value):
        """Set item(s) in the underlying DataFrame."""
        self._df[key] = value

    @property
    def path(self) -> Path:
        """Get the output path for saving data."""
        if self._load_path in [self._fav_path, self._arch_path]:
            return self._load_path
        elif self._modified or not self._load_path:
            return self._new_path
        else:
            return self._load_path

    @property
    def logger(self) -> JDLogger:
        """Get the JobsData logger instance."""
        return self._logger

    @classmethod
    def set_log_level(cls, level: str):
        """Set the logging level for the JobsData class.

        Parameters
        ----------
        level : str
            Logging level (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
        """
        cls._logger.set_level(level)

    #################################
    ## QAbstractTableModel Methods ##
    #################################

    def set_visible_columns(self, columns: list[str]):
        """Set the visible columns in the data model.

        Parameters
        ----------
        columns : list[str]
            List of column names to set as visible.
        """
        self.beginResetModel()
        self.columns = columns
        self.endResetModel()

    def set_column_labels(self, labels: dict[str, str]):
        """Set custom labels for columns.

        Parameters
        ----------
        labels : dict[str, str]
            Dictionary mapping column names to their desired labels.
        """
        self.beginResetModel()
        self._header_labels = labels
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:        # noqa: N802
        return self._dyn_df.shape[0]

    def columnCount(self, parent=QModelIndex()) -> int:     # noqa: N802
        return len(self.columns)

    def columnIndex(self, column_name: str) -> int:         # noqa: N802
        return int(self.columns.index(column_name))

    def headerData(self, section, orientation, role):       # noqa: N802
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                col = self.columns[section]
                return self._header_labels.get(col, col.replace("_", " ").title())
            elif orientation == Qt.Orientation.Vertical:
                return str(self._dyn_df.index[section])
        return None

    def data(self, index, role):
        if not index.isValid():
            return None
        col = self.columns[index.column()]
        val = self._dyn_df[col].iloc[index.row()]
        try:
            val = val.item()
        except AttributeError:
            pass
        if role == Qt.ItemDataRole.DisplayRole:
            split = " "
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
                split = ", "
            if isinstance(val, bool):
                if col == "is_favorite":
                    val = "★" if val else "☆"
                else:
                    val = "◆" if val else ""   # ╳
            if col in self._col_len_thresh:
                pos = self._col_len_thresh[col]
                val = str(val)
                while pos < len(val):
                    split_pos = val.rfind(split, 0, pos)
                    if split_pos == -1:
                        break
                    if split == ", ":
                        split_pos += 1
                    val = val[:split_pos] + "\n" + val[split_pos + 1:]
                    pos = split_pos + self._col_len_thresh[col] + 1
            return str(val)
        elif role == Qt.ItemDataRole.EditRole:
            return val
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if isinstance(val, bool):
                return Qt.AlignmentFlag.AlignCenter
        elif role == Qt.ItemDataRole.FontRole:
            if col == "site":
                font = QFont()
                font.setUnderline(True)
                return font
        elif role == Qt.ItemDataRole.ForegroundRole:
            if col == "site":
                return QColor(Qt.GlobalColor.blue)
        elif role == Qt.ItemDataRole.UserRole + 1:
            # Custom role: indicates clickable item
            if col in ["site", "company", "title", "is_favorite"]:
                return True
        return None

    def __apply_sort(self):
        if self._sort_column is not None:
            ascending = self._sort_order == Qt.SortOrder.AscendingOrder
            self._df.sort_values(by=self._sort_column,
                                 ascending=ascending,
                                 inplace=True,
                                 ignore_index=True)

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        self._sort_column = self.columns[column]    # type: ignore
        self._sort_order = order
        self.layoutAboutToBeChanged.emit()
        self.__apply_sort()
        self.layoutChanged.emit()

    def __apply_filters(self):
        if self._filter_masks:
            combined_mask = pd.Series(True, index=self._df.index)
            for m in self._filter_masks.values():
                combined_mask &= m
            self._dyn_df = self._df[combined_mask].reset_index(drop=True)
        else:
            self._dyn_df = self._df.copy()

    def set_filter(self,
                    identifier: str,
                    column: str,
                    expression: list[str]|str|bool|int|float|pd.Series|Callable,
                    invert: bool = False):
        """Filter data based on the specified expression in the given column.

        Parameters
        ----------
        identifier : str
            Unique identifier for the filter (used to manage multiple filters).
        column : str
            Name of the source column to search.
        expression : list[str]|str|bool|int|float|pd.Series|Callable
            Expression defining the terms or matches to search for.

            *See `JobsData.exists()` for details on supported types.*
        invert : bool, optional
            If True, invert the filter to exclude matching rows.
        """
        self.beginResetModel()
        mask = self.exists(column, expression)
        if invert:
            mask = ~mask
        self._filter_masks[identifier] = mask
        self.__apply_filters()
        self.__apply_sort()
        self.endResetModel()

    def refresh_view(self):
        """Refresh the dynamic view by reapplying filters and sorting."""
        self.beginResetModel()
        self.__apply_filters()
        self.__apply_sort()
        self.endResetModel()

    def toggle_favorite(self, index: QModelIndex):
        """Toggle the 'favorite' status of the job at the given index.

        Parameters
        ----------
        index : QModelIndex
            Index of the job posting to toggle favorite status for.
        """
        job_id = self._dyn_df["id"].iloc[index.row()]
        if self._dyn_df.at[index.row(), "is_favorite"]:
            # Remove from favorites
            self._fav_df = self._fav_df[self._fav_df["id"] != job_id]
            self._dyn_df.at[index.row(), "is_favorite"] = False
        else:
            # Add to favorites
            job_row = self._dyn_df[self._dyn_df["id"] == job_id]
            if not job_row.empty:
                self._fav_df = pd.concat([self._fav_df, job_row], ignore_index=True)
                self._dyn_df.at[index.row(), "is_favorite"] = True
        # Save updated favorites
        self.export_csv(path=self._fav_path, data=self._fav_df)
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole,
                                                Qt.ItemDataRole.EditRole])

    def get_job_data(self, index: QModelIndex) -> dict:
        """Get the job data as a dictionary for the given model index."""
        data = self._dyn_df.iloc[index.row()].copy()
        data.replace({pd.NA: None, np.nan: None}, inplace=True)
        return data.to_dict()

    def get_index_url(self, index: QModelIndex) -> str:
        """Get the posting URL for the given model index."""
        return self._dyn_df["job_url"].iloc[index.row()]

    #################################
    ##       Data Collection       ##
    #################################

    def __pre_load(self):
        """Operations to be performed before loading data."""
        if self._load_path == self._foobar_path:
            # Clear out placeholder data
            self._df = pd.DataFrame()
            self._load_path = Path()
        # Signal model reset
        self.beginResetModel()

    def __prep_data(self):
        """Prepare data after loading or collection."""
        if self._df.empty:
            return
        # Load favorites
        self._df["is_favorite"] = False
        if (self._fav_path / "jobs_data.csv").exists():
            self._fav_df = pd.read_csv(self._fav_path / "jobs_data.csv")
            if not self._fav_df.empty:
                self._df["is_favorite"] = self._df["id"].isin(self._fav_df["id"].values)
        # Remove escape characters from emphasis tags in descriptions
        self._df["description"] = self._df["description"].apply(
            lambda md: re.sub(r"\\*(_|\*)", r"\1", md) if isinstance(md, str) else md)
        # Ensure date_posted is in YYYY-MM-DD format
        self._df["date_posted"] = pd.to_datetime(self._df["date_posted"]).dt.strftime("%Y-%m-%d")
        # Parse locations into city and state
        self._df["city"], self._df["state"] = zip(*self._df["location"].map(parse_location))
        # Add degree existence columns
        has_degrees = self._df["description"].map(parse_degrees)
        self._df["has_ba"], self._df["has_ma"], self._df["has_phd"] = zip(*has_degrees)

    def __post_load(self):
        """Operations to be performed after loading data."""
        # Copy to dynamic DataFrame
        self._dyn_df = self._df.copy()
        if not self._df.empty:
            # Apply any active filters and sorting criteria
            self.__apply_filters()
            self.__apply_sort()
            # Compute dynamic string wrapping thresholds
            for col in ["company", "title"]:
                self._col_len_thresh[col] = self.__calc_col_len_thresh(col)
        # Signal model reset complete
        self.endResetModel()

    @staticmethod
    def __scrape_jobs_worker(queue: mp.Queue, kwargs: dict):
        """Worker for calling scrape_jobs in a separate process."""
        try:
            jobs = scrape_jobs(**kwargs)
            queue.put(jobs)
        except Exception as e:
            queue.put(e)

    def collect(self,
                site_name: str | list[str],
                search_term: str,
                job_type: str,
                locations: list[str],
                results_wanted: int,
                proxy: str,
                hours_old: int,
                cancel_event: threading.Event | None = None):
        """Collect job postings.

        Parameters
        ----------
        site_name : str | list[str]
            Job site name(s) to scrape (e.g., "LinkedIn", "Indeed").
        search_term : str
            Search term/expression to use for job scraping.
        job_type : str
            Job type to filter for (e.g., "fulltime", "parttime", "contract", etc.).
        locations : list[str]
            List of locations to search for jobs.
        results_wanted : int
            Number of job postings to collect.
        proxy : str
            Proxy server to use for scraping.
        hours_old : int
            Maximum age of job postings in hours.
        cancel_event : threading.Event, optional
            Event to signal cancellation of the collection process.

        Returns
        -------
        int
            Number of job postings collected.
        """
        # Set up cancellation check
        if cancel_event is None:
            cancel_check = lambda: False  # noqa: E731
        else:
            cancel_check = cancel_event.is_set
        # Collect jobs for each location
        n_init = len(self._df)
        t_init = time.time()
        self.__pre_load()
        for location in locations:
            if cancel_check():
                self._logger.info(f"Job collection cancelled before location '{location}'.")
                break
            # Scrape jobs for this location and search terms
            kwargs = dict(site_name=site_name,
                          search_term=search_term,
                          location=location,
                          job_type=job_type,
                          results_wanted=results_wanted,
                          proxies=proxy,
                          description_format="html",
                          linkedin_fetch_description=True,
                          hours_old=hours_old,
                          enforce_annual_salary=False)
            # Set up multiprocessing queue and process
            q: mp.Queue = mp.Queue()
            p = mp.Process(target=self.__scrape_jobs_worker, args=(q, kwargs))
            p.start()
            jobs = pd.DataFrame()
            # Monitor process and queue
            while True:
                # Check for cancellation
                if cancel_check():
                    self._logger.info("Job collection cancelled: terminating worker process.")
                    if p.is_alive():
                        p.terminate()
                        p.join()
                    break
                # Check for results
                try:
                    result = q.get(timeout=0.5)
                    if isinstance(result, Exception):
                        self._logger.warning(f"Collection worker raised an exception: {result}")
                    else:
                        jobs = result
                    p.join()
                    break
                except queue.Empty:
                    # No result yet; check if process is still alive
                    if not p.is_alive():
                        break
            # Cancellation mid-scrape
            if cancel_check():
                break
            # Skip if no jobs found
            if jobs.empty:
                self._logger.info(f"No jobs found for location '{location}'.")
                continue
            # Filter out jobs older than hours_old
            datetime = pd.to_datetime(jobs["date_posted"])
            cutoff = dt.datetime.now() - dt.timedelta(hours=hours_old)
            cutoff = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
            jobs = jobs[datetime >= cutoff]
            # Append to main DataFrame
            self._df = pd.concat([self._df, jobs], ignore_index=True)
            self._df.reset_index(drop=True, inplace=True)
            self._modified = True
        # Convert raw html descriptions to markdown
        self._df["description"] = self._df["description"].apply(
            lambda html: self._converter.convert(html)
                         if isinstance(html, str) and len(html) > 0 else html)
        # Prepare data
        self.__prep_data()
        self.drop_duplicate_jobs()
        # Update dynamic view
        self.__post_load()
        self._logger.info(f"Collected {len(self._df) - n_init} new jobs in {time.time() - t_init:.1f}s.")

    def load_data(self, source: Path | str):
        """Load job data from a CSV file.

        Parameters
        ----------
        source : Path | str
            Data source to load from.
            - *Path* : load data from the specified CSV file or directory.
            - *"latest"* : load data from the most recent run.
            - *"favorites"* : load data from the favorites data path.
            - *"archive"* : load data from the archive data path.
        """
        if source == Path() or source == "":
            return
        if isinstance(source, str):
            if source == "latest":
                data_paths = get_data_sources()
                source = data_paths[max(data_paths.keys())]
            else:
                source = Path(source)
        if isinstance(source, Path):
            if not source.is_absolute():
                source = get_data_dir() / source
            if source.is_dir():
                source = source / "jobs_data.csv"
        if not source.exists():
            if get_data_dir() in source.parents:
                source_str = str(source.relative_to(get_data_dir()))
            else:
                source_str = str(source)
            self._logger.warning(f"Data source not found at {source_str.replace("/jobs_data.csv", "")}.")
            return
        # Load data
        self.__pre_load()
        self._df = pd.read_csv(source)
        self.__prep_data()
        self._load_path = source.parent
        self._modified = False
        self.__post_load()
        if get_data_dir() in source.parents:
            source_str = str(source.relative_to(get_data_dir()))
        else:
            source_str = str(source)
        self._logger.info(f"Loaded {len(self._df)} jobs from {source_str.replace("/jobs_data.csv", "")}.")

    def update(self, other, inplace: bool = True):
        """Update this `JobsData` instance with another `JobsData` or DataFrame."""
        if isinstance(other, JobsDataModel):
            other_df = other._df
        elif isinstance(other, pd.DataFrame):
            other_df = other
        else:
            raise TypeError("Argument 'other' must be a JobsDataModel or DataFrame.")
        jobs = self if inplace else self.clone()
        jobs.__pre_load()
        jobs._df = pd.concat([jobs._df, other_df], ignore_index=True)
        jobs._df.reset_index(drop=True, inplace=True)
        jobs.__prep_data()
        jobs._modified = True
        jobs.drop_duplicate_jobs()
        jobs.__post_load()
        if not inplace:
            return jobs

    def update_archive(self):
        """Update the archive data with the current data."""
        archive = JobsDataModel("archive")
        archive._df = pd.concat([archive._df, self._df], ignore_index=True)
        archive._df["description"] = archive._df["description"].apply(
            lambda md: re.sub(r"\\*(_|\*)", r"\1", md) if isinstance(md, str) else md)
        archive._df["date_posted"] = pd.to_datetime(archive._df["date_posted"]).dt.strftime("%Y-%m-%d")
        archive.drop_duplicate_jobs()
        archive.export_csv(get_data_dir() / "archive")

    #################################
    ##       Filtering Tools       ##
    #################################

    def drop_duplicate_jobs(self):
        """Remove duplicate job postings. Keeps the first occurrence."""
        n_init = len(self._df)
        # Temporarily order jobs chronologically to keep oldest instances
        self._df.sort_values(by="date_posted", ascending=True, inplace=True, ignore_index=True)
        # Drop duplicates with the same job board identifier
        self._df.drop_duplicates(subset=["id"], keep="first", inplace=True, ignore_index=True)
        # Drop duplicates pointing to the same direct job URL
        self._df.drop_duplicates(subset=["job_url_direct"], keep="first", inplace=True, ignore_index=True)
        # Drop duplicates with the same company and title
        self._df.drop_duplicates(subset=["company", "title"], keep="first", inplace=True, ignore_index=True)
        # Drop duplicates with the same title and description
        self._df.drop_duplicates(subset=["title", "description"], keep="first", inplace=True, ignore_index=True)
        # Restore original order
        self._df.sort_values(by="date_posted", ascending=False, inplace=True, ignore_index=True)
        self._modified = True
        self._logger.info(f"Removed {n_init - len(self._df)} duplicate job postings.")
        return n_init - len(self._df)

    def exists(self, column: str, expression: list[str]|str|bool|int|float|pd.Series|Callable) -> pd.Series:
        """Create a boolean mask indicating which rows match the specified expression.

        Parameters
        ----------
        column : str
            Name of the source column to search.
        expression : list[str]|str|bool|int|float|pd.Series|Callable
            Expression defining the terms or matches to search for.

            *Supported types:*
            - *string or list[str] -> regex matching*
            - *bool/int/float -> direct equality (useful for boolean columns)*
            - *list/tuple/set of scalars -> .isin() matching*
            - *pd.Series (boolean mask) -> reindex/align to stored DataFrame*
            - *Callable -> custom mask builder: Callable(series) -> boolean Series*

        Returns
        -------
        mask : pd.Series
            Boolean mask indicating which rows match the expression.
        """
        if column not in self._df.columns:
            self._logger.warning(f"Column '{column}' not found in DataFrame.")
            mask = pd.Series(False, index=self._df.index)
        elif callable(expression):
            mask = pd.Series(expression(self._df[column]), index=self._df.index).astype(bool)
        elif isinstance(expression, pd.Series):
            mask = expression.reindex(self._df.index).fillna(False).astype(bool)
        elif isinstance(expression, (bool, int, float)):
            mask = (self._df[column] == expression).fillna(False)
        elif isinstance(expression, (list, tuple, set)):
            if all(isinstance(item, (bool, int, float)) for item in expression):
                mask = self._df[column].isin(expression).fillna(False)
            elif all(isinstance(item, str) for item in expression):
                pattern = build_regex(expression)   # type: ignore
                mask = self._df[column].str.contains(pattern, case=False, na=False)
            else:
                self._logger.warning(f"Unsupported expression list types for column '{column}'.")
                mask = pd.Series(False, index=self._df.index)
        else:
            #Fallback: string patterns
            pattern = build_regex(expression)
            mask = self._df[column].str.contains(pattern, case=False, na=False)
        return mask

    #################################
    ##        Sorting Tools        ##
    #################################

    def update_degree_score(self, degree_values: tuple[int, int, int]):
        """Compute degree-based priority scores.

        Parameters
        ----------
        degree_scores : tuple[int, int, int]
            Tuple of score adjustments for (bachelor, master, doctorate) degrees.
        """
        score = pd.Series(0, index=self._df.index)
        score += degree_values[0] * self._df["has_ba"].astype(int)
        score += degree_values[1] * self._df["has_ma"].astype(int)
        score += degree_values[2] * self._df["has_phd"].astype(int)
        self._df["degree_score"] = score
        self._dyn_df["degree_score"] = score

    def update_keyword_score(self, keyword_score_map: dict[int, list[str]]):
        """Compute keyword-based priority scores.

        Parameters
        ----------
        keyword_score_map : dict[int, list[str]]
            Dictionary mapping integer priorities to lists of keywords.
            Each keyword found in title or description adds the corresponding
            priority to the job posting's running score.
        """
        score = pd.Series(0, index=self._df.index)
        keywords = pd.Series([[] for _ in range(len(self._df))], index=self._df.index)
        for priority, keywords_list in keyword_score_map.items():
            for term in keywords_list:
                mask = (self._df["title"].str.contains(term, case=False, na=False) |
                        self._df["description"].str.contains(term, case=False, na=False))
                score[mask] += priority
                for idx in self._df.index[mask]:
                    keywords[idx].append(term)
        keywords = keywords.apply(lambda kws: [kw.replace("\\", "") for kw in kws])
        self._df["keyword_score"] = score
        self._df["keywords"] = keywords
        self._dyn_df["keyword_score"] = score
        self._dyn_df["keywords"] = keywords
        self._col_len_thresh["keywords"] = self.__calc_col_len_thresh("keywords")

    def update_rank_order_score(self,
                         source_column: str,
                         rank_order: list[str],
                         target_column: str):
        """Compute priority scores based on specified rank order of column values.

        Parameters
        ----------
        source_column : str
            Name of the source column to evaluate.
        rank_order : list[str]
            List of column values in descending priority order.
        target_column : str
            Name of the target column to store computed scores.

        Notes
        -----
        - Undefined values default to score of 0.
        - Empty values default to score of -1.
        """
        priority_map = {value: len(rank_order) - rank
                        for rank, value in enumerate(rank_order)}
        priority_map[""] = -1
        scores = self._df[source_column].map(priority_map).fillna(0).astype(int)
        self._df[target_column] = scores
        self._dyn_df[target_column] = scores

    def standard_ordering(self):
        """Sort job postings hierarchically by date posted, location, degree, keywords, and site.

        Assumes that `location_score`, `degree_score`,
        `keyword_score`, and `site_score` columns exist.
        """
        self._df["qualification_score"] = (self._df["degree_score"] + self._df["keyword_score"])
        self._df.sort_values(by=["date_posted", "location_score",
                                 "qualification_score", "site_score"],
                             ascending=False, inplace=True, ignore_index=True)
        self._df.drop(columns=["qualification_score"], inplace=True)

    ###############################
    ##         Utilities         ##
    ###############################

    def clone(self) -> "JobsDataModel":
        """Create a copy of this JobsDataModel instance."""
        new = JobsDataModel(data=self._df.copy())
        new._new_path = self._new_path
        new._load_path = self._load_path
        new._modified = self._modified
        new.columns = list(self.columns)
        new._col_len_thresh = dict(self._col_len_thresh)
        new._header_labels = dict(self._header_labels)
        new._filter_masks = dict(self._filter_masks)
        new._sort_column = self._sort_column
        new._sort_order = self._sort_order
        return new

    def __get_new_path(self):
        """Generate a new output path based on the current date and time."""
        now = dt.datetime.now()
        date = now.strftime("%Y%m%d")
        time = now.strftime("%H%M")
        self._new_path = get_data_dir() / date / time

    def __calc_col_len_thresh(self, col: str, method: str = "iqr") -> int:
        """Calculate string length threshold for wrapping long text in the specified column."""
        if isinstance(self._df[col].iloc[0], list):
            item_len = self._df[col].apply(
                lambda strings: sum(len(str(v)) for v in strings) + (2 * (len(strings) - 1)))
        else:
            item_len = self._df[col].str.len()
        if sum(item_len > 80) == 0:
            thresh = 80
        elif method == "iqr":
            upper, lower = item_len.quantile(0.75), item_len.quantile(0.25)
            thresh = int(upper + 1.5 * (upper - lower))
        elif method == "zscore":
            mean, std = item_len.mean(), item_len.std()
            z_score = (item_len - mean) / std
            thresh = int(item_len[z_score <= 3].max())
        else:
            thresh = 80
        return min(thresh, 80)

    ################################
    ##       Data Exporting       ##
    ################################

    def __validate_path(self, path: Path|None, file_name: str) -> Path:
        """Validate and return output directory path.

        Parameters
        ----------
        path : Path|None
            Output directory path.
        file_name : str
            Base output file name.

        Returns
        -------
        Path
            Validated output directory path.
        """
        name, extension = file_name.rsplit(".", 1)
        # Determine output directory path
        if path is None:
            path = self.path
        elif path.suffix == f".{extension}":
            self._logger.warning("Expected directory path, got file path: "
                                    f"{path}. Using parent directory instead.")
            path = path.parent
        # Ensure output directory exists
        os.makedirs(path, exist_ok=True)
        # Determine output file path
        file = path / file_name
        # Make sure we don't overwrite existing HTML results
        if extension == "html":
            i = 0
            while os.path.exists(file):
                i += 1
                file = path / f"{name}_{i}.{extension}"
        return file

    def export_csv(self,
                   path: Path|None = None,
                   data: pd.DataFrame | None = None,
                   drop_derived: bool = True) -> Path:
        """Save collected job postings to CSV file.

        Parameters
        ----------
        path : Path, optional
            Output directory to save data; if empty, uses derived path.
        data : pd.DataFrame, optional
            DataFrame to save; if None, uses internal DataFrame.
        drop_derived : bool, optional
            Whether to drop derived columns. That is, columns
            resulting from transformations of the original data.

        Returns
        -------
        Path
            Path to the saved CSV file.
        """
        # Validate output path
        file = self.__validate_path(path, "jobs_data.csv")
        # Prepare DataFrame for saving
        data = self._df.copy() if data is None else data.copy()
        if drop_derived:
            derived_cols = [col for col in data.columns if col not in desired_order]
            data.drop(columns=derived_cols, inplace=True)
        # Save DataFrame to CSV
        data.to_csv(file, index=False)
        if get_data_dir() in file.parents:
            file_str = str(file.relative_to(get_data_dir()))
        else:
            file_str = str(file)
        self._logger.info(f"Saved {len(data)} jobs to {file_str.replace('/jobs_data.csv', '')}.")
        return file

    def export_html(self,
               headers: dict[str, str] = {
                   "date_posted": "Date",
                   "state": "State",
                   "company": "Company",
                   "title": "Title",
                   "has_ba": "BS",
                   "has_ma": "MS",
                   "has_phd": "PhD",
                   "job_url": "URL"},
               keys: dict[str, str] = {},
               path: Path|None = None) -> Path:
        """Export DataFrame to a nicely formatted HTML file.

        Parameters
        ----------
        headers : dict[str, str]
            Mapping of column names to their display headers.
        keys : dict[str, str]
            Mapping of column names to associated columns used as sort keys.
        path : Path, optional
            Output directory to save HTML file; if empty, uses derived path.

        Returns
        -------
        Path
            Path to the exported HTML file.
        """
        # Build HTML string from DataFrame
        builder = HTMLBuilder(self._df)
        html_str = builder.build_html(headers, keys)
        # Validate output path
        file = self.__validate_path(path, "jobs_data.html")
        # Save HTML string to file
        with open(file, "w", encoding="utf-8") as f:
            f.write(html_str)
        if get_data_dir() in file.parents:
            file_str = file.relative_to(get_data_dir())
        else:
            file_str = file
        self._logger.info(f"Exported {len(self._df)} jobs to {file_str}")
        return file
