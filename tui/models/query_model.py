import os
from os.path import (
    join,
)

from nps_crawling.crawler.pre_fetch_utils.sec_params import (
    SecSearchParams,
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
        """Create or return the singleton instance of QueryModel."""
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        """Initialize the QueryModel instance."""
        if not hasattr(self, '_initialized'):  
            self.query_ids: list[str] = []
            self._initialized = True
            self.selected_queries: set[str] = set()
            self.categories: list[str] = []


    def get_query_ids(self) -> list[str]:
        """Retrieve the list of active query IDs."""
        return self.query_ids

    def accept_queries(self):
        # Technically nothing to do here lol
        """Accept and commit query changes."""
        pass

    def get_queries(self) -> list[QueryData]:
        """Load and return all queries from the query configuration files."""
        params: list[SecSearchParams] = create_search_params_from_config_dir(str(Config.QUERY_PATH))

        queries: list[QueryData] = []
        for param in params:
            queries.append(self._create_query_data_from_config(params=param))
        return queries
    
    def _create_query_data_from_config(self, params: SecSearchParams) -> QueryData:
        """Create a QueryData object from a SecSearchParams instance."""
        import datetime
        entity = ""
        cik = ""
        entity_title = ""
        if params.individual_search:
            if getattr(params.individual_search, "ticker", None):
                if isinstance(params.individual_search.ticker, list) and len(params.individual_search.ticker) > 0:
                    entity = params.individual_search.ticker[0]
                elif isinstance(params.individual_search.ticker, str):
                    entity = params.individual_search.ticker
            cik = getattr(params.individual_search, "cik", "")
            entity_title = getattr(params.individual_search, "title", "")

        created_at = ""
        file_path = join(Config.QUERY_PATH, f"{params.id}.json")
        if os.path.exists(file_path):
            try:
                # Use mtime as it represents when the file was written, formatted as string
                mtime = os.path.getmtime(file_path)
                created_at = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

        return QueryData(
            id=params.id,
            query_base=params.query_base,
            keyword=params.keyword,
            from_date=params.from_date,
            to_date=params.to_date,
            entity=entity,
            cik=cik,
            entity_title=entity_title,
            filing_category=params.filing_category.to_string(),
            filing_types=params.filing_categories,
            date_range=params.date_range or "all",
            limit=params.filing_limit,
            created_at=created_at,
        )

    def update_queries(self) -> list[QueryData]:
        """Scan the query directory and update the list of available queries."""
        if not os.path.isdir(Config.QUERY_PATH):
            return []
        params: list[SecSearchParams] = create_search_params_from_config_dir(str(Config.QUERY_PATH))

        queries: list[QueryData] = []

        for param in params:
            queries.append(self._create_query_data_from_config(params=param))

        return queries

    def _create_config_from_query(self, data: QueryData) -> SecSearchParams:
        """Convert a QueryData object into a SecSearchParams configuration object."""
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
            filing_limit=data.limit,
        )

    def create_query(self, data: QueryData) -> None:
        
        """Create and save a new query configuration file."""
        if data.date_range not in ("all", "custom"):
            import datetime
            today = datetime.date.today()
            data.to_date = today.strftime("%Y-%m-%d")
            try:
                val = int(data.date_range[:-1])
                unit = data.date_range[-1].lower()
                if unit == "y":
                    try:
                        from_date_obj = today.replace(year=today.year - val)
                    except ValueError:
                        from_date_obj = today.replace(year=today.year - val, day=28)
                elif unit == "d":
                    from_date_obj = today - datetime.timedelta(days=val)
                else:
                    from_date_obj = today
                data.from_date = from_date_obj.strftime("%Y-%m-%d")
            except Exception:
                pass

        parameter: SecSearchParams = self._create_config_from_query(data=data)
        parameter.query_base = "https://efts.sec.gov/LATEST/search-index?"

        store_config(path=str(Config.QUERY_PATH), 
                     parameter=parameter)
        
        # TODO Remove in Future lol
        self.query_ids.append(parameter.id)
        print(parameter.id)

    def add_selected(self, id: str) -> None:
        """Add a query ID to the selected set."""
        self.selected_queries.add(id)
    
    def remove_selected(self, id: str) -> None:
        """Remove a query ID from the selected set."""
        self.selected_queries.remove(id)

    def delete_query(self, id: str) -> None:
        # TODO: Maybe extract into param class
        """Delete a query configuration file by ID."""
        if os.path.isdir(Config.QUERY_PATH):
            os.remove(join(Config.QUERY_PATH, f"{id}.json"))

    def fuzzy_search(self, text: str):
        """Perform a fuzzy search against company names and tickers using rapidfuzz."""
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
        """Update the local copy of the filing categories."""
        self.categories = categories.copy()

    def get_filing_categories(self) -> list[str]:
        """Retrieve the local list of filing categories."""
        return self.categories