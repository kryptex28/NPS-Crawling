import scrapy
import json
import re
from urllib.parse import urljoin
from crawler.items import FilingItem


class SECNpsSpider(scrapy.Spider):
    name = "sec_nps"
    allowed_domains = ["sec.gov"]
    start_urls = [
        "https://data.sec.gov/submissions/CIK0000320193.json",  # Apple
        "https://data.sec.gov/submissions/CIK0000789019.json",  # Microsoft
    ]

    def start_requests(self):
        headers = {"User-Agent": "YourName your.email@example.com"}
        for url in self.start_urls:
            yield scrapy.Request(url, headers=headers)

    def parse(self, response):
        data = json.loads(response.text)
        filings = data.get("filings", {}).get("recent", {})
        base_url = "https://www.sec.gov/Archives/"

        # Store company info for later use
        cik = str(data['cik']).zfill(10)  # Pad CIK to 10 digits
        company_name = data.get('name', 'Unknown')

        # Limit to 10 filings
        for i, form_type in enumerate(filings.get("form", [])[:10]):
            if form_type in ["10-K", "10-Q", "8-K"]:
                accession = filings["accessionNumber"][i].replace("-", "")
                # Fix: Use padded CIK
                filing_url = urljoin(base_url, f"edgar/data/{cik}/{accession}/index.json")

                self.logger.info(f"Requesting filing index: {filing_url}")

                yield scrapy.Request(
                    filing_url,
                    callback=self.parse_filing_index,
                    headers=response.request.headers,
                    meta={'company_name': company_name, 'cik': cik}
                )

    def parse_filing_index(self, response):
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
                    meta=response.meta
                )

    def parse_filing_doc(self, response):
        text = response.text
        text_lower = text.lower()

        # Log for debugging
        self.logger.info(f"Parsing document: {response.url} ({len(text)} chars)")

        # Search for "revenue" - virtually guaranteed in 10-K/10-Q filings
        has_keyword = False
        if "revenue" in text_lower:
            has_keyword = True
            self.logger.info(f"✅ Found 'revenue' in {response.url}")

        if has_keyword:
            yield FilingItem(
                company=response.meta.get('company_name', 'Unknown'),
                filing_url=response.url,
                content_excerpt=self.extract_context(text_lower),
            )
        else:
            self.logger.debug(f"No revenue mention found in {response.url}")

    def extract_context(self, text):
        """Extract a snippet around the keyword for context"""
        # Search for "revenue" with surrounding context
        match = re.search(r"(.{0,200}revenue.{0,200})", text, re.IGNORECASE)

        if match:
            # Clean up HTML tags and excessive whitespace
            context = match.group(1)
            context = re.sub(r'<[^>]+>', ' ', context)  # Remove HTML tags
            context = re.sub(r'\s+', ' ', context)  # Normalize whitespace
            return context.strip()

        return ""