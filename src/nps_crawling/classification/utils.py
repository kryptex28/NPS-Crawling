"""Classification pipeline to process and classify company data."""

import logging

from nps_crawling.classification.data_processing.preprocess_data import ClassificationDataProcessing
from nps_crawling.classification.model.classification_model import ClassificationModelPipeline
from nps_crawling.config import Config

logger = logging.getLogger(__name__)


class ClassificationPipeline(Config):
    """Classification pipeline class."""
    def __init__(self):
        """Initialize the ClassificationPipeline."""
        self.get_data = ClassificationDataProcessing()
        self.model_pipeline = ClassificationModelPipeline()

    def classification_workflow(self):
        """Classification workflow method.

        Get all company names --> loop through all companies 1 by 1 --> create dataframe with all
        context windows for 1 company --> ...
        """
        logger.info("Starting classification")

        companies_list = self.get_data.get_list_of_all_companies()

        logger.info(f"Number of companies to be classified: {len(companies_list)}")

        for company in companies_list:

            single_company_df = self.get_data.get_data_for_classification(company)
            self.model_pipeline.model_workflow(single_company_df)

        logger.info("Finished classification")

        return None
