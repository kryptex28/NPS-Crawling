from nps_crawling.utils.filings import FilingCategoryCollection
from nps_crawling.utils.filings import CompanyTicker

class SecParams:
    """Class abstraction of sec.gov parameter based search."""
    keywords: str = ''
    from_date: str = ''
    to_date: str = ''
    date_range: str = ''
    individual_search: CompanyTicker = None
    filing_category: FilingCategoryCollection = FilingCategoryCollection()
    filing_categories: list[str] = []
    involve_type: str = ''
    location: str = ''

    def __init__(self,
                 query_base: str,
                 keyword: str = None,
                 from_date: str = None,
                 to_date: str = None,
                 date_range: str = None,
                 individual_search: CompanyTicker = None,
                 filing_category: FilingCategoryCollection = None,
                 filing_categories: list[str] = None):
        """Initialize SecParams class."""
        self.query_base = query_base
        self.keyword = keyword
        self.from_date = from_date
        self.to_date = to_date
        self.date_range = date_range
        self.individual_search = individual_search
        self.filing_category = filing_category
        self.filing_categories = filing_categories
        self.last_query = ''

    def create_query(self, page: int) -> str:
        """Create the query url with parameters."""
        query_url = f'{self.query_base}q={self.keyword}'

        if page > 1:
            query_url = f'{query_url}&page={page}'

        if self.from_date:
            query_url = f'{query_url}&startdt={self.from_date}'

        if self.from_date:
            query_url = f'{query_url}&enddt={self.to_date}'

        if self.date_range:
            query_url = f'{query_url}&dateRange={self.date_range}'

        #if self.individual_search:

        if self.filing_category and self.filing_categories:
            query_url = f'{query_url}&category={self.filing_category}'
            query_url = f'{query_url}&forms={','.join(self.filing_categories)}'

        if self.individual_search:
            query_url = f'{query_url}&entityName={self.individual_search.create_entity_name()}'
            query_url = f'{query_url}&ciks={self.individual_search.cik}'
            text = self.individual_search.create_entity_name()
            if 'MOLSON COORS BEVERAGE CO (TAP, TAP-A) (CIK 0000024545)' == text:
                pass

        self.last_query = query_url

        return query_url