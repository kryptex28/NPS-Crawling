import os
from os.path import (
    isdir, 
    join,
)

from nps_crawling.crawler.pre_fetch_utils.sec_params import (
    SecSearchParams,
    create_config_from_dict,
    create_search_params_from_config_dir,
    store_config,
)
from nps_crawling.crawler.pre_fetch_utils.filings import FilingsCategoryCollectionCoarse
from nps_crawling.config import Config
from data_package.QueryData import QueryData
from uuid import uuid4


class QueryModel():

    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        self.queries: list[str] = []
#
#    def create_query(self, data: dict) -> None:
#        print(data)
#        parameter: SecSearchParams = create_config_from_dict(data=data)
#        parameter.query_base = "https://efts.sec.gov/LATEST/search-index?"
#
#        store_config(path=Config.GUI_QUERY_PATH, 
#                     parameter=parameter)

    def accept_queries(self, ids: list[str]):
        self.queries.clear()
        self.queries = ids.copy()

    def get_queries(self) -> list[QueryData]:
        params: list[SecSearchParams] = create_search_params_from_config_dir(str(Config.GUI_QUERY_PATH))

        queries: list[QueryData] = []
        for param in params:
            queries.append(self._create_query_data_from_config(params=param))
        return queries
    
    def _create_query_data_from_config(self, params: SecSearchParams) -> QueryData:
        return QueryData(
            id=params.id,
            query_base=params.query_base,
            keyword=params.keyword,
            from_date=params.from_date,
            to_date=params.to_date,
            entity="",
            filing_category=params.filing_category.to_string(),
            filing_types=params.filing_categories
        )

    def update_queries(self) -> list[QueryData]:
        if not os.path.isdir(Config.GUI_QUERY_PATH):
            return []
        params: list[SecSearchParams] = create_search_params_from_config_dir(str(Config.GUI_QUERY_PATH))

        queries: list[QueryData] = []

        for param in params:
            queries.append(self._create_query_data_from_config(params=param))

        return queries

    def _create_config_from_query(self, data: QueryData) -> SecSearchParams:
        return SecSearchParams(
            id=str(uuid4()),
            keyword=data.keyword,
            query_base=data.query_base,
            date_range=data.date_range,
            from_date=data.from_date,
            to_date=data.to_date,
            filing_categories=data.filing_types,
            filing_category=FilingsCategoryCollectionCoarse.from_string(data.filing_category),
            force_crawl=False,
            filing_limit=-1
        )

    def create_query(self, data: QueryData) -> None:
        print(data)
        parameter: SecSearchParams = self._create_config_from_query(data=data)
        parameter.query_base = "https://efts.sec.gov/LATEST/search-index?"

        store_config(path=Config.GUI_QUERY_PATH, 
                     parameter=parameter)