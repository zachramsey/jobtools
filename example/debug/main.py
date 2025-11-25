from math import log
import os
import pandas as pd

from jobtools import JobsData
from jobtools.utils import clean_description, get_label
from jobtools.utils.description_parser import format_mapping, extract_headers, generate_description_debug_str


# Configuration flags
outlier_quantile = None

save_inlier_descriptions = True
save_outlier_descriptions = True

save_inlier_formatted = True
save_outlier_formatted = True

save_inlier_headers = False
save_outlier_headers = False

save_label_frequencies = False
save_header_frequencies = False


if __name__ == "__main__":
    # Configure logging
    JobsData.set_log_level("INFO")

    # Initialize job collector
    jobs = JobsData().from_csv(source="global")
    desc = jobs.data[["description"]]

    # Prepare output directory
    out_dir = jobs._new_path
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # Clean markdown descriptions
    desc["description_clean"] = desc["description"].apply(clean_description)
    jobs.logger.info(f"Cleaned {len(desc)} descriptions")

    # Extract headers from descriptions
    desc["headers"] = desc["description_clean"].apply(extract_headers)
    desc["headers"] = desc["headers"].apply(
        lambda hdrs: [hdr.lower() for hdr in hdrs])

    # Label each header list
    desc["labels"] = desc["headers"].apply(
        lambda hdrs: [get_label(hdr) for hdr in hdrs]
    )

    # Explode lists of headers and labels into separate rows
    hl = desc[["headers", "labels"]]
    hl = hl.explode(["headers", "labels"]).reset_index(drop=True)
    # Map headers to labels
    hdr_lbls = hl.drop_duplicates(subset=["headers"]).set_index("headers")["labels"].to_dict()
    # Count header frequencies
    hl_hdr_counts = hl["headers"].value_counts().to_frame(name="count")
    hl_hdr_counts["label"] = hl_hdr_counts.index.map(hdr_lbls)
    hl_hdr_counts = hl_hdr_counts.sort_values(by=["label", "count"], ascending=[True, False])
    hl_hdr_counts["count_label"] = list(zip(hl_hdr_counts["count"], hl_hdr_counts["label"]))
    hdr_counts = hl_hdr_counts["count_label"].to_dict()
    # Count label frequencies
    lbl_counts = hl["labels"].value_counts().to_dict()

    # Compute per-description metrics and outlier score
    desc["n_headers"] = desc["headers"].apply(len)
    desc["n_labeled"] = desc["labels"].apply(
        lambda lbls: sum(min(1, len(lbl)) for lbl in lbls))
    desc["n_unlabeled"] = desc["n_headers"] - desc["n_labeled"]
    desc["score"] = desc["headers"].apply(
        lambda hdrs: sum(
            -log(max(hdr_counts.get(hdr, (1.0, ""))[0] / len(desc), 1e-6))
            for hdr in hdrs
        ) / len(desc)
    )

    # Create header-label debug strings
    desc["headers_str"] = desc.apply(
        lambda row: format_mapping(row["headers"], row["labels"]),
        axis=1
    )

    # Identify outliers
    if outlier_quantile is not None:
        upper_threshold = desc["score"].quantile(outlier_quantile)
    else:
        lq = desc["score"].quantile(0.25)
        uq = desc["score"].quantile(0.75)
        upper_threshold = lq + 1.5 * (uq - lq)
        inliers = desc[desc["score"] < upper_threshold]
        inliers = inliers.sort_values(by="score")
        outliers = desc[desc["score"] >= upper_threshold]
        outliers = outliers.sort_values(by="score", ascending=False)

    if save_inlier_descriptions:
        # Save inlier descriptions
        with open(os.path.join(out_dir, "inlier_descriptions.txt"), "w", encoding="utf-8") as f:
            for i, description in enumerate(inliers["description"]):
                f.write(f"{'=' * 80}\n")
                f.write(f"Description {i + 1}:\n\n")
                f.write(f"{description}\n\n")

    if save_outlier_descriptions:
        # Save outlier descriptions
        with open(os.path.join(out_dir, "outlier_descriptions.txt"), "w", encoding="utf-8") as f:
            for i, description in enumerate(outliers["description"]):
                f.write(f"{'=' * 80}\n")
                f.write(f"Description {i + 1}:\n\n")
                f.write(f"{description}\n\n")

    if save_inlier_formatted:
        # Save inlier descriptions
        with open(os.path.join(out_dir, "inlier_formatted.txt"), "w", encoding="utf-8") as f:
            for i, description in enumerate(inliers["description_clean"]):
                f.write(f"{'=' * 80}\n")
                f.write(f"Description {i + 1}:\n\n")
                f.write(f"{generate_description_debug_str(description)}\n\n")

    if save_outlier_formatted:
        # Save outlier descriptions
        with open(os.path.join(out_dir, "outlier_formatted.txt"), "w", encoding="utf-8") as f:
            for i, description in enumerate(outliers["description_clean"]):
                f.write(f"{'=' * 80}\n")
                f.write(f"Description {i + 1}:\n\n")
                f.write(f"{generate_description_debug_str(description)}\n\n")

    if save_inlier_headers:
        # Save inlier headers
        with open(os.path.join(out_dir, "inlier_headers.txt"), "w", encoding="utf-8") as f:
            for i, row in enumerate(inliers.itertuples(index=False)):
                f.write(f"{'=' * 80}\n")
                f.write(f"Description {i + 1}:\n\n")
                f.write(f"{str(row.headers_str)}\n\n")

    if save_outlier_headers:
        # Save outlier headers
        with open(os.path.join(out_dir, "outlier_headers.txt"), "w", encoding="utf-8") as f:
            for i, row in enumerate(outliers.itertuples(index=False)):
                f.write(f"{'=' * 80}\n")
                f.write(f"Description {i + 1} | Headers: {row.n_headers} | Labeled: {row.n_labeled} | Unlabeled: {row.n_unlabeled} | Score: {row.score:.4f}\n\n")
                f.write(f"{str(row.headers_str)}\n\n")

    if save_label_frequencies:
        # Save label frequency counts
        with open(os.path.join(out_dir, "label_frequencies.txt"), "w", encoding="utf-8") as f:
            f.write(f"{'=' * 80}\n")
            f.write("Label Frequencies:\n\n")
            for label, count in lbl_counts.items():
                f.write(f"{count:>6} | {count/len(hl):>7.2%} | {label}\n")

    if save_header_frequencies:
        # Save header frequency counts
        with open(os.path.join(out_dir, "header_frequencies.txt"), "w", encoding="utf-8") as f:
            f.write(f"{"=" * 80}\n")
            f.write("Header Frequencies:\n\n")
            curr_label = ""
            for header, (count, label) in hdr_counts.items():
                if label != curr_label:
                    curr_label = label
                    f.write(f"\n{'-' * 40}\n")
                    f.write(f"{curr_label}\n\n")
                f.write(f"{count:>6} | {header}\n")

    # # Extract and analyze topics from headers
    # extractor = TopicExtractor()
    # topics, probs = extractor.extract_topics(hdr_counts.index.tolist())
    # topic_info = extractor.topic_model.get_topic_info()

    # # Save topic details
    # topic_details = {}
    # for topic in topic_info["Topic"]:
    #     if topic == -1:
    #         continue
    #     topic_details[topic] = extractor.topic_model.get_topic(topic)
    # with open(out_dir/"topic_details.txt", "w", encoding="utf-8") as f:
    #     for topic, words in topic_details.items():
    #         f.write(f"Topic {topic}:\n")
    #         for word, weight in words:
    #             f.write(f"  {word}: {weight:.4f}\n")
    #         f.write("\n")

    # # Visualize topics
    # topics_figure = extractor.topic_model.visualize_topics()
    # topics_figure.write_html(out_dir/"topics.html")
    # hierarchy_figure = extractor.topic_model.visualize_hierarchy()
    # hierarchy_figure.write_html(out_dir/"hierarchy.html")
