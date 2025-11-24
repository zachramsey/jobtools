__all__ = ["HTMLBuilder"]


import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_string_dtype

# Behold my assortment of unicode arrows!
# ⧫ ▲ ▼ | 🮮 🮦 🮧 | 🡙 🡑 🡓 | ↕ ↑ ↓ | ⭥ ⭡ ⭣ | ⮁ ⮅ ⮇ | ◆ ⏶ ⏷ ⬘ ⬙ | ⇕ ⇑ ⇓ | ⇳ ⇧ ⇩ | ⥮ ⥣ ⥥ | ⬍ 🠭 🠯
# 🠁 🠃 | 🠑 🠓 | 🠕 🠗 | 🠅 🠇 | 🠡 🠣 | 🠥 🠧 | 🠙 🠛 | 🠩 🠫 | 🠝 🠟 | 🠉 🠋 | 🠱 🠳 | 🡅 🡇 | 🡡 🡣 | 🡩 🡫 | 🡱 🡳 | 🡹 🡻 | 🢁 🢃

# HTML boilerplate for exported job table
HTML_OPEN = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Postings</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
  </head>
  <body>
    <style type="text/css">
      body {
        margin: 0;
        padding: 20px;
        background-color: #282828;
        font-family: "Roboto", sans-serif;
        font-optical-sizing: auto;
        font-weight: 400;
        font-style: normal;
        font-variation-settings: "wdth" 100;
        font-size: 16px;
        color: #FFFFFF;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        border-radius: 8px;
        overflow: hidden;
        background-color: #323232;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
      }
      tr {
        background-color: #323232;
      }
      tr:nth-child(even) td {
        background-color: #2C2C2C;
      }
      th {
        padding: 8px 10px;
        text-align: left;
        font-weight: 600;
        background-color: #1E1E1E;
        user-select: none;
        position: relative;
        vertical-align: middle;
      }
      .sort-widget {
        position: absolute;
        left: 8px;
        top: 50%;
        transform: translateY(-50%);
        display: flex;
        flex-direction: column;
        align-items: center;
        line-height: 1;
      }
      .sort-arrow {
        cursor: pointer;
        font-size: 10px;
        padding: 1px;
        transition: color 0.2s;
      }
      .sort-arrow.inactive {
        color: #464646;
      }
      .sort-arrow.active {
        color: #FFFFFF;
      }
      .sort-arrow:hover {
        color: #3F638B;
      }
      .sort-rank {
        font-size: 12px;
        font-weight: bold;
        color: #FFFFFF;
        min-height: 12px;
        margin: -2px 0 -4px 0;
      }
      td {
        padding: 8px 10px;
        text-align: left;
      }
      a {
        color: #419CFF;
        text-decoration: none;
      }
      a:visited {
        color: #7858DD;
      }
    </style>
"""

SCRIPT = """
    <script>
      /**
       * Updates visuals (arrows and rank numbers) based on hierarchy.
       */
      function updateHeaderVisuals(table) {
        table.querySelectorAll('th[data-sort-key]').forEach(th => {
          const colIndex = th.cellIndex;
          const sortState = table._sortHierarchy.find(s => s.index === colIndex);
          
          const upArrow = th.querySelector('.sort-arrow.up');
          const downArrow = th.querySelector('.sort-arrow.down');
          const rankSpan = th.querySelector('.sort-rank');
          
          // Reset all
          upArrow.classList.remove('active');
          downArrow.classList.remove('active');
          upArrow.classList.remove('inactive');
          downArrow.classList.remove('inactive');
          rankSpan.textContent = ''; // Clear rank

          if (sortState) {
            // It is in the hierarchy
            if (sortState.dir === 'asc') {
              upArrow.classList.add('active');
              downArrow.classList.add('inactive');
            } else {
              downArrow.classList.add('active');
              upArrow.classList.add('inactive');
            }
            
            // Set the rank number (1-based index)
            const rank = table._sortHierarchy.indexOf(sortState) + 1;
            rankSpan.textContent = rank;
          }
        });
      }

      /**
       * Performs the multi-column sort.
       */
      function performSort(table) {
        const tableBody = table.querySelector('tbody');
        const sortHierarchy = table._sortHierarchy;

        if (sortHierarchy.length === 0) {
          tableBody.append(...table._originalRows);
          return;
        }

        const rows = Array.from(tableBody.querySelectorAll('tr'));

        rows.sort((rowA, rowB) => {
          for (const sortCol of sortHierarchy) {
            const colIndex = sortCol.index;
            const sortKey = sortCol.key;
            const dir = sortCol.dir;

            const cellA = rowA.querySelectorAll('td')[colIndex];
            const cellB = rowB.querySelectorAll('td')[colIndex];

            let valueA, valueB;
            if (sortKey === 'text') {
              valueA = cellA.textContent.trim().toLowerCase();
              valueB = cellB.textContent.trim().toLowerCase();
            } else {
              valueA = cellA.dataset[sortKey];
              valueB = cellB.dataset[sortKey];
            }

            const isNumeric = !isNaN(parseFloat(valueA)) && !isNaN(parseFloat(valueB));
            let comparison = 0;
            if (isNumeric) {
              comparison = parseFloat(valueA) - parseFloat(valueB);
            } else {
              comparison = valueA.localeCompare(valueB);
            }
            
            if (comparison !== 0) {
              return comparison * (dir === 'asc' ? 1 : -1);
            }
          }
          return 0;
        });

        tableBody.append(...rows);
      }

      /**
       * Handles specific arrow clicks.
       */
      function handleSortClick(table, header, direction) {
        const columnIndex = header.cellIndex;
        const sortKey = header.dataset.sortKey;
        
        // Find if this column is already in hierarchy
        const colStateIndex = table._sortHierarchy.findIndex(s => s.index === columnIndex);
        
        if (colStateIndex > -1) {
          // Column is active
          const currentState = table._sortHierarchy[colStateIndex];
          
          if (currentState.dir === direction) {
            // Clicked the SAME direction -> Deselect (Remove)
            table._sortHierarchy.splice(colStateIndex, 1);
          } else {
            // Clicked the OPPOSITE direction -> Swap direction, keep rank
            currentState.dir = direction;
          }
        } else {
          // Column is not active -> Add to end of hierarchy
          table._sortHierarchy.push({
            index: columnIndex,
            key: sortKey,
            dir: direction
          });
        }

        updateHeaderVisuals(table);
        performSort(table);
      }

      // Initialization
      document.addEventListener('DOMContentLoaded', () => {
        const table = document.getElementById('myTable');
        if (!table) return;

        const tableBody = table.querySelector('tbody');
        table._originalRows = Array.from(tableBody.querySelectorAll('tr'));
        table._sortHierarchy = [];

        // Attach listeners to the ARROWS, not the header
        table.querySelectorAll('th[data-sort-key]').forEach(header => {
          
          const upArrow = header.querySelector('.sort-arrow.up');
          const downArrow = header.querySelector('.sort-arrow.down');
          
          upArrow.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent bubbling
            handleSortClick(table, header, 'asc');
          });
          
          downArrow.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent bubbling
            handleSortClick(table, header, 'desc');
          });
        });
      });
    </script>
"""


class HTMLBuilder:
    """ Class for building HTML exports of job postings.
    """

    def __init__(self, data: pd.DataFrame):
        """ Initialize HTMLBuilder.

        Parameters
        ----------
        data : pd.DataFrame
            DataFrame containing job postings.
        """
        self._data = data.copy()

    def build_html(self,
                   headers: dict[str, str],
                   keys: dict[str, str]) -> str:
        """ Build the HTML export string.

        Parameters
        ----------
        headers : dict[str, str]
            Mapping of column names to their display headers.
        keys : dict[str, str]
            Mapping of column names to associated columns used as sort keys.

        Returns
        -------
        str
            HTML string representing the job postings table.
        """
        # Process each column for HTML formatting
        config = {}
        for val_col, val_hdr in headers.items():
            # Add column to config
            key_col = keys.get(val_col, "")
            if key_col:
                self._data[f"{key_col}_key"] = self._data[key_col].copy()
                key_col = f"{key_col}_key"
            config[val_col] = (val_hdr, key_col)
            # Handle different data types
            if self._data[val_col].dtype == bool:
                # Boolean case
                self._data[val_col] = self._data[val_col].apply(lambda v: "✕" if v else "")
            elif is_datetime64_any_dtype(self._data[val_col]):
                # Datetime case
                if key_col and is_datetime64_any_dtype(self._data[key_col]):
                    self._data[key_col] = self._data[key_col].fillna(pd.Timestamp.min).astype(int) // 10**9
                self._data[val_col] = self._data[val_col].dt.strftime("%m/%d").fillna("")
            elif is_string_dtype(self._data[val_col]) and self._data[val_col].str.startswith("http", na=False).any():
                # URL case
                url_series = self._data[val_col]
                label_series = self._data[key_col] if key_col else pd.Series(["link"] * len(url_series))
                self._data[val_col] = url_series.combine(label_series, lambda url, label:
                      f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'
                      if pd.notna(url) and url.startswith("http") else "")
            else:
                # Default case
                self._data[val_col] = self._data[val_col].fillna("")
            
            # Wrap values in <td> with optional sorting attribute
            if key_col:
                # Add data-* attribute for sorting
                self._data[val_col] = self._data.apply(
                    lambda row: f'<td data-{key_col}="{row[key_col]}">{row[val_col]}</td>',
                    axis=1)
            else:
                # No sorting attribute
                self._data[val_col] = self._data[val_col].apply(lambda v: f"<td>{v}</td>")

        # Initialize HTML string
        html = HTML_OPEN
        html += '    <table id="myTable">\n'
        html += "      <thead>\n"
        html += "        <tr>\n"

        # Build table headers
        for val_hdr, key_col in config.values():
            if key_col:
                html += f'          <th data-sort-key="{key_col}" style="padding-left: 32px;">\n'
                html += '             <div class="sort-widget">\n'
                html += '               <span class="sort-arrow up">🮧</span>\n'
                html += '               <span class="sort-rank"></span>\n'
                html += '               <span class="sort-arrow down">🮦</span>\n'
                html += '             </div>\n'
            else:
                html += f"          <th>\n"

            html += f'                {val_hdr}\n'
            html += f'              </th>\n'

        html += "        </tr>\n"
        html += "      </thead>\n"
        html += "      <tbody>\n"

        # Build table rows
        for _, row in self._data.iterrows():
            html += "        <tr>\n"
            for val_col in config.keys():
                html += f"          {row[val_col]}\n"
            html += "        </tr>\n"

        html += "      </tbody>\n"
        html += "    </table>\n"
        html += SCRIPT
        html += "  </body>\n"
        html += "</html>\n"

        return html
