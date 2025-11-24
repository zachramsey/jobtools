import datetime as dt
from jobspy import scrape_jobs                      # type: ignore
from markdownify import MarkdownConverter           # type: ignore
from markdownify import ATX, SPACES, UNDERSCORE     # type: ignore
import os
import pandas as pd
import re

from . import HTMLBuilder
from .utils.logger import JTLogger
from .utils import parse_degrees, parse_location, build_regex


class JobsData:
    """ Wrapper around jobspy API to collect and process job postings.
    """

    _logger = JTLogger()
    """ Logger instance for JobsData class. """
    _logger.configure("WARNING")
    
    _converter = MarkdownConverter(bullets='*',
                                   default_title=True,
                                   escape_misc=False,
                                   heading_style=ATX,
                                   newline_style=SPACES,
                                   strong_em_symbol=UNDERSCORE)
    """ Converter to put raw HTML job descriptions into markdown format. """

    def __init__(self, data: pd.DataFrame = pd.DataFrame()):
        """ Initialize the job collector.

        Parameters
        ----------
        data : pd.DataFrame, optional
            Existing DataFrame of job postings.
        """
        date = dt.datetime.now().strftime("%Y%m%d")
        time = dt.datetime.now().strftime('%H%M')
        self._new_path = os.path.join("output", date, time)
        """ Unique output directory for new/modified data. """

        self._load_path = ""
        """ Path from which existing data was loaded. """

        self._modified = False
        """ Flag indicating whether data has been modified since loading. """

        self._df = data.copy()
        """ DataFrame containing collected job postings. """

        # Preprocess existing data
        if len(self._df) > 0:
            self.preprocess()

    def __len__(self) -> int:
        """ Get the number of collected job postings. """
        return len(self._df)
    
    def __getattr__(self, name):
        """ Delegate attribute access to the underlying DataFrame. """
        return getattr(self._df, name)
    
    def __getitem__(self, key):
        """ Get item(s) from the underlying DataFrame. """
        result = self._df.__getitem__(key)
        if isinstance(result, pd.DataFrame):
            jobs = JobsData(data=result)
            jobs._new_path = self._new_path
            jobs._load_path = self._load_path
            jobs._modified = self._modified
            return jobs
        return result

    def __setitem__(self, key, value):
        """ Set item(s) in the underlying DataFrame. """
        self._df.__setitem__(key, value)

    @property
    def path(self) -> str:
        """ Get the output path for saving data. """
        if self._modified or not self._load_path:
            return self._new_path
        else:
            return self._load_path
        
    @property
    def logger(self) -> JTLogger:
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

    @classmethod
    def from_csv(cls, source: str) -> 'JobsData':
        """ Create a JobsData instance from an existing CSV file.

        Parameters
        ----------
        source : str
            Source from which to load existing data.

            *Options:*
            - *`""` -> no existing data (Default)*
            - *`"recent"` -> load most recent output directory*
            - *`"global"` -> load global jobs_data.csv*
            - *`"{yyyymmdd}/{HHMM}"` -> load specified subdirectory*

        Returns
        -------
        JobsData
            JobsData instance with loaded data.

        Notes
        -----
        When an explicit path is provided, it may be specified as a relative
        path to either a directory or a file. If a directory is provided,
        the `jobs_data.csv` file within that directory will be loaded.
        """
        # Load existing data if specified
        path = ""
        if source:
            # Determine full path based on source
            if source == "global":
                # Load output/jobs_data.csv
                path = os.path.join("output", "global", "jobs_data.csv")
            elif source == "recent":
                # Find most recent day-wise subdirectory
                day_dirs = []
                for d in os.listdir("output"):
                    if (os.path.isdir(os.path.join("output", d)) and
                        re.match(r"^\d{4}[01]\d[0-3]\d$", d)):
                        day_dirs.append(d)
                if len(day_dirs) == 0:
                    raise FileNotFoundError("No existing day subdirectories found in output/.")
                day_dirs.sort()
                day_dir = day_dirs[-1]
                # Find most recent time-wise subdirectory
                time_dirs = []
                for d in os.listdir(os.path.join("output", day_dir)):
                    if (os.path.isdir(os.path.join("output", day_dir, d)) and
                        re.match(r"^[0-2]\d[0-5]\d$", d)):
                        time_dirs.append(d)
                if len(time_dirs) == 0:
                    raise FileNotFoundError(f"No existing time subdirectories found in output/{day_dir}.")
                time_dirs.sort()
                time_dir = time_dirs[-1]
                # Construct full path to jobs_data.csv
                path = os.path.join("output", day_dir, time_dir, "jobs_data.csv")
            else:
                # Use specified directory
                if source.startswith("output"):
                    path = source
                else:
                    path = os.path.join("output", source)
                # If path is a directory, append jobs_data.csv
                if os.path.isdir(path):
                    path = os.path.join(path, "jobs_data.csv")
            # Validate data source path
            if not os.path.exists(path):
                raise FileNotFoundError(f"Could not find existing data at {path}")
            # Load existing data
            jobsdata = cls(data=pd.read_csv(path))
            jobsdata._load_path = os.path.dirname(path)
            jobsdata._logger.info(f"Loaded {len(jobsdata)} jobs from {path}")
        else:
            jobsdata = cls()
        return jobsdata
    
    def preprocess(self):
        """ Preprocess collected job postings. """
        # Standardize date_posted column to datetime
        self._df["date_posted"] = pd.to_datetime(self._df["date_posted"])
        # Parse locations into city and state
        city_state_loc = self._df["location"].map(parse_location)
        self._df["city"], self._df["state"], self._df["location"] = zip(*city_state_loc)
        # Add degree existence columns
        has_degrees = self._df["description"].map(parse_degrees)
        self._df["has_ba"], self._df["has_ma"], self._df["has_phd"] = zip(*has_degrees)

    def collect(self,
                site_name: str | list[str],
                search_term: str,
                job_type: str,
                locations: list[str],
                results_wanted: int,
                proxy: str,
                hours_old: int) -> int:
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
            
        Returns
        -------
        int
            Number of job postings collected.

        Notes
        -----
        Collected job postings are appended to the existing DataFrame
        accesible by the `JobsData::data` property.

        Relevant columns from JobSpy include:  
        `"date_posted"`, `"location"`, `"company"`, `"title"`,
        `"job_url"`, `"job_url_direct"`, `"company_url_direct"`,
        `"min_amount"`, `"max_amount"`, `"currency"`, `"interval"`

        Derived columns include:  
        `"city"`, `"state"`, `"has_ba"`,
        `"has_ma"`, `"has_phd"`
        """
        n_init = len(self._df)
        for location in locations:
            # Scrape jobs for this location and search terms
            jobs = scrape_jobs(site_name=site_name,
                               search_term=search_term,
                               location=location,
                               job_type=job_type,
                               results_wanted=results_wanted,
                               proxies=proxy,
                               description_format="html",
                               linkedin_fetch_description=True,
                               hours_old=hours_old,
                               enforce_annual_salary=True)
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
        self.preprocess()
        # Mark data as modified
        self._modified = True
        return len(self._df) - n_init
    
    def update(self, other):
        """ Update this `JobsData` instance with another `JobsData` or DataFrame. """
        if isinstance(other, JobsData):
            self._df = pd.concat([self._df, other._df], ignore_index=True)
        elif isinstance(other, pd.DataFrame):
            self._df = pd.concat([self._df, other], ignore_index=True)
        else:
            raise TypeError(f"Unsupported type for update with JobsData: {type(other)}")
        self._df.reset_index(drop=True, inplace=True)

    def exists(self, column: str, expression: list[str]|str) -> pd.Series:
        """ Create a new boolean column indicating presence of terms in source column.
        
        Parameters
        ----------
        column : str
            Name of the source column to search.
        expression : list[str]|str
            A list of terms or a regex pattern.

        Returns
        -------
        pd.Series
            Series of boolean values.
        """
        pattern = build_regex(expression)
        return self._df[column].str.contains(pattern, case=False, na=False)
    
    def omit(self, column: str, expression: list[str]|str) -> int:
        """ Omit rows where the specified column contains any of the given terms.

        Parameters
        ----------
        column : str
            Column name to check.
        expression : list[str]|str
            A list of terms or a regex pattern.

        Returns
        -------
        int
            Number of rows removed.
        """
        n_init = len(self._df)
        self._df = self._df[~self.exists(column, expression)]
        return n_init - len(self._df)

    def require(self, column: str, expression: list[str]|str) -> int:
        """ Require rows where the specified column contains any of the given terms.

        Parameters
        ----------
        column : str
            Column name to check.
        expression : list[str]|str
            A list of terms or a regex pattern.

        Returns
        -------
        int
            Number of rows removed.
        """
        n_init = len(self._df)
        self._df = self._df[self.exists(column, expression)]
        return n_init - len(self._df)

    def degree_score(self, degree_values: tuple[int, int, int]) -> pd.Series:
        """ Compute degree-based priority scores.

        Parameters
        ----------
        degree_scores : tuple[int, int, int]
            Tuple of score adjustments for (bachelor, master, doctorate) degrees.

        Returns
        -------
        pd.Series
            Series of degree scores.
        """
        score = pd.Series(0, index=self._df.index)
        score += degree_values[0] * self._df["has_ba"].astype(int)
        score += degree_values[1] * self._df["has_ma"].astype(int)
        score += degree_values[2] * self._df["has_phd"].astype(int)
        return score
            
    def keyword_score(self, keyword_score_map: dict[int, list[str]]
                      ) -> tuple[pd.Series, pd.Series]:
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
        pd.Series
            Series of keyword scores.
        pd.Series
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
        return score, keywords
    
    def rank_order_score(self, column: str, rank_order: list[str]) -> pd.Series:
        """ Compute priority scores based on specified rank order of column values.

        Parameters
        ----------
        column : str
            Column name to evaluate.
        rank_order : list[str]
            List of column values in descending priority order.  

        Returns
        -------
        pd.Series
            Series of priority scores.

        Notes
        -----
        - Undefined values default to score of 0.
        - Empty values default to score of -1.
        """
        priority_map = {value: len(rank_order) - rank
                        for rank, value in enumerate(rank_order)}
        priority_map[""] = -1
        return self._df[column].map(priority_map).fillna(0).astype(int)
        
    def prioritize(self,
                   keyword_value_map: dict[int, list[str]],
                   state_rank_order: list[str],
                   site_rank_order: list[str],
                   degree_values: tuple[int, int, int]):
        """ Opinionated helper method to apply a priority ordering among job postings.

        Parameters
        ----------
        keyword_value_map : dict[int, list[str]]
            Dictionary mapping integer priorities to lists of keywords.
            Each keyword found in title or description adds the corresponding
            priority to the job posting's running score.
        state_rank_order : list[str]
            List of states in descending priority order.
        site_rank_order : list[str]
            List of job sites in descending priority order.
        degree_values : tuple[int, int, int]
            Tuple of score adjustments for (bachelor, master, doctorate) degrees.
        """
        self._df["keyword_score"], self._df["keywords"] = self.keyword_score(keyword_value_map)
        self._df["degree_score"] = self.degree_score(degree_values)
        self._df["req_score"] = self._df["keyword_score"] + self._df["degree_score"]
        self._df["location_score"] = self.rank_order_score("state", state_rank_order)
        self._df["site_score"] = self.rank_order_score("site", site_rank_order)
        self._df.sort_values(by=["date_posted", "req_score", "location_score", "site_score"],
                             ascending=False, inplace=True)
        self._df.reset_index(drop=True, inplace=True)
        self._df.drop(columns=["keyword_score", "keywords", "degree_score",
                               "req_score", "location_score", "site_score"], inplace=True)

    def deduplicate(self) -> int:
        """ Remove duplicate job postings where the following column
        subsets are identical: `(company, terms)` or `(title, terms)`
        if `terms` column exists, otherwise `(company title)`.

        Returns
        -------
        int
            number of duplicates removed.

        Notes
        -----
        The `terms` column is created in `JobsData::keyword_score()` method;
        assuming a **sufficiently rich keyword dictionary**, it can serve
        as an efficient heuristic for identifying duplicate descriptions
        where `company` or `title` may vary slightly.
        """
        n_init = len(self._df)
        has_terms = [["company", "terms"], ["title", "terms"]]
        no_terms = [["company", "title"]]
        subsets = has_terms if "terms" in self._df.columns else no_terms
        for subset in subsets:
            self._df.drop_duplicates(subset=subset, inplace=True)
        self._df.reset_index(drop=True)
        return n_init - len(self._df)
    
    def _validate_path(self, path: str, file_name: str) -> str:
        """ Validate and return output directory path.

        Parameters
        ----------
        path : str
            Output directory path.
        file_name : str
            Base output file name.

        Returns
        -------
        str
            Validated output directory path.

        Raises
        ------
        ValueError
            If a file path is provided instead of a directory path.
        """
        name, extension = file_name.rsplit('.', 1)
        # Determine output directory path
        if not path:
            path = self.path
        elif path.endswith(f".{extension}"):
            JobsData._logger.warning("Expected directory path, got file path: "
                                    f"{path}. Using parent directory instead.")
            path = os.path.dirname(path)
        # Ensure output directory exists
        if not os.path.exists(path):
            os.makedirs(path)
        # Determine output file path
        file = os.path.join(path, file_name)
        if not path.startswith(os.path.join("output", "global")):
            i = 0
            while os.path.exists(file):
                i += 1
                file = os.path.join(path, f"{name}_{i}.{extension}")
        return file
    
    def export_csv(self, path: str = ""):
        """ Save collected job postings to CSV file.

        Parameters
        ----------
        path : str, optional
            Output directory to save data; if empty, uses derived path.
        """
        # Validate output path
        file = self._validate_path(path, "jobs_data.csv")
        # Prepare DataFrame for saving
        new_cols = ["city", "state", "has_ba", "has_ma", "has_phd"]
        data = self._df.drop(columns=new_cols, errors='ignore')
        # Save DataFrame to CSV
        data.to_csv(file, index=False)
        JobsData._logger.info(f"Saved {len(self._df)} jobs to {file}")            
                
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
               path: str = "") -> str:
        """ Export DataFrame to a nicely formatted HTML file.

        Parameters
        ----------
        headers : dict[str, str]
            Mapping of column names to their display headers.
        keys : dict[str, str]
            Mapping of column names to associated columns used as sort keys.
        path : str, optional
            Output directory to save HTML file; if empty, uses derived path.

        Returns
        -------
        str
            Path to the exported HTML file.
        """
        # Build HTML string from DataFrame
        builder = HTMLBuilder(self._df)
        html_str = builder.build_html(headers, keys)
        # Validate output path
        file = self._validate_path(path, "jobs_data.html")
        # Save HTML string to file
        with open(file, "w", encoding="utf-8") as f:
            f.write(html_str)
        JobsData._logger.info(f"Exported {len(self._df)} jobs to {file}")
        return file
