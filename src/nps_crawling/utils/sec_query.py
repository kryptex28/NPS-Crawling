import requests

from nps_crawling.utils.sec_params import SecParams
from nps_crawling.utils.filings import Filing


def create_filing(data: dict) -> Filing:
    _source = data['_source']
    _id = data['_id']
    _index = data['_index']

    ciks = _source['ciks']
    period_ending = _source['period_ending']
    file_num = _source['file_num']
    display_names = _source['display_names']
    xsl = _source['xsl']
    sequence = _source['sequence']
    root_forms = _source['root_forms']
    file_date = _source['file_date']
    biz_states = _source['biz_states']
    sics = _source['sics']
    form = _source['form']
    adsh = _source['adsh']
    firm_number = _source['film_num']
    biz_location = _source['biz_locations']
    file_type = _source['file_type']
    file_description = _source['file_description']
    inc_states = _source['inc_states']

    filename = _id.split(':', 1)[1]

    filing = Filing(
        filename,
        _index,
        ciks,
        period_ending,
        file_num,
        display_names,
        xsl,
        sequence,
        root_forms,
        file_date,
        biz_states,
        sics,
        form,
        adsh,
        firm_number,
        biz_location,
        file_type,
        file_description,
        inc_states,
    )

    return filing

def create_filings(data: list) -> list[Filing]:
    filings: list = []

    for page in data:
        for entry in page['hits']['hits']:
            filings.append(create_filing(entry))

    return filings

def get_total_filings_count(data: dict) -> int:
    return int(data['hits']['total']['value'])

def get_fetched_filings_count(data: dict) -> int:
    return int(data['query']['size'])

class SecQuery:

    def __init__(self, sec_params: SecParams, limit: int = -1):
        self.sec_params = sec_params
        self.results = -1
        self.keyword_filings = []
        self.query_base_url = 'https://efts.sec.gov/LATEST/search-index?'
        self.limit = limit


    def query_over_keyword(self, page: int) -> dict:

        headers = {
            'User-Agent': 'YourName your.email@example.com',
        }

        query = self.sec_params.create_query(page=page)
        response = requests.get(query, headers=headers)

        return response.json()

    def fetch_filings(self) -> None:
        queries: list = self.query_over_keywords()
        self.keyword_filings = create_filings(queries)

    def query_over_keywords(self) -> list:
        total: int = -1
        limit: int = self.limit
        page: int = 1
        queries: list = []

        while True:
            response: dict = self.query_over_keyword(page=page)
            queries.append(response)
            if self.results == -1:
                self.results = get_total_filings_count(response)
                #self.results = response['hits']['total']['value']
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
