"""SEC Parameter search abstraction module with utility functions."""
from __future__ import annotations

import uuid
import json
import os
from os import listdir
from os.path import isfile, join

from nps_crawling.crawler.pre_fetch_utils.filings import CompanyTicker, FilingCategoryCollection, FilingsCategoryCollectionCoarse


def create_search_params_from_config(path: str) -> list[SecSearchParams]:
    """Create params from config file."""
    params: list[SecSearchParams] = []

    with open(path, 'r') as f:
        config: dict = json.load(f)

    queries = config['queries']

    for query_id, query_data in queries.items():
        query_base: str = query_data.get('query_base', '')
        keyword = query_data.get('keyword', '')
        from_date: str = query_data.get('from_date', '')
        to_date: str = query_data.get('to_date', '')
        date_range = query_data.get('date_range', 'N/A')
        filing_limit = query_data.get('filing_limit', -1)
        force_crawl: bool = query_data.get('force_crawl', False)

        individual_search_ticker: list[str] = query_data.get('individual_search_ticker', [])
        individual_search_cik: str = query_data.get('individual_search_cik', '')
        individual_search_title: str = query_data.get('individual_search_title', '')

        individual_search: CompanyTicker = None
        if individual_search_title and individual_search_cik and individual_search_ticker:
            individual_search: CompanyTicker = CompanyTicker(ticker=query_data.get('individual_search', ''),
                                                             cik=query_data.get('individual_search_cik', ''),
                                                             title=query_data.get('individual_search_title', ''))

        filing_category: FilingsCategoryCollectionCoarse = FilingsCategoryCollectionCoarse.from_string(
            query_data.get('filing_category', ''),
        )
        if filing_category == FilingsCategoryCollectionCoarse.CUSTOM:
            filing_categories: list[str] = query_data.get('filing_categories', [])
        else:
            filing_categories: list[str] = FilingCategoryCollection.filing_categories[filing_category]

        p = SecSearchParams(query_base=query_base,
                      individual_search=individual_search,
                      keyword=keyword,
                      from_date=from_date,
                      to_date=to_date,
                      date_range=date_range,
                      filing_category=filing_category,
                      filing_categories=filing_categories,
                      filing_limit=filing_limit,
                      force_crawl=force_crawl,
                      id=query_id,
                      )

        params.append(p)
    return params


def create_search_params_from_config_dir(query_dir: str) -> list[SecSearchParams]:
    """Create params from config files inside directory."""
    queries: list = [join(query_dir, f) for f in listdir(query_dir) if isfile(join(query_dir, f))]
    search_parameters: list[SecSearchParams] = []

    for query in queries:
        params: list[SecSearchParams] = create_search_params_from_config(query)
        search_parameters.extend(params)

    return search_parameters


def create_config_from_search_params(params: list[SecSearchParams]) -> dict:
    """Create config data from parameter list."""
    data: dict = {
        "queries": {},
    }

    queries: dict = data['queries']
    for i, param in enumerate(params):
        key: int = i + 1
        queries[str(key)] = param.create_dict()

    return data

def get_config_from_id(path: str, id: str) -> str:
    return join(path, f"{id}.json")

def create_config_from_dict(data: dict) -> SecSearchParams:    
    keyword: str = data.get("query", "")
    entity: str = data.get("entity", "")
    filing_category_str: str = data.get("filing_category", "")
    date_range: str = data.get("date_range", "")
    from_date: str = data.get("from_date", "")
    to_date: str = data.get("to_date", "")

    filing_category: FilingsCategoryCollectionCoarse = FilingsCategoryCollectionCoarse.from_string(filing_category_str)
    if filing_category == FilingsCategoryCollectionCoarse.CUSTOM:
        filing_categories: list[str] = data.get('filing_categories', [])
    else:
        filing_categories: list[str] = FilingCategoryCollection.filing_categories[filing_category]

    return SecSearchParams(keyword=keyword,
                           filing_category=filing_category,
                           filing_categories=filing_categories,
                           individual_search=CompanyTicker("",[""],""),
                           date_range=date_range,
                           from_date=from_date,
                           to_date=to_date,
                           query_base=""
                           )

def store_config(path: str, parameter: SecSearchParams) -> None:

    os.makedirs(os.path.dirname(f"{path}"), exist_ok=True)
    id = parameter.id.translate(str.maketrans(':*?"<>|/\\', '_________'))
    fname = f"{parameter.id}.json"

    saved_path = f"{path}/{fname}"
    with open(saved_path, "w", encoding="utf-8") as f:
        json.dump({ "queries": parameter.create_dict() }, f, ensure_ascii=False, indent=2)
    



class SecSearchParams:
    """Class abstraction of sec.gov parameter based search."""
    def __init__(self,
                 query_base: str = None,
                 keyword: str = None,
                 from_date: str = None,
                 to_date: str = None,
                 date_range: str = None,
                 individual_search: CompanyTicker = None,
                 filing_category: FilingsCategoryCollectionCoarse = FilingsCategoryCollectionCoarse.ALL,
                 filing_categories: list[str] = [],
                 filing_limit: int = -1,
                 force_crawl: bool = False,
                 id: str = ""):
        """Initialize SecSearchParams class."""
        if len(id) == 0:
            self.id = str(uuid.uuid4())
        else:
            self.id = id
        self.query_base = query_base
        self.keyword = keyword
        self.from_date = from_date
        self.to_date = to_date
        self.date_range = date_range
        self.individual_search = individual_search
        self.filing_category = filing_category
        self.filing_categories = filing_categories
        self.last_query = ''
        self.filing_limit: int = filing_limit
        self.force_crawl: bool = force_crawl

    def create_query(self, page: int) -> str:
        """Create the query url with parameters."""
        query_url = f'{self.query_base}q={self.keyword}'

        if page > 1:
            query_url = f'{query_url}&page={page}'
            query_url = f'{query_url}&from={(page - 1) * 100}'

        if self.from_date:
            query_url = f'{query_url}&startdt={self.from_date}'

        if self.from_date:
            query_url = f'{query_url}&enddt={self.to_date}'

        if self.date_range:
            query_url = f'{query_url}&dateRange={self.date_range}'

        if self.filing_category and self.filing_categories:
            query_url = f'{query_url}&category={self.filing_category}'
            query_url = f'{query_url}&forms={",".join(self.filing_categories)}'

        if self.individual_search:
            query_url = f'{query_url}&entityName={self.individual_search.create_entity_name()}'
            query_url = f'{query_url}&ciks={self.individual_search.cik}'
            self.individual_search.create_entity_name()

        self.last_query = query_url

        return query_url

    def create_dict(self) -> dict:
        """Create dictionary representation of query parameters."""
        individual_search_ticker: list[str] = []
        individual_search_cik: str = ''
        individual_search_title: str = ''

        if self.individual_search:
            individual_search_ticker = self.individual_search.ticker
            individual_search_cik = self.individual_search.cik
            individual_search_title = self.individual_search.title

        return { self.id: {
            'query_base': self.query_base,
            'keyword': self.keyword,
            'from_date': self.from_date,
            'to_date': self.to_date,
            'date_range': self.date_range,
            'individual_search_ticker': individual_search_ticker,
            'individual_search_cik': individual_search_cik,
            'individual_search_title': individual_search_title,
            'filing_category': self.filing_category.to_string(),
            'filing_categories': self.filing_categories,
        }}
    
    def __hash__(self) -> int:
        return hash((self.keyword, self.from_date, self.to_date, self.individual_search.ticker, self.individual_search.cik))
