"""Spider to crawl SEC filings for NPS mentions."""

import json
import os.path
import pickle
from datetime import datetime
from typing import Any, Generator
from urllib.parse import urljoin

import scrapy
from scrapy import Request

from nps_crawling.crawler.items import FilingItem


class SECNpsSpider(scrapy.Spider):
    """Spider to crawl SEC filings for NPS mentions."""
    name = "sec_nps"

    def __init__(self,
                 crawler_name='crawler',
                 form_types=[],
                 keywords=[],
                 base_url='https://www.sec.gov/Archives/',
                 max_depth=-1,
                 allowed_domains=[],
                 output_format='json',
                 output_path='./data',
                 context_window=300,
                 use_all_companies=False,
                 ticker_list=[],
                 cik_list=[],
                 max_nps_found_count=5,
                 *args, **kwargs):
        """Initialize the spider with configuration parameters."""
        super(SECNpsSpider, self).__init__(*args, **kwargs)

        self.crawler_name = crawler_name
        self.form_types = form_types
        self.base_url = base_url
        self.keywords = keywords
        self.max_depth = max_depth
        self.output_format = output_format
        self.output_path = output_path
        self.context_window = context_window
        self.use_all_companies = use_all_companies
        self.ticker_list = ticker_list
        self.cik_list = cik_list
        self.nps_found_count = 0
        self.max_nps_found_count = max_nps_found_count

        # Override class attributes with instance attributes
        if allowed_domains:
            self.allowed_domains = allowed_domains

        from pathlib import Path
        Path(self.output_path).mkdir(parents=True, exist_ok=True)

        self.state_file = None

        self.state_record: dict = {
            'companies_processed': [],
            'current_company_cik': None,
            'current_company_ticker': None,

            'total_filings': 0,
            'total_errors': 0,
            'urls_processed': [],

            'crawl_start': datetime.now().isoformat(),
            'last_save': None,
            'resume_count': 0,
        }

    def closed(self, reason):
        """Saves state and prints statistics of crawler on Close."""
        self.save_state()

        if self.crawler.stats:
            stats = self.crawler.stats.get_stats()
            self.logger.info(f"Crawler stats: {stats}")

    def load_state(self):
        """Loads crawler state from pickle file."""
        if self.state_file and os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'rb') as f:
                    loaded = pickle.load(f)
                    self.state_record.update(loaded)
                    self.state_record['resume_count'] += 1
                self.logger.warning(f"State loaded: {self.state_record['resume_count']}")
                self.logger.warning(f"Previously processed: {len(self.state_record['companies_processed'])} companies")
            except FileNotFoundError:
                self.logger.error(f"State file not found: {self.state_file}")

    def save_state(self):
        """Save state to pickle file."""
        if self.state_file:
            try:
                from pathlib import Path
                # Create the PARENT directory, not the file itself as a directory
                Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)

                self.state_record['last_save'] = datetime.now().isoformat()
                with open(self.state_file, 'wb') as f:
                    pickle.dump(self.state_record, f)
            except Exception as e:
                self.logger.error(f"Failed to save state: {e}")

    def start_requests(self):
        """Generate start requests based on configuration."""
        headers = {"User-Agent": "YourCompany your.email@example.com"}
        # TODO: Idk what to put here lol (will be replaced in future if noone complaints)

        jobdir = self.settings.get('JOBDIR')
        if jobdir:
            self.state_file = os.path.join(jobdir, self.crawler_name, 'state_record.pkl')
            self.load_state()

        # Crawl every possible company (Very long runtime)
        if self.use_all_companies:
            # Fetch ticker.txt to get all companies
            yield scrapy.Request(
                "https://www.sec.gov/include/ticker.txt",
                callback=self.parse_ticker_file,
                headers=headers,
                dont_filter=True,
            )
        # If ticker are defined, use selected
        elif self.ticker_list:
            # First get the ticker-to-CIK mapping
            yield scrapy.Request(
                "https://www.sec.gov/include/ticker.txt",
                callback=self.parse_ticker_file_for_specific,
                headers=headers,
                meta={'ticker_list': self.ticker_list},
                dont_filter=True,
            )
        # If cik are defined, use selected
        elif self.cik_list:
            # Directly use provided CIKs
            for cik in self.cik_list:
                cik_padded = str(cik).zfill(10)
                url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
                yield scrapy.Request(url, callback=self.parse, headers=headers)
        else:
            self.logger.warning("No companies specified. Use use_all_companies=True, ticker_list=[], or cik_list=[]")

    def parse_ticker_file(self, response) -> Generator[Request, Any, None]:
        """Parse ticker.txt and create requests for all companies.

        :param response: ticker.txt
        :return:
        """
        headers = {"User-Agent": "YourCompany your.email@example.com"}
        lines = response.text.strip().split('\n')

        for line in lines:
            if '\t' in line:
                ticker, cik = line.split('\t')
                cik_padded = str(cik).zfill(10)
                url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"

                self.logger.info(f"Queuing company: {ticker.upper()} (CIK: {cik_padded})")

                yield scrapy.Request(
                    url,
                    callback=self.parse,
                    headers=headers,
                    meta={'ticker': ticker.upper()},
                )

    def parse_ticker_file_for_specific(self, response) -> Generator[Request, Any, None]:
        """Parse ticker.txt for specific tickers only.

        :param response: ticker.txt
        :return:
        """
        headers = {"User-Agent": "YourCompany your.email@example.com"}
        lines = response.text.strip().split('\n')
        ticker_list = [t.lower() for t in response.meta['ticker_list']]

        ticker_to_cik = {}
        for line in lines:
            if '\t' in line:
                ticker, cik = line.split('\t')
                if ticker.lower() in ticker_list:
                    ticker_to_cik[ticker.lower()] = cik

        # Create requests for found tickers
        for ticker, cik in ticker_to_cik.items():
            cik_padded = str(cik).zfill(10)
            url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"

            self.logger.info(f"Queuing company: {ticker.upper()} (CIK: {cik_padded})")

            yield scrapy.Request(
                url,
                callback=self.parse,
                headers=headers,
                meta={'ticker': ticker.upper()},
            )

    def parse(self, response, **kwargs) -> Generator[Request, Any, None]:
        """Parse function that fetches all filings and passes them further to extract information.

        :param response:
        :param kwargs:
        :return:
        """
        data = json.loads(response.text)
        filings = data.get("filings", {}).get("recent", {})

        # Store company info for later use
        cik = str(data['cik']).zfill(10)
        company_name = data.get('name', 'Unknown')
        ticker = response.meta.get('ticker', 'N/A')

        self.state_record['current_company_cik'] = cik
        self.state_record['current_company_ticker'] = ticker

        if cik in self.state_record['companies_processed']:
            self.logger.info(f"Company {cik} already processed")
            return

        self.logger.info(f"Processing {company_name} ({ticker})")

        for i, form_type in enumerate(filings.get("form", [])):
            if form_type in self.form_types:
                self.state_record['total_filings'] += 1

                accession = filings["accessionNumber"][i].replace("-", "")
                filing_url = urljoin(self.base_url, f"edgar/data/{cik}/{accession}/index.json")

                self.logger.info(f"Requesting filing index: {filing_url}")

                yield scrapy.Request(
                    filing_url,
                    callback=self.parse_filing_index,
                    headers=response.request.headers,
                    meta={
                        'company_name': company_name,
                        'cik': cik,
                        'ticker': ticker,
                    },
                )
        self.state_record['companies_processed'].append(cik)

        if len(self.state_record['companies_processed']) % 10 == 0:
            self.save_state()
            self.logger.info("Checkpoint")

    def parse_filing_index(self, response):
        """Parse filing.

        :param response:
        :return:
        """
        self.logger.info(f"Parsing index: {response.url}")

        try:
            index_data = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON from {response.url}")
            return

        items = index_data.get("directory", {}).get("item", [])
        self.logger.info(f"Found {len(items)} items in index")

        for doc in items:
            name = doc["name"]
            if name.endswith(".htm") or name.endswith(".html"):
                doc_url = response.url.replace("index.json", name)
                self.logger.info(f"Requesting document: {doc_url}")

                yield scrapy.Request(
                    doc_url,
                    callback=self.parse_filing_doc,
                    headers=response.request.headers,
                    meta=response.meta,
                )

    def parse_filing_doc(self, response):
        """Parse the actual filing document to search for keywords.

        :param response:
        """
        text = response.text
        text_lower = text.lower()

        self.state_record['urls_processed'].append(response.url)

        # Log for debugging
        self.logger.info(f"Parsing document: {response.url} ({len(text)} chars)")

        # Initialize has_keyword flag
        has_keyword = False
        found_keywords = []

        # Search for all configured keywords
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                has_keyword = True
                found_keywords.append(keyword)
                self.logger.info(f"Found keyword: '{keyword}' in {response.url}")

        if has_keyword:

            from pathlib import Path

            cik = response.meta.get('cik', 'unknown')
            accession = response.url.split('/')[-2]
            filename = f"{cik}_{accession}_{response.url.split('/')[-1]}"
            filepath = Path(self.output_path) / filename

            # Save the file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(response.text)

            self.nps_found_count += 1
            if self.nps_found_count == self.max_nps_found_count:
                if self.crawler.engine:
                    self.crawler.engine.close_spider(self, 'max_nps_findings_reached')
                else:
                    self.logger.error("Crawler engine not available to close spider.")

            yield FilingItem(
                company=response.meta.get('company_name', 'Unknown'),
                ticker=response.meta.get('ticker', 'N/A'),
                cik=response.meta.get('cik', 'Unknown'),
                filing_url=response.url,
                keywords_found=found_keywords,
                html_text=response.text,
            )
        else:
            self.logger.debug(f"No keywords found in {response.url}")
