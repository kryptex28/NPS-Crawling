from pathlib import Path

from nps_crawling.classification.evaluation_summary import (
    extract_evaluation_results_from_configurations,
)

df = extract_evaluation_results_from_configurations(print_highlights=True)
df.to_csv("evaluation_results.csv", index=False)

# Or a custom tree:
#df = extract_evaluation_results_from_configurations(Path("path/to/configurations"))

# Your own analysis on the long-format table, e.g.:
#best = df.groupby("model_name")["weighted_f1"].mean().sort_values(ascending=False)