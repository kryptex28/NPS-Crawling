from config.config import Config

from .data_processing.preprocess_data import ClassificationDataProcessing
from .model.classification_model import ClassificationModelPipeline

import logging
logger = logging.getLogger(__name__)

class ClassificationPipeline(Config):
  
    def __init__(self):

        self.get_data = ClassificationDataProcessing()
        self.model_pipeline = ClassificationModelPipeline()

    def classification_workflow(self):
        """
        get all company names --> loop through all companies 1 by 1 --> create dataframe with all
        context windows for 1 company --> ...
        """

        logger.info("Starting classification")

        companies_list = self.get_data.get_list_of_all_companies()

        logger.info(f"Number of companies to classify: {len(companies_list)}")

        for company in companies_list:

            single_company_df = self.get_data.get_data_for_classification(company)
            self.model_pipeline.classification_workflow(single_company_df)

        logger.info("Finished classification")

        return None