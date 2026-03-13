"""SEC Parameter search abstraction module with utility functions."""
from __future__ import annotations

import json

from nps_crawling.utils.filings import CompanyTicker, FilingCategoryCollection, FilingsCategoryCollectionCoarse


def create_params_from_config(path: str) -> list[SecParams]:
    """Create params from config file."""
    params: list[SecParams] = []

    with open(path, 'r') as f:
        config: dict = json.load(f)

    queries = config['queries']

    for query_id, query_data in queries.items():
        query_base: str = query_data.get('query_base', '')
        keyword = query_data.get('keyword', '')
        from_date: str = query_data.get('from_date', '')
        to_date: str = query_data.get('to_date', '')
        date_range = query_data.get('date_range', 'N/A')

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

        p = SecParams(query_base=query_base,
                      individual_search=individual_search,
                      keyword=keyword,
                      from_date=from_date,
                      to_date=to_date,
                      date_range=date_range,
                      filing_category=filing_category,
                      filing_categories=filing_categories,
                      )

        params.append(p)
    return params


def create_config_from_params(params: list[SecParams]) -> dict:
    """Create config data from parameter list."""
    data: dict = {
        "queries": {},
    }

    queries: dict = data['queries']
    for i, param in enumerate(params):
        key: int = i + 1
        queries[str(key)] = param.create_dict()

    return data


class SecParams:
    """Class abstraction of sec.gov parameter based search."""
    def __init__(self,
                 query_base: str,
                 keyword: str = None,
                 from_date: str = None,
                 to_date: str = None,
                 date_range: str = None,
                 individual_search: CompanyTicker = None,
                 filing_category: FilingsCategoryCollectionCoarse = FilingsCategoryCollectionCoarse.ALL,
                 filing_categories: list[str] = None,
                 principal_office_in: str = None,):
        """Initialize SecParams class."""
        self.query_base = query_base
        self.keyword = keyword
        self.from_date = from_date
        self.to_date = to_date
        self.date_range = date_range
        self.individual_search = individual_search
        self.filing_category = filing_category
        self.filing_categories = filing_categories
        self.principal_office_in = principal_office_in
        self.last_query = ''

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

        if self.principal_office_in:
            query_url = f'{query_url}&locationCode={self.principal_office_in}'
            query_url = f'{query_url}&locationCodes={self.principal_office_in}'

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

        return {
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
        }

def create_sec_param_from_dict(data: dict) -> SecParams:
    """Create SecParams object from dict data."""

    query_base: str = 'https://efts.sec.gov/LATEST/search-index?'
    keyword: str = data['query']
    #from_date: str = data['filed_from']
    #to_date: str = data['filed_to']
    #date_range: str = data['date_range']
    #filing_category: FilingsCategoryCollectionCoarse = data['filing_category']
    #filing_categories: list[str] = data['filing_types']


    sec_params: SecParams = SecParams(query_base=query_base,
                                      keyword=keyword,
                                      #from_date=from_date,
                                      #to_date=to_date,
                                      #date_range=date_range,
                                      )
    return sec_params
