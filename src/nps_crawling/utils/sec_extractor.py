import requests
import datetime

from nps_crawling.utils.filings import Filing

query_base_url = 'https://efts.sec.gov/LATEST/search-index?'

def query_over_keyword(keyword: str,
                       from_date: str = None,
                       to_date: str = None,
                       date_range: str = None,
                       filing_category=None,
                       filing_categories=None,
                       ) -> dict:
    if filing_category is None:
        filing_category = []
    headers = {
        'User-Agent': 'YourName your.email@example.com',
    }

    query_url = f'{query_base_url}q={keyword}&dateRange=30d'

    if from_date:
        query_url += f'&startdt=2026-01-18'

    if to_date:
        query_url += f'&enddt=2026-02-17'


    if filing_category:
        query_url += f'&category={filing_category}'
        query_url += f'&forms={','.join(filing_categories)}'

    response = requests.get(query_url, headers=headers)

    return response.json()

def query_over_keywords(keywords: list[str],
                        from_date = None,
                        to_date = None,
                        date_range = None,
                        filing_category=None,
                        filing_categories=None):
    if filing_category is None:
        filing_category = []
    queries: list[dict] = []

    for keyword in keywords:
        queries.append(query_over_keyword(keyword=keyword,
                                          from_date=from_date,
                                          to_date=to_date,
                                          date_range=date_range,
                                          filing_category=filing_category,
                                          filing_categories=filing_categories))

    return queries

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

def create_filings(data) -> list[Filing]:
    filings: list[Filing] = []

    for d in data:
        for entry in d['hits']['hits']:
            print(entry['_source'])
            filings.append(create_filing(entry))

    return filings

def get_sec_data(keywords: list[str],
                 from_date = None,
                 to_date = None,
                 date_range = None,
                 individual_search=None,
                 filing_category: str = None,
                 filing_categories: list[str] = None,
                 invole_type = None,
                 location = None,
                 ) -> list[Filing]:
    # TODO: Add enums for closed search + encoding of parameters and keywords
    if individual_search is None:
        individual_search = {}
    if filing_category is None:
        filing_category = {}
    queries: list[dict] = query_over_keywords(keywords=keywords,
                                              from_date=from_date,
                                              to_date=to_date,
                                              date_range=date_range,
                                              filing_category=filing_category,
                                              filing_categories=filing_categories,
                                              )
    filings: list[Filing] = create_filings(queries)

    return filings

