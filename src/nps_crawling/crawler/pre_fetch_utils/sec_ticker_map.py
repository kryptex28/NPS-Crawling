import re

import requests
from nps_crawling.config import Config


class SecTickerMap:
    _instance = None
    _data: dict = {}
    _fuzzy_data: list[tuple[str, str, str]] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load() # TODO: Replace somehow, may slow down startup time
        return cls._instance

    def _load(self):
        headers = {
            "User-Agent": "your-app-name contact@youremail.com",
        }
        response = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=headers,
        )
        response.raise_for_status()
        self._data = {
            str(v["cik_str"]).zfill(10): v["ticker"]
            for v in response.json().values()
        }
        for v in response.json().values():
            self._fuzzy_data.append((str(v["cik_str"]).zfill(10), v["ticker"], v["title"]))
            

    def get_ticker(self, cik: str) -> str | None:
        cik = cik.zfill(10)
        return self._data.get(cik)

    def get_tickers_from_string(self, text: str) -> list[str]:
        """Extract all tickers from the display string."""
        match = re.search(r'\(([A-Z,\s-]+)\)\s+\(CIK', text)
        if not match:
            return []
        return [t.strip() for t in match.group(1).split(",")]

    def get_tickers_from_strings(self, text: list[str]) -> list[str]:
        """Extract all tickers from multiple display string."""
        ticker: list[str] = []
        for t in text:
            ticker.extend(self.get_tickers_from_string(t))
        return ticker

    def get_fuzzy_data(self) -> list[tuple[str, str, str]]:
        return self._fuzzy_data