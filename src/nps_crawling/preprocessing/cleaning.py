"""Text cleaning pipeline for preprocessing HTML content."""

import re
import warnings

from bs4 import BeautifulSoup, NavigableString, XMLParsedAsHTMLWarning

from nps_crawling.config import Config

# Ignore warning about parsing XML documents with an HTML parser
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class CleanTextPipeline(Config):
    """Text cleaning pipeline class."""

    def __init__(self):
        """Initialize with lowercased keyword list for table scanning."""
        self._keywords = [p.lower() for p in Config.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR]

    def cleaning_workflow(self, dict_batch):
        """Clean a batch of items by processing their 'html_text' fields."""
        cleaned_batch = []

        for item in dict_batch:
            cleaned_item = self.process_item(item)
            cleaned_batch.append(cleaned_item)

        return cleaned_batch

    def process_item(self, item: dict) -> dict:
        """Clean the 'core_text' field of an item by removing HTML tags.

        Normalizing whitespace, and stripping signature markers.
        """
        if "core_text" in item and isinstance(item["core_text"], str):
            # Parse HTML content into plain text
            soup = BeautifulSoup(item["core_text"], "lxml")

            # Collapse tables with keyword matches before extracting text.
            # Matching rows become a single compact sentence; all other rows
            # are discarded so the surrounding prose serves as context.
            self._collapse_keyword_tables(soup)

            # Extract visible text while keeping spaces between elements
            text = soup.get_text(separator=" ", strip=True)

            # Replace non-breaking spaces and newlines with normal spaces
            text = text.replace("\xa0", " ")
            text = text.replace("\n", " ")
            text = text.replace("\r", " ")

            # Remove signature-like markers such as '/s/ Name'
            text = re.sub(r'By:\s*/s/\s*[A-Za-z .-]+', '', text, flags=re.IGNORECASE)  # By: /s/ Name Name2
            text = re.sub(r'/s/\s*[A-Za-z .-]+', '', text)  # /s/ Name Name2

            # Store cleaned text back into the item
            item["core_text"] = text

        return item

    # ------------------------------------------------------------------
    # Table handling
    # ------------------------------------------------------------------

    def _collapse_keyword_tables(self, soup):
        """Replace tables that contain keyword hits with compact row strings.

        Tables without any keyword match are left untouched so that
        ``get_text()`` handles them as before.
        """
        for table in soup.find_all("table"):
            header_cells = self._extract_header(table)
            matching_row_texts = []

            for row in table.find_all("tr"):
                cells = [c.get_text(separator=" ", strip=True) for c in row.find_all(["td", "th"])]
                row_text_lower = " ".join(cells).lower()

                if any(kw in row_text_lower for kw in self._keywords):
                    matching_row_texts.append(
                        self._format_table_row(cells, header_cells)
                    )

            if not matching_row_texts:
                continue

            # Build a replacement string that ends with a period so the
            # sentence splitter in filtering.py can create a clean boundary.
            replacement = " ".join(matching_row_texts)
            table.replace_with(NavigableString(f" {replacement} "))

    @staticmethod
    def _extract_header(table):
        """Return the cells of the first <thead> row or first <tr> with <th>."""
        thead = table.find("thead")
        if thead:
            first_row = thead.find("tr")
            if first_row:
                return [th.get_text(separator=" ", strip=True) for th in first_row.find_all("th")]

        # Fallback: first <tr> that is made up entirely of <th> cells
        for row in table.find_all("tr", limit=5):
            ths = row.find_all("th")
            if ths and not row.find_all("td"):
                return [th.get_text(separator=" ", strip=True) for th in ths]

        return []

    @staticmethod
    def _format_table_row(cells, header_cells):
        """Turn a table row into a readable sentence like 'Col1: Val1 | Col2: Val2.'"""
        if header_cells and len(header_cells) == len(cells):
            parts = [f"{h}: {v}" for h, v in zip(header_cells, cells) if v]
        else:
            parts = [c for c in cells if c]

        return " | ".join(parts) + "."
