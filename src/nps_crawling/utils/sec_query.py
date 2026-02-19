import requests

from nps_crawling.utils.sec_params import SecParams
from nps_crawling.utils.filings import Filing


def create_filing(data: dict) -> Filing:
    """Helper function to create Filing object based on JSON payload."""
    _source = data['_source'] # Main data payload containing filing details
    _id = data['_id'] # Unique filing identifier from source
    _index = data['_index'] # Elasticsearch index name, same for all entries

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

    filing = Filing(_id=_id,
                    _index=_index,
                    ciks=ciks,
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
                    file_path_name=file_name_path
    )

    return filing

def create_filings(data: list) -> list[Filing]:
    """Create list of filings based on JSON payload."""
    filings: list = []

    for page in data:
        for entry in page['hits']['hits']:
            filings.append(create_filing(entry))

    return filings

def get_total_filings_count(data: dict) -> int:
    """Get total number of queried filings."""
    return int(data['hits']['total']['value'])

def get_fetched_filings_count(data: dict) -> int:
    """Get total number of queried filings of the requested page."""
    return int(data['query']['size'])

class SecQuery:
    """Class to create SecQuery object."""
    def __init__(self, sec_params: SecParams, limit: int = -1):
        self.sec_params = sec_params
        self.results = -1
        self.keyword_filings = []
        self.limit = limit

    def query_request(self, page: int) -> dict:
        """Queries the requested filings page."""
        headers = {
            'User-Agent': 'YourName your.email@example.com',
        }

        query = self.sec_params.create_query(page=page)
        response = requests.get(query, headers=headers)

        return response.json()

    def fetch_filings(self) -> None:
        """Starts the fetching process."""
        queries: list = self.query_multi_request()
        self.keyword_filings = create_filings(queries)

    def query_multi_request(self) -> list:
        """Queries the requested filings across all pages."""
        total: int = -1
        limit: int = self.limit
        page: int = 1
        queries: list = []

        while True:
            response: dict = self.query_request(page=page)
            queries.append(response)
            # Set total results of the query on first query
            if self.results == -1:
                self.results = get_total_filings_count(response)
                total = self.results
                print(f'Total Results: {total}')
            query = get_fetched_filings_count(response)
            total -= query
            limit -= query
            if total <= 0 or limit <= 0:
                break
            page += 1
            print(f'Page: {page}')

        return queries
