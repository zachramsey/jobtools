import datetime as dt
from jobspy import scrape_jobs, desired_order       # type: ignore
from markdownify import MarkdownConverter           # type: ignore
from markdownify import ATX, SPACES, UNDERSCORE     # type: ignore
import multiprocessing as mp
import os
import pandas as pd
from pathlib import Path
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
import re
import threading
import time
from typing import Callable
from ..utils import HTMLBuilder
from ..utils import JDLogger
from ..utils import parse_degrees, parse_location, build_regex
from ..utils import get_data_dir, get_data_sources


# COLUMN_ORDER = [
#     'id', 'date_posted', 'city', 'state', 'location', 'location_score',
#     'company', 'company_description', 'company_industry',
#     'company_num_employees', 'company_revenue', 'company_rating'
#     'company_reviews_count', 'company_addresses', 'company_url'
#     'company_url_direct', 'company_logo', 'title', 'job_function',
#     'description', 'skills', 'keywords', 'keyword_score', 'job_level',
#     'experience_range', 'job_type', 'work_from_home_type', 'is_remote',
#     'has_ba', 'has_ma', 'has_phd', 'degree_score', 'salary_source',
#     'interval', 'min_amount', 'max_amount', 'currency', 'vacancy_count',
#     'site', 'job_url', 'job_url_direct', 'emails'
# ]


class JobsDataModel(QAbstractTableModel):
    """ Wrapper around jobspy API to collect and process job postings. """

    _logger = JDLogger()
    """ Logger instance for JobsData class. """
    
    _converter = MarkdownConverter(bullets='*',
                                   default_title=True,
                                   escape_misc=False,
                                   heading_style=ATX,
                                   newline_style=SPACES,
                                   strong_em_symbol=UNDERSCORE)
    """ Converter to put raw HTML job descriptions into markdown format. """

    def __init__(self, data: pd.DataFrame|Path|str = pd.DataFrame()):
        """ Initialize the job collector.

        Parameters
        ----------
        data : pd.DataFrame|Path|str, optional
            Initial data to populate the JobsData instance.
            - *DataFrame* : use the provided DataFrame as initial data.
            - *Path* : load data from the specified CSV file.
            - *"latest"* : load data from the most recent run.
            - *"archive"* : load data from the archive data path.
        """
        super().__init__()

        date = dt.datetime.now().strftime("%Y%m%d")
        time = dt.datetime.now().strftime('%H%M')
        self._new_path = get_data_dir() / date / time
        """ Unique output directory for new/modified data. """

        self._load_path = Path()
        self._modified = False
        
        if isinstance(data, pd.DataFrame):
            self._df = data.copy()
        else:
            # Determine full path based on source
            path = Path()
            if isinstance(data, str):
                if data == "archive":
                    # Use archive data path
                    path = get_data_dir() / "archive" / "jobs_data.csv"
                elif data == "latest":
                    # Find most recent day-wise subdirectory
                    data_paths = get_data_sources()
                    del data_paths["Archive"]
                    path = data_paths[max(data_paths.keys())]
            elif isinstance(data, Path):
                # Use specified directory
                path = data if data.is_absolute() else get_data_dir() / data
                # If path is a directory, get jobs_data.csv within it
                if path.is_dir():
                    path = path / "jobs_data.csv"
            # Validate data source path
            if not path.exists():
                raise FileNotFoundError(f"Could not find existing data at {path}")
            # Load existing data
            self._df = pd.read_csv(path)
            self._load_path = path.parent
            self._logger.info(f"Loaded {len(self._df)} jobs from {path}")

        # Preprocess existing data
        if len(self._df) > 0:
            self.__preprocess()

    def __len__(self) -> int:
        """ Get the number of collected job postings. """
        return len(self._df)
    
    def __getattr__(self, name):
        """ Delegate attribute access to the underlying DataFrame. """
        return getattr(self._df, name)
    
    def __getitem__(self, key):
        """ Get item(s) from the underlying DataFrame. """
        result = self._df[key]
        if isinstance(result, pd.DataFrame):
            jobs = JobsDataModel(data=result)
            jobs._new_path = self._new_path
            jobs._load_path = self._load_path
            jobs._modified = self._modified
            return jobs
        return result

    def __setitem__(self, key, value):
        """ Set item(s) in the underlying DataFrame. """
        self._df[key] = value

    @property
    def path(self) -> Path:
        """ Get the output path for saving data. """
        if self._modified or not self._load_path:
            return self._new_path
        else:
            return self._load_path
        
    @property
    def logger(self) -> JDLogger:
        """ Get the JobsData logger instance. """
        return self._logger
        
    @classmethod
    def set_log_level(cls, level: str):
        """ Set the logging level for the JobsData class.

        Parameters
        ----------
        level : str
            Logging level (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
        """
        cls._logger.set_level(level)

    def update(self, other):
        """ Update this `JobsData` instance with another `JobsData` or DataFrame. """
        if isinstance(other, JobsDataModel):
            self._df = pd.concat([self._df, other._df], ignore_index=True)
        elif isinstance(other, pd.DataFrame):
            self._df = pd.concat([self._df, other], ignore_index=True)
        else:
            raise TypeError(f"Unsupported type for update with JobsData: {type(other)}")
        self._df.reset_index(drop=True, inplace=True)

    #################################
    ## QAbstractTableModel Methods ##
    #################################
        
    @property
    def columns(self) -> list[str]:
        return self._df.columns.tolist()

    def rowCount(self, parent=QModelIndex()) -> int:
        return self._df.shape[0]
    
    def columnCount(self, parent=QModelIndex()) -> int:
        return self._df.shape[1]
    
    def columnIndex(self, column_name: str) -> int:
        return int(self._df.columns.get_loc(column_name))  # type: ignore
    
    def data(self, index, role):
        if index.isValid():
            val = self._df.iloc[index.row(), index.column()]
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
                return str(self._df.columns[section])
            # elif orientation == Qt.Orientation.Vertical:
            #     return str(self._jobs._df.index[section])
        return None
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        col_name = self._df.columns[column]
        self.layoutAboutToBeChanged.emit()
        try:
            self._df.sort_values(by=col_name,
                                 ascending=(order == Qt.SortOrder.AscendingOrder),
                                 inplace=True)
        except Exception as e:
            self._logger.warning(f"Failed to sort by column '{col_name}': {e}")
        self.layoutChanged.emit()
    
    #################################
    ##       Data Collection       ##
    #################################
    
    def __preprocess(self):
        """ Preprocess collected job postings. """
        # Remove escape characters from emphasis tags in descriptions
        self._df["description"] = self._df["description"].apply(
            lambda md: re.sub(r'\\*(_|\*)', r'\1', md) if isinstance(md, str) else md)
        # Ensure date_posted is in YYYY-MM-DD format
        self._df["date_posted"] = pd.to_datetime(self._df["date_posted"]).dt.strftime("%Y-%m-%d")
        # Parse locations into city and state
        self._df["city"], self._df["state"] = zip(*self._df["location"].map(parse_location))
        # Add degree existence columns
        has_degrees = self._df["description"].map(parse_degrees)
        self._df["has_ba"], self._df["has_ma"], self._df["has_phd"] = zip(*has_degrees)
        # # Standardize column order
        # existing_cols = [col for col in COLUMN_ORDER if col in self._df.columns]
        # self._df = self._df.reindex(columns=existing_cols)

    @staticmethod
    def __scrape_jobs_worker(queue: mp.Queue, kwargs: dict):
        """ Worker for calling scrape_jobs in a separate process. """
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
                cancel_event: threading.Event | None = None) -> int:
        """ Collect job postings.

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
        if cancel_event is None:
            cancel_check = lambda: False  # noqa: E731
        else:
            cancel_check = cancel_event.is_set
        # Collect jobs for each location
        n_init = len(self._df)
        for location in locations:
            if cancel_check():
                self.logger.info("Job collection cancelled before next location.")
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
                          enforce_annual_salary=True)
            # Set up multiprocessing queue and process
            q: mp.Queue = mp.Queue()
            p = mp.Process(target=self.__scrape_jobs_worker, args=(q, kwargs))
            p.start()
            # Monitor process for cancellation
            while p.is_alive():
                if cancel_check():
                    self.logger.info("Job collection cancelled: terminating worker process.")
                    p.terminate()
                    p.join()
                    break
                time.sleep(0.1)     # Avoid busy waiting
            # Get results from queue
            jobs = pd.DataFrame()
            try:
                result = q.get_nowait()
                if isinstance(result, Exception):
                    self.logger.warning(f"Collection worker raised an exception: {result}")
                else:
                    jobs = result
            except Exception as e:
                self.logger.warning(f"Failed to get results from collection worker: {e}")
            # Cancellation mid-scrape
            if cancel_check():
                break
            # Skip if no jobs found
            if len(jobs) > 0:
                # Filter out jobs older than hours_old
                datetime = pd.to_datetime(jobs["date_posted"])
                cutoff = dt.datetime.now() - dt.timedelta(hours=hours_old)
                cutoff = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
                jobs = jobs[datetime >= cutoff]
                # Append to main DataFrame
                self._df = pd.concat([self._df, jobs], ignore_index=True)
                self._df.reset_index(drop=True, inplace=True)
        # Convert raw html descriptions to markdown
        self._df["description"] = self._df["description"].apply(
            lambda html: self._converter.convert(html)
                         if isinstance(html, str) and len(html) > 0 else html)
        # Preprocess collected data
        self.__preprocess()
        # Mark data as modified
        self._modified = True
        self.logger.info(f"Collected {len(self._df) - n_init} new jobs.")
        return len(self._df) - n_init

    #################################
    ##       Data Processing       ##
    #################################

    def exists(self, column: str, expression: list[str]|str|bool|int|float|pd.Series|Callable) -> pd.Series:
        """ Create a boolean mask indicating which rows match the specified expression.
        
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
    
    def exclude(self, column: str, expression: list[str]|str|bool|int|float|pd.Series|Callable) -> int:
        """ Exclude rows that match the specified expression in the given column.
        
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
        int
            Number of rows removed.
        """
        n_init = len(self._df)
        self._df = self._df[~self.exists(column, expression)]
        self._modified = True
        self.logger.info(f"Removed {n_init - len(self._df)} jobs with `{column.replace('_', ' ')}` rejection filter.")
        return n_init - len(self._df)

    def select(self, column: str, expression: list[str]|str|bool|int|float|pd.Series|Callable) -> int:
        """ Select rows that match the specified expression in the given column.
        
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
        int
            Number of rows removed.
        """
        n_init = len(self._df)
        self._df = self._df[self.exists(column, expression)]
        self._modified = True
        self.logger.info(f"Removed {n_init - len(self._df)} jobs with `{column.replace('_', ' ')}` requirement filter.")
        return n_init - len(self._df)

    def degree_score(self,
                     degree_values: tuple[int, int, int],
                     inplace: bool = False) -> pd.Series|None:
        """ Compute degree-based priority scores.

        Parameters
        ----------
        degree_scores : tuple[int, int, int]
            Tuple of score adjustments for (bachelor, master, doctorate) degrees.
        inplace : bool, optional
            If True, add `degree_score` column to DataFrame;  
            if False, return Series of scores (default).

        Returns
        -------
        pd.Series, optional
            Series of degree-based priority scores.
        """
        score = pd.Series(0, index=self._df.index)
        score += degree_values[0] * self._df["has_ba"].astype(int)
        score += degree_values[1] * self._df["has_ma"].astype(int)
        score += degree_values[2] * self._df["has_phd"].astype(int)
        if inplace:
            self._df["degree_score"] = score
            return None
        else:
            return score
            
    def keyword_score(self,
                      keyword_score_map: dict[int, list[str]],
                      inplace: bool = False) -> tuple[pd.Series, pd.Series]|None:
        """ Compute keyword-based priority scores.

        Parameters
        ----------
        keyword_score_map : dict[int, list[str]]
            Dictionary mapping integer priorities to lists of keywords.
            Each keyword found in title or description adds the corresponding
            priority to the job posting's running score.
        inplace : bool, optional
            If True, add `keyword_score` and `keywords` columns to DataFrame;  
            if False, return Series of scores and matched keywords (default).

        Returns
        -------
        tuple[pd.Series, pd.Series], optional
            Series of keyword scores.  
            Series of matched keywords as comma-separated strings.
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
        keywords = keywords.apply(lambda kws: ", ".join(kw.replace("\\", "") for kw in kws))
        if inplace:
            self._df["keyword_score"] = score
            self._df["keywords"] = keywords
            return None
        else:
            return score, keywords
    
    def rank_order_score(self,
                         source_column: str,
                         rank_order: list[str],
                         target_column: str | None = None) -> pd.Series|None:

        """ Compute priority scores based on specified rank order of column values.

        Parameters
        ----------
        source_column : str
            Name of the source column to evaluate.
        rank_order : list[str]
            List of column values in descending priority order.  
        target_column : str, optional
            If specified, add `target_column` to DataFrame;  
            if None, return Series of scores (default).

        Returns
        -------
        pd.Series, optional
            Series of rank-order based priority scores.

        Notes
        -----
        - Undefined values default to score of 0.
        - Empty values default to score of -1.
        """
        priority_map = {value: len(rank_order) - rank
                        for rank, value in enumerate(rank_order)}
        priority_map[""] = -1
        scores = self._df[source_column].map(priority_map).fillna(0).astype(int)
        if target_column is not None:
            self._df[target_column] = scores
            return None
        else:
            return scores
        
    def standard_ordering(self):
        """ Sort job postings hierarchically by date
        posted, location, degree, keywords, and site.

        Assumes that `location_score`, `degree_score`,
        `keyword_score`, and `site_score` columns exist.
        """
        self._df.sort_values(by=["date_posted", "location_score", "degree_score",
                                 "keyword_score", "site_score"],
                             ascending=False, inplace=True)
        self._df.reset_index(drop=True, inplace=True)
        
    def prioritize(self,
                   state_rank_order: list[str],
                   degree_values: tuple[int, int, int],
                   keyword_value_map: dict[int, list[str]],
                   site_rank_order: list[str],
                   drop_intermediate: bool = True):
        """ Helper method to apply a priority ordering among job postings.

        Parameters
        ----------
        state_rank_order : list[str]
            List of states in descending priority order.
        degree_values : tuple[int, int, int]
            Tuple of score adjustments for (bachelor, master, doctorate) degrees.
        keyword_value_map : dict[int, list[str]]
            Dictionary mapping integer priorities to lists of keywords.
            Each keyword found in title or description adds the corresponding
            priority to the job posting's running score.
        site_rank_order : list[str]
            List of job sites in descending priority order.
        drop_intermediate : bool, optional
            Whether to drop intermediate scoring columns after prioritization.
        """
        keyword_results = self.keyword_score(keyword_value_map)
        self._df["location_score"] = self.rank_order_score("state", state_rank_order)
        self._df["degree_score"] = self.degree_score(degree_values)
        self._df["keyword_score"], self._df["keywords"] = keyword_results  # type: ignore
        self._df["site_score"] = self.rank_order_score("site", site_rank_order)
        self.standard_ordering()
        if drop_intermediate:
            self._df.drop(columns=["location_score", "degree_score", "keyword_score",
                                   "keywords", "site_score"], inplace=True)

    def drop_duplicate_jobs(self) -> int:
        """ Remove duplicate job postings. Keeps the first occurrence.

        Sorting jobs in descending order of preference before calling
        this method is recommended to retain the most relevant postings.

        Returns
        -------
        int
            number of duplicates removed.
        """
        n_init = len(self._df)
        # Drop duplicates with the same job board identifier
        self._df.drop_duplicates(subset=["id"], keep="first", inplace=True, ignore_index=True)
        # Drop duplicates pointing to the same direct job URL
        self._df.drop_duplicates(subset=["job_url_direct"], keep="first", inplace=True, ignore_index=True)
        # Drop duplicates with the same company and title
        self._df.drop_duplicates(subset=["company", "title"], keep="first", inplace=True, ignore_index=True)
        # Drop duplicates with the same title and description
        self._df.drop_duplicates(subset=["title", "description"], keep="first", inplace=True, ignore_index=True)
        self._df.reset_index(drop=True, inplace=True)
        self._modified = True
        self.logger.info(f"Removed {n_init - len(self._df)} duplicate job postings.")
        return n_init - len(self._df)
    
    def drop_empty_cols(self):
        """ Drop columns that contain only NaN or empty values. """
        for col in self._df.columns:
            if self._df[col].replace("", pd.NA).isna().all():
                self._df.drop(columns=[col], inplace=True)
        self._modified = True
    
    ################################
    ##       Data Exporting       ##
    ################################
    
    def __validate_path(self, path: Path|None, file_name: str) -> Path:
        """ Validate and return output directory path.

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
        name, extension = file_name.rsplit('.', 1)
        # Determine output directory path
        if path is None:
            path = self.path
        elif path.suffix == f".{extension}":
            JobsDataModel._logger.warning("Expected directory path, got file path: "
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
                   drop_derived: bool = True) -> Path:
        """ Save collected job postings to CSV file.

        Parameters
        ----------
        path : Path, optional
            Output directory to save data; if empty, uses derived path.
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
        data = self._df.copy()
        if drop_derived:
            derived_cols = [col for col in data.columns if col not in desired_order]
            data.drop(columns=derived_cols, inplace=True)
        # Save DataFrame to CSV
        data.to_csv(file, index=False)
        JobsDataModel._logger.info(f"Saved {len(self._df)} jobs to {file}")
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
        """ Export DataFrame to a nicely formatted HTML file.

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
        JobsDataModel._logger.info(f"Exported {len(self._df)} jobs to {file}")
        return file
