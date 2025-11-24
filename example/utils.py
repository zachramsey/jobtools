import datetime as dt
import os
import pandas as pd
import re
from jobtools import JobsData
from jobtools.cluster import TopicExtractor
from jobtools.process import split_sections, get_label
from jobtools.utils import JTLogger
from filters import (JOB_TYPE_OMIT, JOB_LVL_OMIT,
                     TITLE_REQ, TITLE_OMIT,
                     DESC_REQ, DESC_OMIT)
from priorities import KEYWORD_VALUE_MAP, STATE_RANK_ORDER


def filter_jobs(jobs: JobsData):
    """ Apply filtering criteria to job postings DataFrame.

    Parameters
    ----------
    jobs : JobsData
        JobsData instance containing job postings.
    """
    logger = JTLogger()
    start = dt.datetime.now()
    n_init = len(jobs)

    # Preliminary column filters
    n_rem = jobs.omit("job_type", JOB_TYPE_OMIT)
    logger.info(f"Removed {n_rem} with job type filter")
    n_rem = jobs.omit("job_level", JOB_LVL_OMIT)
    logger.info(f"Removed {n_rem} with job level filter")

    n_rem = len(jobs)
    jobs = jobs[~jobs["is_remote"]]
    n_rem -= len(jobs)
    logger.info(f"Removed {n_rem} with remote filter")

    # Title filters
    n_rem = jobs.omit("title", TITLE_OMIT)
    logger.info(f"Removed {n_rem} with title filter")
    n_rem = jobs.require("title", TITLE_REQ)
    logger.info(f"Removed {n_rem} with title requirements")

    # Description filters
    n_rem = jobs.omit("description", DESC_OMIT)
    logger.info(f"Removed {n_rem} with description filter")
    n_rem = jobs.require("description", DESC_REQ)
    logger.info(f"Removed {n_rem} with description requirements")

    # Conditional degree requirement filter
    n_init = len(jobs)
    jobs = jobs[~((jobs["has_master"] | jobs["has_doctorate"]) & ~jobs["has_bachelor"])]
    logger.info(f"Removed {n_init - len(jobs)} requiring advanced degree")

    # Final prioritization and deduplication
    jobs.prioritize(KEYWORD_VALUE_MAP, STATE_RANK_ORDER,
                    ["LinkedIn", "Indeed"], "bachelor")
    n_rem = jobs.deduplicate()
    logger.info(f"Removed {n_rem} duplicates")

    diff = n_init - len(jobs)
    dur = (dt.datetime.now() - start).total_seconds()
    logger.info(f"Removed {diff} jobs in {dur:.1f}s")

    return jobs


def cluster_jobs(jobs: JobsData):
    """ Cluster job postings and extract topics.    

    Parameters
    ----------
    jobs : JobsData
        JobsData instance containing job postings.
    out_dir : str, optional
        Output directory for saving results, by default "output".
    """
    logger = JTLogger()
    logger.info("Beginning job clustering...")

    # Prepare job descriptions for topic extraction
    start = dt.datetime.now()
    relevant_sections = ["REQUIRED", "PREFERRED", "QUALIFICATIONS"]
    data = []
    for desc in jobs["description"]:
        if isinstance(desc, str) and len(desc) > 0:
            sections = split_sections(desc)
            data.append("\n\n".join([content for (header, content) in sections
                                    if get_label(header) in relevant_sections]))
    dur = (dt.datetime.now() - start).total_seconds()
    logger.info(f"Prepared {len(data)} descriptions in {dur:.1f}s")

    # Extract topics from job postings data
    start = dt.datetime.now()
    extractor = TopicExtractor()
    topics, probs = extractor.extract_topics(data)
    topic_info = extractor.topic_model.get_topic_info()
    dur = (dt.datetime.now() - start).total_seconds()
    logger.info(f"Extracted {len(topic_info)-1} topics in {dur:.1f}s")

    # Save topic details
    if not os.path.exists(jobs.path):
        os.makedirs(jobs.path)
    topic_details = {}
    for topic in topic_info["Topic"]:
        if topic == -1:
            continue
        topic_details[topic] = extractor.topic_model.get_topic(topic)
    with open(f"{jobs.path}/topics_details.txt", "w") as f:
        for topic, words in topic_details.items():
            f.write(f"Topic {topic}:\n")
            for word, weight in words:
                f.write(f"  {word}: {weight:.4f}\n")
            f.write("\n")
    logger.info("Saved topic details")

    # Visualize topics
    topics_figure = extractor.topic_model.visualize_topics()
    topics_figure.write_html(f"{jobs.path}/topics_overview.html")
    hierarchy_figure = extractor.topic_model.visualize_hierarchy()
    hierarchy_figure.write_html(f"{jobs.path}/topics_hierarchy.html")
    logger.info("Saved topic visualizations")
