import datetime as dt
from jobtools import JobsData
from jobtools.utils import clean_description
from proxy import PROXY
from queries import SEARCH_STRINGS
from priorities import KEYWORD_VALUE_MAP, STATE_RANK_ORDER
from filters import JOB_TYPE_OMIT, JOB_LVL_OMIT
from filters import TITLE_REQ, TITLE_OMIT
from filters import DESC_REQ, DESC_OMIT


us = ["United States"]
iowa = ["Iowa, United States"]
seattle = ["Greater Seattle Area"]
tech = ["Greater Seattle Area", "San Francisco Bay Area"]
west = tech + ["Portland, Oregon Metropolitan Area"]
states = ["Washington, United States", "Oregon, United States",
          "California, United States", "Texas, United States",
          "Massachusetts, United States", "Virginia, United States",
          "Maryland, United States", "New York, United States"]

locations = us
results_wanted = 10000
hours_old = 24 * 1

# Options:
#                "" -> do not load previous data
#          "recent" -> load most recent output directory
#          "global" -> load global jobs_data.csv
# "output/{subdir}" -> load specified subdirectory
load_data: str = "recent"

save_raw: bool = True
update_global: bool = True

scrape: bool = True
filter: bool = True
export: bool = True


if __name__ == "__main__":
    # Configure logging
    JobsData.set_log_level("INFO")

    # Initialize job collector
    jobs = JobsData().from_csv(source=load_data)

    if scrape:
        # Collect job postings
        for group, search in SEARCH_STRINGS.items():
            # Collect job postings for this group
            start = dt.datetime.now()
            n_jobs = jobs.collect(site_name=["LinkedIn", "Indeed"],
                                  search_term=search,
                                  job_type="fulltime",
                                  locations=locations,
                                  results_wanted=results_wanted,
                                  proxy=PROXY,
                                  hours_old=hours_old)
            dur = (dt.datetime.now() - start).total_seconds()
            jobs.logger.info(f"{group} > Collected {n_jobs} job postings in {dur:.1f}s")

            # Prioritize and deduplicate after collection
            jobs.prioritize(KEYWORD_VALUE_MAP, STATE_RANK_ORDER,
                            ["LinkedIn", "Indeed"], (5, -3, -3))
            n_rem = jobs.deduplicate()
            jobs.logger.info(f"{group} > Removed {n_rem} duplicate job postings") 
            jobs.logger.info(f"{group} > Found {n_jobs - n_rem} unique job postings")

            # Write local csv for this group
            if save_raw:
                jobs.export_csv()

    # Update global data
    if update_global:
        # Load global data and update with current jobs
        g_jobs = JobsData().from_csv(source="global")
        g_jobs.update(jobs)
        # Prioritize and deduplicate global data after update
        g_jobs.prioritize(KEYWORD_VALUE_MAP, STATE_RANK_ORDER,
                          ["LinkedIn", "Indeed"], (5, -3, -3))
        n_rem = g_jobs.deduplicate()
        g_jobs.logger.info(f"Global > Removed {n_rem} duplicate job postings")
        # Write updated global data
        g_jobs.export_csv()

    # Clean markdown descriptions
    jobs["description"] = jobs["description"].apply(clean_description)
    jobs.logger.info(f"Cleaned {len(jobs)} descriptions")

    if filter:
        # Filter job postings
        start = dt.datetime.now()
        n_init = len(jobs)

        # Preliminary column filters
        n_rem = jobs.omit("job_type", JOB_TYPE_OMIT)
        jobs.logger.info(f"Removed {n_rem} with job type filter")
        n_rem = jobs.omit("job_level", JOB_LVL_OMIT)
        jobs.logger.info(f"Removed {n_rem} with job level filter")
        n_rem = len(jobs)
        jobs = jobs[~jobs["is_remote"]]
        jobs.logger.info(f"Removed {n_rem - len(jobs)} with remote filter")

        # Conditional degree requirement filter
        n_rem = len(jobs)
        jobs = jobs[~((jobs["has_master"] | jobs["has_doctorate"]) & ~jobs["has_bachelor"])]
        jobs.logger.info(f"Removed {n_rem - len(jobs)} requiring advanced degree")

        # Title filters
        n_rem = jobs.omit("title", TITLE_OMIT)
        jobs.logger.info(f"Removed {n_rem} with title filter")
        n_rem = jobs.require("title", TITLE_REQ)
        jobs.logger.info(f"Removed {n_rem} with title requirements")

        # Description filters
        n_rem = jobs.omit("description", DESC_OMIT)
        jobs.logger.info(f"Removed {n_rem} with description filter")
        n_rem = jobs.require("description", DESC_REQ)
        jobs.logger.info(f"Removed {n_rem} with description requirements")

        diff = n_init - len(jobs)
        dur = (dt.datetime.now() - start).total_seconds()
        jobs.logger.info(f"Removed {diff} jobs in {dur:.1f}s")

    if export:
        # Save results to html
        jobs["keyword_score"], jobs["keywords"] = jobs.keyword_score(KEYWORD_VALUE_MAP)
        jobs["degree_score"] = jobs.degree_score((5, -3, -3))
        jobs["location_score"] = jobs.rank_order_score("state", STATE_RANK_ORDER)
        path = jobs.export_html(
            headers={"date_posted": "Date",
                     "state": "State",
                     "company": "Company",
                     "title": "Title",
                     "has_bachelor": "BS",
                     "has_master": "MS",
                     "has_doctorate": "PhD",
                     "keywords": "Keywords",
                     "job_url": "URL"},
            keys={"date_posted": "date_posted",
                  "state": "location_score",
                  "company": "company",
                  "title": "title",
                  "has_bachelor": "degree_score",
                  "keywords": "keyword_score",
                  "job_url": "site"},
        )
