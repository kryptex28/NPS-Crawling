import requests
import datetime

from nps_crawling.utils.sec_query import SecParams
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
    fire_descrption = _source['file_description']
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
        fire_descrption,
        inc_states,
    )

    return filing

def create_filings(data: dict) -> dict:
    filings: dict = {}

    for k, v in data.items():
        filings[k] = []
        for page in data[k]:
            for entry in page['hits']['hits']:
                filings[k].append(create_filing(entry))
            #print(entry['_source'])
            #filings[k] = create_filing(entry)

    return filings

class SecQuery:

    def __init__(self, sec_params: SecParams):
        self.sec_params = sec_params
        self.results = -1
        self.keyword_filings = {}
        self.query_base_url = 'https://efts.sec.gov/LATEST/search-index?'


    def query_over_keyword(self, keyword: str, page: int) -> dict:

        headers = {
            'User-Agent': 'YourName your.email@example.com',
        }

        query = self.sec_params.create_query_keyword(query=self.query_base_url, keyword=keyword, page=page)
        response = requests.get(query, headers=headers)

        return response.json()

    def fetch_filings(self):
        queries: dict = self.query_over_keywords()
        self.keyword_filings: dict = create_filings(queries)

    def query_over_keywords(self) -> dict:
        queries: dict = {}
        total: int = -1
        page: int = 1
        for keyword in self.sec_params.keywords:
            queries[keyword] = []
            while True:
                response: dict = self.query_over_keyword(keyword=keyword, page=page)
                queries[keyword].append(response)
                if self.results == -1:
                    self.results = response['hits']['total']['value']
                    total = self.results
                query = response['query']['size']
                total -= query
                if total == 0:
                    break
                page += 1
                print(f'Page: {page}')


        return queries
