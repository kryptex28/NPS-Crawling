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
from nps_crawling.config import Config


class QueryModel():

    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        self.queries: list[str] = []

    def create_query(self, data: dict) -> None:
        print(data)
        parameter: SecSearchParams = create_config_from_dict(data=data)
        parameter.query_base = "https://efts.sec.gov/LATEST/search-index?"

        store_config(path=Config.GUI_QUERY_PATH, 
                     parameter=parameter)

    def accept_queries(self, ids: list[str]):
        self.queries.clear()
        self.queries = ids.copy()

    def get_queries(self) -> list[SecSearchParams]:
        if not os.path.isdir(Config.GUI_QUERY_PATH):
            return []
        
        params: list[SecSearchParams] = create_search_params_from_config_dir(str(Config.GUI_QUERY_PATH))
        return params