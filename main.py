import pandas as pd
from jobtools.jobsdata import deduplicate
from jobtools.process import clean_description, generate_header_debug_str
from jobtools.analysis import header_analysis
from jobtools.utils import JTLogger


def main():
    logger = JTLogger()
    logger.configure("INFO")
    src_file = "output/jobs_data.csv"
    snk_file = "output/description_headers.txt"
    df = pd.read_csv(src_file)
    # df["clean"] = df["description"].apply(clean_md)
    # df["headers"] = df["clean"].apply(get_debugging)

    logger.info(f"Loaded {len(df)} descriptions.")
    df, n_rem = deduplicate(df)
    df = df.reset_index(drop=True)
    logger.info(f"Removed {n_rem} duplicates.")
    logger.info(f"{len(df)} unique descriptions remain.")

    # df["description"] = df["description"].apply(clean_md)
    # with open("output/description_texts.txt", "w", encoding="utf-8") as f:
    #     for desc in df["description"]:
    #         f.write("\n\n" + "-" * 60 + "\n\n")
    #         f.write(desc)

    # Remove empty descriptions
    df = df[df["description"].notna()].reset_index(drop=True)

    header_analysis(
        texts=df["description"],
        out_dir="output",
    )

    # # output descriptions to text file
    # with open(snk_file, "w", encoding="utf-8") as f:
    #     for headers in df["headers"]:
    #         f.write("\n\n" + "-" * 60 + "\n\n")
    #         f.write(headers)

if __name__ == "__main__":
    main()
