from src.crawler import CrawlerPipeline
from src.preprocessing import PreProcessingPipeline
from src.classification import ClassificationPipeline
from src.results import ResultsPipeline

import click

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

@click.command()
@click.option('--crawler', is_flag=True, help='Crawler')
@click.option('--process_data', is_flag=True, help='Process Data')
@click.option('--classification', is_flag=True, help='Classification of Data')
@click.option('--results', is_flag=True, help='Displaying of Results')
def main(crawler, process_data, classification, results):

    if crawler:
        crawler = CrawlerPipeline()
        crawler.crawler_workflow()

    if process_data:
        pre_processing = PreProcessingPipeline()
        pre_processing.pre_processing_workflow()
    
    if classification:
        classification = ClassificationPipeline()
        classification.classification_workflow()

    if results:
        results = ResultsPipeline()
        results.results_workflow()

if __name__ == "__main__":
    main()