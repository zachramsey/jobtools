import datetime as dt
import os
import time
from typing import Callable

import numpy as np
import pandas as pd  # type: ignore
from markdownify import ATX, SPACES, UNDERSCORE, MarkdownConverter  # type: ignore
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont

from ..utils import JDLogger, build_regex, get_data_dir, parse_degrees, parse_location
from . import ConfigModel

FOOBAR_DATA = {
    "id": "li-0000000000",
    "site": "linkedin",
    "job_url": "https://www.linkedin.com/jobs/view/0000000000",
    "job_url_direct": "https://careers.example.com/",
    "title": "Example Job Title",
    "company": "Example Company",
    "location": "Example City, EX, USA",
    "date_posted": "1970-01-01",
    "job_type": "fulltime",
    "salary_source": "direct_data",
    "interval": "yearly",
    "min_amount": 100000.0,
    "max_amount": 150000.0,
    "currency": "USD",
    "is_remote": "False",
    "job_level": "mid-senior_level",
    "job_function": "Engineering and Information Technology",
    "listing_type": "",
    "emails": "careers@example.com",
    "description": "This is an example job description used as placeholder \
                    data. It provides details about the job responsibilities, \
                    requirements, and qualifications needed for the position.",
    "company_industry": "Internet and Software",
    "company_url": "https://www.linkedin.com/company/example",
    "company_logo": "https://upload.wikimedia.org/wikipedia/commons/8/8b/Wikimedia-logo_black.svg",
    "company_url_direct": "https://www.example.com",
    "company_addresses": "123 Example St, Example City, EX 12345",
    "company_num_employees": "201 to 500",
    "company_revenue": "$5M to $25M",
    "company_description": "Example Company is a leading provider of example \
                            solutions, dedicated to delivering high-quality \
                            products and services to our customers worldwide.",
    "skills": "Example Skill 1; Example Skill 2; Example Skill 3",
    "experience_range": "3-5 years",
    "company_rating": "4.5",
    "company_reviews_count": "150",
    "vacancy_count": "3",
    "work_from_home_type": "hybrid",
}


class JobsDataModel(QAbstractTableModel):
    """Wrapper around jobspy API to collect and process job postings."""

    collectStarted = Signal()       # noqa: N815
    collectFinished = Signal()   # noqa: N815

    logger = JDLogger()
    _converter = MarkdownConverter(
        bullets="*", default_title=True, escape_misc=False,
        heading_style=ATX, newline_style=SPACES, strong_em_symbol=UNDERSCORE
    )

    def __init__(self, config_model: ConfigModel):
        """Initialize the JobsDataModel instance."""
        super().__init__()
        self._config_model = config_model

        # Raw data storage
        self._original_df = pd.DataFrame([FOOBAR_DATA])
        # Intermediate data to be used in dynamic view
        self._active_df = pd.DataFrame()
        # Dynamic data view
        self._dynamic_df = pd.DataFrame()

        # Dynamic view of internal data
        self.active_days = 7
        self.display_favorites = False
        self.columns = self._original_df.columns.tolist()
        self._col_len_thresh: dict[str, int] = {}
        self._header_labels: dict[str, str] = {}
        self._filters: dict[str, tuple[str, list[str]|str|bool|int|float|pd.Series|Callable, bool]] = {}
        self._sort_column = None
        self._sort_order = Qt.SortOrder.AscendingOrder

        # Standard ordering
        self._degree_values: tuple[int, int, int] = (0, 0, 0)
        self._keyword_score_map: dict[int, list[str]] = {}
        self._rank_orders: dict[str, tuple[str, dict[str, int]]] = {}
        self.standard_order = ["date_posted", "location_score", "degree_score",
                               "keyword_score", "site_score"]

        # Initialize data
        self._arch_path = get_data_dir()
        arch_file = self._arch_path / "jobs_data.csv"
        if os.path.exists(arch_file):
            self._original_df = pd.read_csv(arch_file)
            self.logger.info(f"Loaded archived jobs data from '{arch_file}'.")
        else:
            self.logger.info(f"No archived jobs data found at '{arch_file}'.")

    @classmethod
    def set_log_level(cls, level: str):
        """Set the logging level for the JobsData class.

        Parameters
        ----------
        level : str
            Logging level (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
        """
        cls.logger.set_level(level)

    ##################################
    ##        Config Handling       ##
    ##################################

    def init_config(self):
        """Initialize data model with current config settings."""
        work_models = [wm.upper() == "REMOTE" for wm in self._config_model.get_value("work_models")]
        self.set_filter("work_models", "is_remote", work_models)
        job_types = self._config_model.get_value("job_types")
        self.set_filter("job_types", "job_type", job_types)
        title_exclude = self._config_model.get_value("title_exclude_selected")
        self.set_filter("title_exclude", "title", title_exclude, invert=True)
        title_require = self._config_model.get_value("title_require_selected")
        self.set_filter("title_require", "title", title_require)
        descr_exclude = self._config_model.get_value("descr_exclude_selected")
        self.set_filter("descr_exclude", "description", descr_exclude, invert=True)
        descr_require = self._config_model.get_value("descr_require_selected")
        self.set_filter("descr_require", "description", descr_require)

        sites_selected = self._config_model.get_value("sites_selected")
        self.set_rank_order("site", sites_selected, "site_score")
        degree_values = self._config_model.get_value("degree_values")
        self.set_degree_values(degree_values)
        location_order = self._config_model.get_value("location_order_selected")
        self.set_rank_order("state", location_order, "location_score")
        prioritized_terms = self._config_model.get_value("prioritized_terms_selected")
        self.set_keyword_scores(prioritized_terms, score=1)
        unprioritized_terms = self._config_model.get_value("unprioritized_terms_selected")
        self.set_keyword_scores(unprioritized_terms, score=0)
        deprioritized_terms = self._config_model.get_value("deprioritized_terms_selected")
        self.set_keyword_scores(deprioritized_terms, score=-1)

        self.display_favorites = self._config_model.get_value("display_favorites")
        self.active_days = self._config_model.get_value("max_age_days")

        self.beginResetModel()
        self.build_active_data()
        self.apply_filters()
        self.apply_sort()
        self.endResetModel()

    def update_filters(self):
        """Update data model filters from current config settings."""
        work_models = [wm.upper() == "REMOTE" for wm in self._config_model.get_value("work_models")]
        self.set_filter("work_models", "is_remote", work_models)
        job_types = self._config_model.get_value("job_types")
        self.set_filter("job_types", "job_type", job_types)
        title_exclude = self._config_model.get_value("title_exclude_selected")
        self.set_filter("title_exclude", "title", title_exclude, invert=True)
        title_require = self._config_model.get_value("title_require_selected")
        self.set_filter("title_require", "title", title_require)
        descr_exclude = self._config_model.get_value("descr_exclude_selected")
        self.set_filter("descr_exclude", "description", descr_exclude, invert=True)
        descr_require = self._config_model.get_value("descr_require_selected")
        self.set_filter("descr_require", "description", descr_require)

        rebuild_active = False
        # Recent days filter
        recent_days = self._config_model.get_value("max_age_days")
        if recent_days != self.active_days:
            self.active_days = recent_days
            rebuild_active = True
        # Favorites filter
        display_favorites = self._config_model.get_value("display_favorites")
        if display_favorites != self.display_favorites:
            self.display_favorites = display_favorites
            rebuild_active = True

        # Apply changes to data model
        self.beginResetModel()
        if rebuild_active:
            self.build_active_data()
        self.apply_filters()
        self.apply_sort()
        self.endResetModel()

    @Slot(QModelIndex, QModelIndex)
    def _on_config_changed(self, top_left: QModelIndex, bottom_right: QModelIndex):
        """Update data model sorting when config model changes."""
        val = self._config_model.get_value("sites_selected", top_left)
        if val is not None:
            self.set_rank_order("site", val, "site_score")
        val = self._config_model.get_value("degree_values", top_left)
        if val is not None:
            self.set_degree_values(val)
        val = self._config_model.get_value("location_order_selected", top_left)
        if val is not None:
            self.set_rank_order("state", val, "location_score")
        val = self._config_model.get_value("prioritized_terms_selected", top_left)
        if val is not None:
            self.set_keyword_scores(val, score=1)
        val = self._config_model.get_value("unprioritized_terms_selected", top_left)
        if val is not None:
            self.set_keyword_scores(val, score=0)
        val = self._config_model.get_value("deprioritized_terms_selected", top_left)
        if val is not None:
            self.set_keyword_scores(val, score=-1)

        # Apply changes to data model
        self.beginResetModel()
        self.apply_sort()
        self.endResetModel()

    ##################################
    ##          Collection          ##
    ##################################

    def update(self, jobs_data: pd.DataFrame):
        """Update the data model with newly collected job postings.

        Parameters
        ----------
        jobs_data : pd.DataFrame
            DataFrame containing raw collected job postings.
        """
        t_init = time.time()
        self.beginResetModel()
        if jobs_data.empty:
            self.endResetModel()
            self.logger.info("No new jobs collected.")
            return
        self._dynamic_df = jobs_data.copy()
        n_init = len(self._dynamic_df)
        # Convert raw html descriptions to markdown
        self._dynamic_df["description"] = self._dynamic_df["description"].apply(
            lambda html: self._converter.convert(html)
                         if isinstance(html, str) and len(html) > 0 else html)
        # Initialize 'is_favorite' column
        self._dynamic_df["is_favorite"] = False
        # Remove duplicate jobs from current collection
        self._dynamic_df = self.drop_duplicate_jobs(self._dynamic_df)
        # Remove jobs already in original data
        self._dynamic_df = self.drop_known_jobs(self._dynamic_df, self._original_df)
        # Count jobs found
        n_found = len(self._dynamic_df)
        self.logger.info(f"Removed {n_init - n_found} known and duplicate jobs.")
        # Ensure date_posted is in YYYY-MM-DD format
        self._dynamic_df["date_posted"] = pd.to_datetime(self._dynamic_df["date_posted"]).dt.strftime("%Y-%m-%d")
        # Add to original data and update archive file
        self._original_df = pd.concat([self._dynamic_df, self._original_df], ignore_index=True)
        archive_path = self._arch_path / "jobs_data.csv"
        self._original_df.to_csv(archive_path, index=False)
        self.logger.info(f"Updated archive at '{archive_path}'.")
        # Rebuild recent data and apply filters/sorting
        self.build_active_data()
        self.apply_filters()
        self.apply_sort()
        # Signal model reset complete
        self.endResetModel()
        self.logger.info(f"Collected {n_found} new jobs in {time.time() - t_init:.1f}s.")

    ###################################
    ## QAbstractTableModel Overrides ##
    ###################################

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
        return self._dynamic_df.shape[0]

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
                return str(self._dynamic_df.index[section])
        return None

    def data(self, index, role):
        if not index.isValid():
            return None
        col = self.columns[index.column()]
        if col not in self._dynamic_df.columns:
            return None
        val = self._dynamic_df[col].iloc[index.row()]
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

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        self._sort_column = self.columns[column]    # type: ignore
        self._sort_order = order
        self.apply_sort()

    ###################################
    ##           Filtering           ##
    ###################################

    def build_active_data(self):
        """Build the recent data DataFrame based on the specified number of days.

        Parameters
        ----------
        days : int
            Number of days to consider for recent job postings.
        """
        if self.display_favorites:
            mask = self._original_df["is_favorite"] == True  # noqa: E712
        else:
            date_cutoff = (dt.datetime.now() - dt.timedelta(self.active_days)).strftime("%Y-%m-%d")
            mask = self._original_df["date_posted"] >= date_cutoff
        self._active_df = self._original_df[mask].reset_index(drop=True)
        self._active_df = self.build_derived_columns(self._active_df)
        for col in ["company", "title"]:
            self._col_len_thresh[col] = self.calc_col_len_thresh(self._active_df, col)
        self._update_rank_order_score("site_score")
        self._update_rank_order_score("location_score")
        self._update_degree_scores()
        self._update_keyword_scores()
        self._dynamic_df = self._active_df.copy()

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
        self._filters[identifier] = (column, expression, invert)

    def apply_filters(self):
        """Apply all set filters to the dynamic DataFrame."""
        if not self._dynamic_df.empty:
            combined_mask = pd.Series(True, index=self._dynamic_df.index)
            for col, expr, inv in self._filters.values():
                mask = self.create_filter_mask(col, expr)
                if inv:
                    mask = ~mask
                combined_mask &= mask
            self._dynamic_df = self._dynamic_df[combined_mask].reset_index(drop=True)

    def create_filter_mask(self, column: str, expression: list[str]|str|bool|int|float|pd.Series|Callable) -> pd.Series:
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
        if column not in self._active_df.columns:
            self.logger.warning(f"Column '{column}' not found in DataFrame.")
            mask = pd.Series(False, index=self._active_df.index)
        elif callable(expression):
            mask = pd.Series(expression(self._active_df[column]), index=self._active_df.index).astype(bool)
        elif isinstance(expression, pd.Series):
            mask = expression.reindex(self._active_df.index).fillna(False).astype(bool)
        elif isinstance(expression, (bool, int, float)):
            mask = (self._active_df[column] == expression).fillna(False)
        elif isinstance(expression, (list, tuple, set)):
            if all(isinstance(item, (bool, int, float)) for item in expression):
                mask = self._active_df[column].isin(expression).fillna(False)
            elif all(isinstance(item, str) for item in expression):
                pattern = build_regex(expression)   # type: ignore
                mask = self._active_df[column].str.contains(pattern, case=False, na=False)
            else:
                self.logger.warning(f"Unsupported expression list types for column '{column}'.")
                mask = pd.Series(False, index=self._active_df.index)
        else:
            #Fallback: string patterns
            pattern = build_regex(expression)
            mask = self._active_df[column].str.contains(pattern, case=False, na=False)
        return mask

    ###################################
    ##            Sorting            ##
    ###################################

    def set_degree_values(self, degree_values: tuple[int, int, int]):
        """Compute degree-based priority scores.

        Parameters
        ----------
        degree_scores : tuple[int, int, int]
            Tuple of score adjustments for (bachelor, master, doctorate) degrees.
        """
        self._degree_values = degree_values

    def set_keyword_scores(self, keywords: list[str], score: int):
        """Set keyword-based priority scores.

        Parameters
        ----------
        keywords : list[str]
            List of keywords to search for in job title and description.
        score : int
            Score adjustment to apply for each matching keyword.
        """
        self._keyword_score_map[score] = keywords

    def set_rank_order(self,
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
        self._rank_orders[target_column] = (source_column, priority_map)

    def apply_sort(self):
        """Apply sorting to the dynamic DataFrame."""
        cols = self.standard_order.copy()
        ascending = [False] * len(cols)
        if self._sort_column:
            if self._sort_column in cols:
                cols.remove(self._sort_column)
            cols.insert(0, self._sort_column)
            is_asc = self._sort_order == Qt.SortOrder.AscendingOrder
            ascending = [is_asc] + [False] * (len(cols) - 1)
        self._dynamic_df.sort_values(by=cols, ascending=ascending, inplace=True, ignore_index=True)

    def _update_degree_scores(self):
        """Compute degree-based priority scores in the active DataFrame."""
        score = pd.Series(0, index=self._active_df.index)
        score += self._degree_values[0] * self._active_df["has_ba"].astype(int)
        score += self._degree_values[1] * self._active_df["has_ma"].astype(int)
        score += self._degree_values[2] * self._active_df["has_phd"].astype(int)
        self._active_df["degree_score"] = score

    def _update_keyword_scores(self):
        """Compute keyword-based priority scores in the active DataFrame."""
        score = pd.Series(0, index=self._active_df.index)
        keywords = pd.Series([[] for _ in range(len(self._active_df))], index=self._active_df.index)
        for priority, keywords_list in self._keyword_score_map.items():
            for term in keywords_list:
                mask = (self._active_df["title"].str.contains(term, case=False, na=False) |
                        self._active_df["description"].str.contains(term, case=False, na=False))
                score[mask] += priority
                for idx in self._active_df.index[mask]:
                    keywords[idx].append(term)
        keywords = keywords.apply(lambda kws: [kw.replace("\\", "") for kw in kws])
        self._active_df["keyword_score"] = score
        self._active_df["keywords"] = keywords
        self._col_len_thresh["keywords"] = self.calc_col_len_thresh(self._active_df, "keywords")

    def _update_rank_order_score(self, target_column: str):
        """Compute rank order-based priority scores in the active DataFrame.

        Parameters
        ----------
        target_column : str
            Name of the target column to update scores for.
        """
        source_column, priority_map = self._rank_orders[target_column]
        scores = self._active_df[source_column].map(priority_map).fillna(0).astype(int)
        self._active_df[target_column] = scores

    ##################################
    ##      Favorites Handling      ##
    ##################################

    def toggle_favorite(self, index: QModelIndex):
        """Toggle the 'favorite' status of the job at the given index.

        Parameters
        ----------
        index : QModelIndex
            Index of the job posting to toggle favorite status for.
        """
        row = index.row()
        row_id = self._dynamic_df.at[row, "id"]
        id_mask = self._original_df["id"] == row_id
        is_fav = self._dynamic_df.at[row, "is_favorite"]
        self._original_df.loc[id_mask, "is_favorite"] = not is_fav
        self._dynamic_df.at[row, "is_favorite"] = not is_fav
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])

    ###############################
    ##         Utilities         ##
    ###############################

    def get_job_data(self, index: QModelIndex) -> dict:
        """Get the job data as a dictionary for the given model index."""
        data = self._dynamic_df.iloc[index.row()].copy()
        data.replace({pd.NA: None, np.nan: None}, inplace=True)
        return data.to_dict()

    @staticmethod
    def drop_duplicate_jobs(df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate job postings. Keeps the first occurrence."""
        # Temporarily order jobs chronologically to keep oldest instances
        df.sort_values(by="date_posted", ascending=True, inplace=True, ignore_index=True)
        # Drop duplicates with the same job board identifier
        df.drop_duplicates(subset=["id"], keep="first", inplace=True, ignore_index=True)
        # Drop duplicates pointing to the same direct job URL
        df.drop_duplicates(subset=["job_url_direct"], keep="first", inplace=True, ignore_index=True)
        # Drop duplicates with the same company and title
        df.drop_duplicates(subset=["company", "title"], keep="first", inplace=True, ignore_index=True)
        # Drop duplicates with the same title and description
        df.drop_duplicates(subset=["title", "description"], keep="first", inplace=True, ignore_index=True)
        # Restore original order
        df.sort_values(by="date_posted", ascending=False, inplace=True, ignore_index=True)
        return df

    @staticmethod
    def drop_known_jobs(df: pd.DataFrame, parent_df: pd.DataFrame) -> pd.DataFrame:
        """Remove job postings that already exist in the parent DataFrame."""
        # Find duplicates with the same job board identifier
        dup_id = pd.merge(df, parent_df, on="id", how="inner").index
        # Find duplicates pointing to the same direct job URL
        dup_url = pd.merge(df, parent_df, on="job_url_direct", how="inner").index
        # Find duplicates with the same company and title
        dup_company = pd.merge(df, parent_df, on=["company", "title"], how="inner").index
        # Find duplicates with the same title and description
        dup_description = pd.merge(df, parent_df, on=["title", "description"], how="inner").index
        # Drop identified duplicates
        dup_rows = dup_id.union(dup_url).union(dup_company).union(dup_description)
        df.drop(index=dup_rows, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    @staticmethod
    def build_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Build derived columns in the DataFrame."""
        if df.empty:
            return df
        # Parse locations into city and state
        df["city"], df["state"] = zip(*df["location"].map(parse_location))
        # Add degree existence columns
        has_degrees = df["description"].map(parse_degrees)
        df["has_ba"], df["has_ma"], df["has_phd"] = zip(*has_degrees)
        return df

    @staticmethod
    def calc_col_len_thresh(df: pd.DataFrame, col: str, method: str = "iqr") -> int:
        """Calculate string length threshold for wrapping long text in the specified column."""
        if len(df[col]) == 0:
            return 80
        if isinstance(df[col].iloc[0], list):
            item_len = df[col].apply(
                lambda strings: sum(len(str(v)) for v in strings) + (2 * (len(strings) - 1)))
        else:
            item_len = df[col].str.len()
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
