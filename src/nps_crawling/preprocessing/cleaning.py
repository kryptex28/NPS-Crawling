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

    # Max number of follow-up data rows pulled in when the keyword hits a
    # section-label row (a row with no numeric content).
    _SECTION_FOLLOW_ROWS = 5

    def _collapse_keyword_tables(self, soup):
        """Replace keyword-containing tables with LLM-friendly sentences.

        Fast path: one ``get_text`` per table as a keyword pre-check.  Tables
        with no hit are left untouched (the surrounding ``get_text`` pass
        handles them), so the expensive per-row parsing only runs for the
        small fraction of tables that actually contain a keyword.

        Slow path emits one self-contained sentence per relevant row.  Each
        sentence carries the table's caption (from ``<caption>`` or a short
        preceding heading), column headers zipped against values, and the
        row label.  Three hit patterns are handled:

        1. **Data-row hit** — keyword is on a numeric row.  Emit that row.
        2. **Section-label hit** — keyword is on a non-numeric label row
           ("Net Promoter Score" as a subsection heading).  Merge the label
           with the next few data rows into one sentence so keyword and
           numbers stay inside one context window.
        3. **Column-header hit** — keyword only appears in a column header.
           Emit each data row showing only the relevant column(s), so the
           LLM sees the row label + value without the noise of unrelated
           columns.
        """
        for table in soup.find_all("table"):
            table_text_lower = table.get_text(" ", strip=True).lower()
            if not any(kw in table_text_lower for kw in self._keywords):
                continue

            parsed_rows = []
            for row in table.find_all("tr"):
                cells = [
                    c.get_text(" ", strip=True)
                    for c in row.find_all(["td", "th"])
                ]
                cells = [c for c in cells if not self._is_noise_cell(c)]
                if cells:
                    parsed_rows.append(cells)

            if not parsed_rows:
                continue

            header, body_start = self._split_header_body(parsed_rows)
            caption = self._extract_caption(table)
            prefix = f"Table '{caption}'" if caption else "Table"

            sentences = []

            # Patterns 1 + 2: keyword appears somewhere in a body row.
            for i in range(body_start, len(parsed_rows)):
                cells = parsed_rows[i]
                if not any(kw in " ".join(cells).lower() for kw in self._keywords):
                    continue

                if self._has_digit(cells):
                    sentences.append(
                        f"{prefix} | {self._format_row(cells, header)}."
                    )
                    continue

                parts = [f"{prefix} | Section: {' '.join(cells)}"]
                for follow in parsed_rows[i + 1 : i + 1 + self._SECTION_FOLLOW_ROWS]:
                    if self._is_header_like(follow):
                        break
                    if not self._has_digit(follow):
                        break
                    parts.append(self._format_row(follow, header))
                sentences.append(" | ".join(parts) + ".")

            # Pattern 3: keyword only in column header — emit data rows with
            # just the relevant column(s) so each row becomes a clean
            # "<row label> | <keyword col>: <value>" sentence.
            if not sentences and header:
                relevant_cols = [
                    idx for idx, h in enumerate(header)
                    if any(kw in h.lower() for kw in self._keywords)
                ]
                if relevant_cols:
                    for cells in parsed_rows[body_start:]:
                        if len(cells) != len(header) or not self._has_digit(cells):
                            continue
                        label = cells[0]
                        values = [
                            f"{header[c]}: {cells[c]}"
                            for c in relevant_cols
                            if cells[c]
                        ]
                        if values:
                            sentences.append(
                                f"{prefix} | {label} | " + " | ".join(values) + "."
                            )

            if not sentences:
                continue

            replacement = " ".join(sentences)
            table.replace_with(NavigableString(f" [TABLE] {replacement} [/TABLE] "))

    @staticmethod
    def _is_noise_cell(text: str) -> bool:
        """True for empty or pure-punctuation cells ("$", "%", "—", "(", ")")."""
        return not any(ch.isalnum() for ch in text)

    @staticmethod
    def _has_digit(cells) -> bool:
        """True if any cell contains a digit."""
        return any(any(ch.isdigit() for ch in c) for c in cells)

    @classmethod
    def _is_header_like(cls, cells) -> bool:
        """Heuristic: a row is header-like if most cells are non-numeric labels."""
        if not cells:
            return False
        non_numeric = sum(
            1 for c in cells if not any(ch.isdigit() for ch in c)
        )
        return non_numeric >= max(1, int(len(cells) * 0.6))

    @classmethod
    def _split_header_body(cls, parsed_rows):
        """Return ``(header_row, body_start_index)`` for a parsed table.

        Walks the top of the table collecting consecutive header-like rows
        (max 3) and picks the one with the most cells as the effective
        header — typically the row closest to the data with the most
        specific labels (e.g. year columns under a grouped
        "Three Months Ended" super-header).  Returns ``([], 0)`` when no
        header can be identified.
        """
        header_rows = []
        for row in parsed_rows[:3]:
            if cls._is_header_like(row):
                header_rows.append(row)
            else:
                break
        if not header_rows:
            return [], 0
        best = max(header_rows, key=len)
        return best, len(header_rows)

    @staticmethod
    def _extract_caption(table) -> str:
        """Return the table's caption or a short preceding heading, if any."""
        cap = table.find("caption", recursive=False)
        if cap:
            text = cap.get_text(" ", strip=True)
            if text:
                return text[:200]
        prev = table.find_previous_sibling()
        if prev is not None and prev.name in {
            "p", "h1", "h2", "h3", "h4", "h5", "h6", "b", "strong", "div",
        }:
            text = prev.get_text(" ", strip=True)
            if text and 5 < len(text) < 200:
                return text
        return ""

    @staticmethod
    def _format_row(cells, header_cells) -> str:
        """Format a row as ``'Col1: Val1 | Col2: Val2'`` (no trailing period).

        Falls back to a plain pipe-joined list when header length doesn't
        match the row length.
        """
        if header_cells and len(header_cells) == len(cells):
            parts = [f"{h}: {v}" for h, v in zip(header_cells, cells) if v]
        else:
            parts = list(cells)
        return " | ".join(parts)
