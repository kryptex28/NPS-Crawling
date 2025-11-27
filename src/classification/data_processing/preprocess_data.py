from src.config import Config
import pyarrow.dataset as ds

class ClassificationDataProcessing(Config):
  
    def __init__(self):

        self.parquet_root = Config.NPS_CONTEXT_PARQUET_PATH

        # the dataset object used by PyArrow. expects that dataset is partioned by "company"
        self._dataset = ds.dataset(
            self.parquet_root,
            format="parquet",
            partitioning="hive",
        )

    def get_list_of_all_companies(self):
        """
        reads only the company column across all partitions to increase performance

        output: unique list of all companies currently stored
        """
        table = self._dataset.to_table(columns=["company"])
        companies = table["company"].to_pylist()
        
        return sorted({c for c in companies if c is not None})

    def get_data_for_classification(self, company):
        """
        checks which partition directories match company from param. reads only those parquet files

        output: pandas dataframe inlcuding all the context windows for param company
        """
        table = self._dataset.to_table(
            columns=[
                "company",
                "ticker",
                "cik",
                "filing_url",
                "keywords_found",
                "matched_phrase",
                "context"
            ],
            filter=ds.field("company") == company,
        )
        return table.to_pandas()