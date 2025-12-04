"""Storage pipeline to save context windows to Parquet files."""

import os

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from nps_crawling.config import Config


class SaveToJSONPipeline(Config):
    """Storage pipeline to save context windows to Parquet files."""
    def __init__(self):
        """Initialize the storage pipeline."""
        self.parquet_root = Config.NPS_CONTEXT_PARQUET_PATH

    def storage_workflow(self, context_windows_dict_batch):
        """Store a batch of context windows into Parquet files partitioned by company."""
        df = pd.DataFrame(context_windows_dict_batch)

        table = pa.Table.from_pandas(df, preserve_index=False)

        # partition by company (allows effective queueing by company)
        pq.write_to_dataset(table, root_path=self.parquet_root, partition_cols=["company"])

        return None

    def count_parquet_files(self):
        """For logging only."""
        count = 0
        for root, dirs, files in os.walk(self.parquet_root):
            count += sum(1 for f in files if f.endswith(".parquet"))
        return count
