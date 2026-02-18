from nps_crawling.utils.filings import Filing, FilingCategoryCollection

class SecParams:
    keywords: list[str] = []
    from_date: str = ''
    to_date: str = ''
    date_range: str = ''
    individual_search: list[str] = []
    filing_category: FilingCategoryCollection = FilingCategoryCollection()
    filing_categories: list[str] = []
    involve_type: str = ''
    location: str = ''

    def __init__(self,
                 keywords: list[str] = None,
                 from_date: str = None,
                 to_date: str = None,
                 date_range: str = None,
                 individual_search: list[str] = None,
                 filing_category: FilingCategoryCollection = None,
                 filing_categories: list[str] = None) :
        self.keywords = keywords
        self.from_date = from_date
        self.to_date = to_date
        self.date_range = date_range
        self.individual_search = individual_search
        self.filing_category = filing_category
        self.filing_categories = filing_categories

    def create_query_keyword(self, query: str, keyword, page: int) -> str:
        query_url = f'{query}q={keyword}'

        if page > 1:
            query_url = f'{query_url}&page={page}'

        if self.from_date:
            query_url = f'{query_url}&startdt={self.from_date}'

        if self.from_date:
            query_url = f'{query_url}&enddt={self.to_date}'

        if self.date_range:
            query_url = f'{query_url}&dateRange={self.date_range}'

        return query_url