I know these should be set up as issues. I'm not there yet :)

- [Bug] Automatically refresh data source selector and table view when new data collected
- [Optimization] Cache data during runtime (enable/disable in settings)
    - Advantage: much quicker data source browsing
    - Caveat: larger memory footprint, changes to filter/sort settings will require recalculation
- [Optimization] Make derived columns persistent (save with csv)
    - Advantage: Should improve data loading speed
    - Caveat: any changes to derived column creation logic would necessitate recalculating; some increase to storage size
- [Enhancement] Combine CollectionWorker into JobsData
- [Enhancement] Set up data handling as monolithic data set (current the archive); easier data management and may be helpful for detecting re-posted jobs
- [Enhancement] Single source of truth for jobs; keep track of when a given job is posted across multiple sites and dates in a single record. That is, if a known job is scraped in a unique format, save the associated differing information like site and date. Look into also keeping track of differing job ids, locations, levels, remote status, and compensation. Then, when that unique instance is scraped, the new information will be displayed, but evidence of existing records can be indicated in-line and provided in details.
- [Feature] Options for grouping job listings
- [Feature] Theme options in settings
- [Feature] Once more specific information is being parsed from jobs, provide a means for users to customize which fields are displayed in the data table.
