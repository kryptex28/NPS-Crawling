import requests
import datetime

from nps_crawling.utils.filings import Filing

query_base_url = 'https://efts.sec.gov/LATEST/search-index?q='

def query_over_keyword(keyword) -> dict:
    headers = {
        'User-Agent': 'YourName your.email@example.com',
    }

    query_url = f'{query_base_url}{keyword}'

    response = requests.get(query_url, headers=headers)

    return response.json()

def query_over_keywords(keywords: list[str]):
    queries: list[dict] = []

    for keyword in keywords:
        queries.append(query_over_keyword(keyword))

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
                 individual_search: dict = {},
                 filing_category = None,
                 invole_type = None,
                 location = None,
                 ) -> list[Filing]:
    # TODO: Add enums for closed search + encoding of parameters and keywords
    queries: list[dict] = query_over_keywords(keywords=keywords)
    filings: list[Filing] = create_filings(queries)

    return filings

