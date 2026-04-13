from nps_crawling.crawler.data_prefetch.strategy.fetch_strategy import FetchStrategy
from nps_crawling.utils.filings import Filing
from nps_crawling.utils.sec_params import SecSearchParams, create_search_params_from_config
from nps_crawling.utils.sec_query import SecQuery

from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import defer, reactor

import logging

logger = logging.getLogger(__name__)

class SearchStrategy(FetchStrategy):

    def __init__(self) -> None:
        super().__init__()

    def fetch(self, 
              query_path: str,
              **kwargs) -> list[Filing]:
        
        ignore_lookup = kwargs.get("ignore_lookup", False)
        # Create search parameters based on queries
        search_parameters: list[SecSearchParams] = create_search_params_from_config(query_path)

        # Create queries
        sec_queries: list[SecQuery] = []
        for parameter in search_parameters:
            if parameter.filing_limit == -1:
                parameter.filing_limit = get_project_settings()["SEC_QUERY_LIMIT_COUNT"]

            query: SecQuery = SecQuery(sec_params=parameter)
            sec_queries.append(query)

        # Fetch all filings per query
        filings_dict: dict[str, Filing] = {}
        duplicates: dict[str, list[Filing]] = {}

        for query in sec_queries:
            temp: list[Filing] = query.fetch_filings()

            if ignore_lookup:
                logger.info("Ignoring database.")
                pass
            else:
                logger.info("Using database for duplicate-check.")
                temp = query.are_filings_present_in_db(filings=temp.copy())
                print(len(temp))
                for filing in temp:
                    if filing.id in filings_dict:
                        # Collect duplicates for analysis
                        if filing.id not in duplicates:
                            duplicates[filing.id] = [filings_dict[filing.id]]
                            logger.debug(f"Found duplicate: {filing.id}")
                        duplicates[filing.id].append(filing)
                    else:
                        filings_dict[filing.id] = filing

        filings = list(filings_dict.values())

        for _id, dupes in duplicates.items():
            logger.info(f"Found for ID {_id} {len(dupes)} duplicates.")

        return filings