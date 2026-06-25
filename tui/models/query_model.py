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
from nps_crawling.crawler.pre_fetch_utils.sec_ticker_map import SecTickerMap
from nps_crawling.config import Config
from data_package.query_data import QueryData
from data_package.entity_data import EntityData

from uuid import uuid4
from rapidfuzz import process, fuzz
from nps_crawling.crawler.pre_fetch_utils.sec_params import CompanyTicker
from nps_crawling.crawler.pre_fetch_utils.sec_ticker_map import SecTickerMap

class QueryModel():

    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        if not hasattr(self, '_initialized'):  
            self.query_ids: list[str] = []
            self._initialized = True
            self.selected_queries: set[str] = set()
            self.categories: list[str] = []


    def get_query_ids(self) -> list[str]:
        return self.query_ids

    def accept_queries(self):
        # Technically nothing to do here lol
        pass

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
        data.id = str(uuid4())

        ticker_map: SecTickerMap = SecTickerMap()
        
        individual_search: tuple[str, str, str] = ("", "", "")

        for cik, ticker, title in ticker_map.get_fuzzy_data():
            if ticker.lower() == data.entity.lower():
                individual_search = (cik, ticker, title)

        return SecSearchParams(
            id=data.id,
            keyword=data.keyword,
            query_base=data.query_base,
            date_range=data.date_range,
            from_date=data.from_date,
            to_date=data.to_date,
            individual_search=CompanyTicker(cik=individual_search[0],
                                            ticker=[individual_search[1]],
                                            title=individual_search[2]),
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
        
        # TODO Remove in Future lol
        self.query_ids.append(parameter.id)
        print(parameter.id)

    def add_selected(self, id: str) -> None:
        self.selected_queries.add(id)
    
    def remove_selected(self, id: str) -> None:
        self.selected_queries.remove(id)

    def delete_query(self, id: str) -> None:
        # TODO: Maybe extract into param class
        if os.path.isdir(Config.GUI_QUERY_PATH):
            os.remove(join(Config.GUI_QUERY_PATH, f"{id}.json"))

    def fuzzy_search(self, text: str):
        data: list[tuple[str, str, str]] = SecTickerMap().get_fuzzy_data()
        limit: int = 5
        choices = {i: row[2] for i, row in enumerate(data)}

        matches = process.extract(
            text,
            choices,
            scorer=fuzz.WRatio,
            limit=limit
        )

        entity_data: list[EntityData] = []
        for _, _, idx in matches:
            d = data[idx]
            entity_data.append(EntityData(cik=d[0], ticker=d[1], title=d[2]))

        return entity_data

    def add_filing_categories(self, categories: list[str]):
        self.categories = categories.copy()

    def get_filing_categories(self) -> list[str]:
        return self.categories