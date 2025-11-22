from config.config import Config

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

class SaveToJSONPipeline(Config):

    def __init__(self):

        self.parquet_root = Config.NPS_CONTEXT_PARQUET_PATH

    def storage_workflow(self, context_windows_dict_batch):

        df = pd.DataFrame(context_windows_dict_batch)

        table = pa.Table.from_pandas(df, preserve_index=False)

        # partition by company (allows effective queueing by company)
        pq.write_to_dataset(table, root_path=self.parquet_root, partition_cols=["company"])

        return None
    