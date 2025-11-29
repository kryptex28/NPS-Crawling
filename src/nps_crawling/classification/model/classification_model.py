"""Classification model pipeline."""

from nps_crawling.config import Config


class ClassificationModelPipeline(Config):
    """Classification model pipeline class."""
    def __init__(self):
        """Initialize the ClassificationModelPipeline."""
        pass

    def model_workflow(self, single_company_df):
        """Model workflow method.

        input: dataframe of single company including all context windows (1 per row).
        """
        return None
