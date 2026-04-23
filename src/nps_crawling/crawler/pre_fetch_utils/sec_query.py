"""SEC Query abstraction module with utility functions."""
import logging
import sys
import time

import requests

from nps_crawling.db.db_adapter import DbAdapter
from nps_crawling.crawler.pre_fetch_utils.filings import Filing
from nps_crawling.crawler.pre_fetch_utils.sec_params import SecSearchParams
from nps_crawling.crawler.pre_fetch_utils.sec_ticker_map import SecTickerMap

logger = logging.getLogger(__name__)


def get_total_filings_count(data: dict) -> int:
    """Get total number of queried filings."""
    return int(data['hits']['total']['value'])


def get_fetched_filings_count(data: dict) -> int:
    """Get total number of queried filings of the requested page."""
    return int(data['query']['size'])


class SecQuery:
    """Class to create SecQuery object."""
    def __init__(self, sec_params: SecSearchParams):
        """Initializes SecQuery object."""
        self.sec_params = sec_params
        self.results = -1
        self.keyword_filings = []

    def query_request(self, page: int) -> dict:
        """Queries the requested filings page."""
        headers = {
            'User-Agent': 'YourName your.email@example.com',
        }

        query = self.sec_params.create_query(page=page)
        response = requests.get(query, headers=headers)

        return response.json()

    def fetch_filings(self) -> list[Filing]:
        """Starts the fetching process."""
        queries: list = self.query_multi_request()
        self.keyword_filings: list[Filing] = self.create_filings(queries)

        self.keyword_filings = self.are_filings_present_in_db(filings=self.keyword_filings,
                                                              bypass_filter=self.sec_params.force_crawl)

        return self.keyword_filings

    def are_filings_present_in_db(self, filings: list[Filing], bypass_filter: bool = False) -> list[Filing]:
        temp: list[Filing] = []
        try:
            db: DbAdapter = DbAdapter()

            for filing in filings:
                if not db.filing_exists(filing.get_id()):
                    temp.append(filing)
                    logger.debug(f"Filing with ID {filing.get_id()} does not exists in DB")
                elif bypass_filter:
                    temp.append(filing)
                else:
                    db.add_keyword(filing.id, filing.keyword)
                    logger.debug(f"Filing with ID {filing.get_id()} does exists in DB")
                    pass

            old_length: int = len(filings)
            filings.clear()
            filings = temp
            new_length: int = len(filings)
            logger.info(f"\n\tNew size: {new_length} {'-' * 3} Old size: {old_length}")
            return temp

        except ModuleNotFoundError as e:
            logger.warning(f"ModuleNotFoundError: {e}")
            return filings
        except ValueError as e:
            logger.warning(f"ValueError: {e}")
            return filings

    def query_multi_request(self) -> list:
        """Queries the requested filings across all pages."""
        total: int = -1
        limit: int = self.sec_params.filing_limit if self.sec_params.filing_limit >= 0 else sys.maxsize
        page: int = 1
        queries: list = []

        timeout: int = 5
        maximum_retries: int = 10
        retries: int = 0

        while True:
            if retries > maximum_retries:
                logger.error(f"Unable to fetch filings after {retries} retries!")
                exit(-1)

            response: dict = self.query_request(page=page)
            # Set total results of the query on first query
            if self.results == -1:
                self.results = get_total_filings_count(response)
                total = self.results
                print(f'Total Results: {total}')

            # Catch any bad response from server and retry again for 10 times until it either works.
            # If after 10 tries it does not work, maybe your internet is the issue.
            try:
                hits: list[str] = response['hits']['hits']
            except Exception as e:
                logger.error(e)
                logger.error(f"Received faulty response: {response}.")
                logger.info(f"Restarting fetch in {timeout} seconds.")
                retries += 1
                time.sleep(timeout)
                continue

            # Give info about retries
            if retries > 0:
                logger.info(f"Filings took {retries} to get processed.")

            retries = 0
            query = len(hits)

            logger.info(f'Iterating through page: {page}')

            if limit < query:
                response['hits']['hits'] = hits[:limit]
                queries.append(response)
                break
            else:
                queries.append(response)

            limit -= query
            total -= query

            if total <= 0 or limit <= 0:
                break
            page += 1

        return queries

    def create_filing(self, data: dict) -> Filing:
        """Helper function to create Filing object based on JSON payload."""
        # Main data payload containing filing details
        _source = data['_source']
        # Unique filing identifier from source
        _id = data['_id']
        # Elasticsearch index name, same for all entries
        _index = data['_index']

        # Unique ID given by website
        _id: str = data['_id']
        # Idk what this does, the same for each entry
        _index: str = data['_index']

        # CIKS, each entry can have multiple
        ciks: list[str] = _source['ciks']
        # Reporting period end date
        period_ending: str = _source['period_ending']
        # File numbers associated with filing
        file_num: list[str] = _source['file_num']
        # File display names
        display_names: list[str] = _source['display_names']
        # XSL stylesheet reference for rendering (?)
        xsl: str = _source['xsl']
        # Filing sequence number
        sequence: str = _source['sequence']
        # Root form types
        root_forms: list[str] = _source['root_forms']
        # When the filing was submitted
        file_date: str = _source['file_date']
        # Business operating states
        biz_states: list[str] = _source['biz_states']
        # Standard Industrial Classification codes
        sics: list[str] = _source['sics']
        # Form type (10-K, 10-Q, 8-K, etc)
        form: str = _source['form']
        # Accession number (unique filing ID)
        adsh: str = _source['adsh']
        # Film numbers (legacy microfilm references)
        film_num: list[str] = _source['film_num']
        # Business location addresses
        biz_locations: list[str] = _source['biz_locations']
        # Type of file (complete submission, amendment, etc)
        file_type: str = _source['file_type']
        file_description: str = _source['file_description']
        # Incorporation states
        inc_states: list[str] = _source['inc_states']

        # Get file name from path
        file_name_path = _id.split(':', 1)[1]

        # Get ticker
        mapper = SecTickerMap()
        ticker: list[str] = mapper.get_tickers_from_strings(display_names)

        filing = Filing(_id=_id,
                        _index=_index,
                        ciks=ciks,
                        ticker=ticker,
                        period_ending=period_ending,
                        file_num=file_num,
                        display_names=display_names,
                        xsl=xsl,
                        sequence=sequence,
                        root_forms=root_forms,
                        file_date=file_date,
                        biz_states=biz_states,
                        sics=sics,
                        form=form,
                        adsh=adsh,
                        film_num=film_num,
                        biz_locations=biz_locations,
                        file_type=file_type,
                        file_description=file_description,
                        inc_states=inc_states,
                        file_path_name=file_name_path,
                        keyword=self.sec_params.keyword,
        )

        return filing

    def create_filings(self, data: list) -> list[Filing]:
        """Create list of filings based on JSON payload."""
        filings: list = []

        for page in data:
            for entry in page['hits']['hits']:
                filings.append(self.create_filing(entry))

        return filings
