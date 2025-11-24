import datetime as dt
import os

from jobtools import JobsData
from jobtools.cluster import TopicExtractor
from jobtools.utils import get_label, parse_description

from filters import JOB_TYPE_OMIT, JOB_LVL_OMIT
from filters import TITLE_REQ, TITLE_OMIT
from filters import DESC_REQ, DESC_OMIT


def filter_jobs(jobs: JobsData):
    """ Apply filtering criteria to job postings DataFrame.

    Parameters
    ----------
    jobs : JobsData
        JobsData instance containing job postings.
    """
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
    jobs.logger.info("Beginning job clustering...")

    # Prepare job descriptions for topic extraction
    start = dt.datetime.now()
    relevant_sections = ["REQUIRED", "PREFERRED", "QUALIFICATIONS"]
    data = []
    for desc in jobs["description"]:
        if isinstance(desc, str) and len(desc) > 0:
            sections = parse_description(desc)
            data.append("\n\n".join([content for (header, content) in sections
                                    if get_label(header) in relevant_sections]))
    dur = (dt.datetime.now() - start).total_seconds()
    jobs.logger.info(f"Prepared {len(data)} descriptions in {dur:.1f}s")

    # Extract topics from job postings data
    start = dt.datetime.now()
    extractor = TopicExtractor()
    topics, probs = extractor.extract_topics(data)
    topic_info = extractor.topic_model.get_topic_info()
    dur = (dt.datetime.now() - start).total_seconds()
    jobs.logger.info(f"Extracted {len(topic_info)-1} topics in {dur:.1f}s")

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
    jobs.logger.info("Saved topic details")

    # Visualize topics
    topics_figure = extractor.topic_model.visualize_topics()
    topics_figure.write_html(f"{jobs.path}/topics_overview.html")
    hierarchy_figure = extractor.topic_model.visualize_hierarchy()
    hierarchy_figure.write_html(f"{jobs.path}/topics_hierarchy.html")
    jobs.logger.info("Saved topic visualizations")
