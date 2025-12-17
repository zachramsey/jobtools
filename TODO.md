I know these should be set up as issues. I'm not there yet :)

- [Bug] Automatically refresh data source selector and table view when new data collected
- [Optimization] Cache data during runtime (enable/disable in settings)
    - Advantage: much quicker data source browsing
    - Caveat: larger memory footprint, changes to filter/sort settings will require recalculation
- [Optimization] Make derived columns persistent (save with csv)
    - Advantage: Should improve data loading speed
    - Caveat: any changes to derived column creation logic would necessitate recalculating; some increase to storage size
- [Enhancement] Automatically switch to console page on collection start
- [Enhancement] Set up data handling as monolithic data set (current the archive); easier data management and may be helpful for detecting re-posted jobs
- [Feature] Options for grouping job listings
- [Feature] Theme options in settings
