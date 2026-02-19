import requests

from nps_crawling.utils.sec_params import SecParams
from nps_crawling.utils.filings import Filing


def create_filing(data: dict) -> Filing:
    _source = data['_source']
    _id = data['_id']
    _index = data['_index']

    _id: str = data['_id']
    _index: str = data['_index']

    ciks: list[str] = _source['ciks']
    period_ending: str = _source['period_ending']
    file_num: list[str] = _source['file_num']
    display_names: list[str] = _source['display_names']
    xsl: str = _source['xsl']
    sequence: str = _source['sequence']
    root_forms: list[str] = _source['root_forms']
    file_date: str = _source['file_date']
    biz_states: list[str] = _source['biz_states']
    sics: list[str] = _source['sics']
    form: str = _source['form']
    adsh: str = _source['adsh']
    film_num: list[str] = _source['film_num']
    biz_locations: list[str] = _source['biz_locations']
    file_type: str = _source['file_type']
    file_description: str = _source['file_description']
    inc_states: list[str] = _source['inc_states']

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
