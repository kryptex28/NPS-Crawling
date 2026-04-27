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
        self._excluded = [p.lower() for p in Config.LIST_OF_PHRASES_TO_EXCLUDE]

    def _mask_excluded(self, text_lower: str) -> str:
        """Blank out excluded phrases so their substrings don't trigger matches."""
        for excluded in self._excluded:
            if excluded:
                text_lower = text_lower.replace(excluded, " " * len(excluded))
        return text_lower

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

    # Max follow-up data rows pulled in when the keyword hits a pure
    # section-label row (single-cell non-numeric row).
    _SECTION_FOLLOW_ROWS = 5

    # Trailing standalone digits on a cell label that look like footnote
    # markers (e.g. "Net Promoter Score 4", "Core Earnings Per Share 1").
    # We keep them visible in row text but strip them when using the label
    # as a key in formatted segments so classification sees clean phrases.
    _TRAILING_FOOTNOTE_RE = re.compile(r"\s+\d{1,2}$")

    def _collapse_keyword_tables(self, soup):
        """Replace keyword-containing tables with a single compact sentence.

        SEC-filing tables come in a wide variety of shapes: compensation
        scorecards (label + threshold/target/maximum/result), metric
        mappings (stakeholder → list of KPIs), KPI trends (metric × years),
        free-text bullet wrappers, and so on. The collapse keeps every
        keyword-matching row (plus surrounding structure) while emitting
        the whole table as ONE sentence so that the downstream sentence
        splitter and context-window builder treat it atomically.

        Output shape::

            [TABLE] <caption>: <row_seg_1> ; <row_seg_2> ; ... [/TABLE].

        Row segments attach the nearest preceding section label where one
        exists, so a compensation-table hit becomes
        ``"Customer Satisfaction — Net Promoter Score (NPS): Weight: 12 |
        Threshold: 43 | Target: 45 | Maximum: 47 | Result: 40 | ..."``.

        Three hit patterns are handled:

        1. **Data-row hit** — keyword is on a row containing digits. Emit
           that row with ``header: value`` pairs and its section prefix.
        2. **Non-numeric body-row hit** — keyword is on a non-numeric body
           row. Two sub-cases:
             a. Multi-cell mapping row (e.g. "Our Customers | NPS, CSAT, …"):
                emit via ``_format_row`` so the column context is preserved.
             b. Single-cell section-style row: treat as a section heading and
                pull in the next few numeric rows so keyword and values land
                in one segment.
        3. **Column-header hit** — keyword only appears in a column header.
           Emit each data row showing just the relevant column(s).

        Fast path: one ``get_text`` per table as a keyword pre-check. Tables
        with no hit (and layout tables masquerading as prose bullet lists)
        are left untouched — the surrounding ``get_text`` pass handles them.
        """
        for table in soup.find_all("table"):
            table_text_lower = self._mask_excluded(table.get_text(" ", strip=True).lower())
            if not any(kw in table_text_lower for kw in self._keywords):
                continue

            # SEC filings frequently render bulleted paragraphs as <table>
            # (bullet glyph in col 1, full sentence in col 2). Wrapping those
            # in [TABLE] markers turns a readable bullet into table noise and
            # discards any rows that don't carry the keyword. Skip the
            # collapse so the outer get_text() pass flattens them as prose.
            if self._is_layout_table(table):
                continue

            parsed_rows = self._parse_table_rows(table)
            if not parsed_rows:
                continue

            caption, header, body = self._structure_table(parsed_rows, table)
            row_segments = self._build_row_segments(body, header)

            if not row_segments:
                continue

            body_text = " ; ".join(row_segments)
            if caption:
                body_text = f"{caption}: {body_text}"

            # One sentence per table: periods inside [TABLE] blocks are
            # protected by the sentence splitter in filtering.py, so
            # abbreviations ("Messrs.", "Inc.") and decimals survive
            # untouched. The trailing "." after [/TABLE] is the real
            # boundary the splitter will break on.
            table.replace_with(NavigableString(f" [TABLE] {body_text} [/TABLE]. "))

    # ------------------------------------------------------------------
    # Table structure helpers
    # ------------------------------------------------------------------

    def _parse_table_rows(self, table):
        """Return a list of cell-lists with noise cells removed.

        Empty rows (after noise filtering) are dropped, and each cell text
        has its whitespace collapsed.
        """
        parsed = []
        for row in table.find_all("tr"):
            cells = []
            for cell in row.find_all(["td", "th"]):
                text = re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).strip()
                if not self._is_noise_cell(text):
                    cells.append(text)
            if cells:
                parsed.append(cells)
        return parsed

    def _structure_table(self, rows, table):
        """Classify rows into caption, header, and body (with section prefixes).

        Uses the most common *body* (digit-bearing) row width as the
        "canonical" column count: the first header-candidate row matching
        that width is the real column header. A header candidate is a
        multi-cell row where most cells contain letters — this tolerates
        headers that carry embedded digits ("Threshold (50% payout)",
        "2024", "Q1 2023") while still rejecting pure-data rows. Narrow
        rows above the header (typical ``colspan`` titles like
        "For Messrs. Norcia, Ruud, and Meador:") are folded into the
        caption rather than broadcast across every column — that
        broadcasting was the source of garbled segments like
        ``"For Messrs... Measures Financial Performance:: Net Promoter Score"``
        in the previous implementation.

        Body rows carry a ``section`` field — the most recent single-cell,
        non-numeric row that preceded them — so a DTE-style compensation
        table emits ``"Customer Satisfaction — Net Promoter Score (NPS):
        Target: 45 | Result: 40"`` instead of orphaning the section label.
        """
        canonical_cols = self._canonical_column_count(rows)

        header_idx = -1
        for i, cells in enumerate(rows):
            if not self._is_header_candidate(cells):
                continue
            if canonical_cols == 0 or len(cells) == canonical_cols:
                header_idx = i
                break
        if header_idx == -1:
            for i, cells in enumerate(rows):
                if self._is_header_candidate(cells):
                    header_idx = i
                    break

        if header_idx >= 0:
            header = [self._normalize_header_cell(c) for c in rows[header_idx]]
            pre_header_rows = rows[:header_idx]
            body_rows_raw = rows[header_idx + 1 :]
        else:
            header = []
            pre_header_rows = []
            body_rows_raw = rows

        # Caption: <caption>/preceding heading + any single-cell "title"
        # rows above the header (flattened, deduplicated).
        external_caption = self._extract_caption(table)
        pre_header_text = " ".join(
            c for row in pre_header_rows for c in row
        ).strip().rstrip(":")
        caption = " — ".join(x for x in [external_caption, pre_header_text] if x)
        caption = caption[:300].strip()

        # Body rows with section attribution. Single-cell non-numeric rows
        # become the running "section" for subsequent rows.
        body = []
        current_section = None
        for cells in body_rows_raw:
            if len(cells) == 1 and not self._has_digit(cells):
                current_section = cells[0].rstrip(":").strip()
                continue
            body.append({"cells": cells, "section": current_section})

        return caption, header, body

    def _build_row_segments(self, body, header):
        """Emit segments for each keyword-hit row in the body.

        Handles all three hit patterns (data row, non-numeric body row,
        column-header hit) and prefixes each segment with its section
        label when one is in scope.
        """
        segments = []

        # Patterns 1 + 2: keyword appears in a body row.
        for i, row_info in enumerate(body):
            cells = row_info["cells"]
            row_text_lower = self._mask_excluded(" ".join(cells).lower())
            if not any(kw in row_text_lower for kw in self._keywords):
                continue

            if self._has_digit(cells):
                segments.append(
                    self._attach_section(
                        self._format_row(cells, header), row_info["section"],
                    ),
                )
                continue

            # Non-numeric body row hit.
            if len(cells) >= 2:
                # Mapping-style row: preserve the column context so a
                # "Our Customers | Net Promoter Score, CSAT, ..." row
                # doesn't collapse into a run-on.
                segments.append(
                    self._attach_section(
                        self._format_row(cells, header), row_info["section"],
                    ),
                )
                continue

            # Single-cell hit — treat this row as a section heading and
            # pull in the next few numeric rows so the keyword lands in
            # one segment with its values.
            label = cells[0].rstrip(":").strip()
            follow_parts = []
            for j in range(i + 1, min(i + 1 + self._SECTION_FOLLOW_ROWS, len(body))):
                follow_cells = body[j]["cells"]
                if not self._has_digit(follow_cells):
                    break
                follow_parts.append(self._format_row(follow_cells, header))
            if follow_parts:
                segments.append(f"{label}: " + " ; ".join(follow_parts))
            else:
                segments.append(self._attach_section(label, row_info["section"]))

        # Pattern 3: keyword only in column header.
        if not segments and header:
            relevant_cols = [
                idx for idx, h in enumerate(header)
                if any(kw in self._mask_excluded(h.lower()) for kw in self._keywords)
            ]
            if relevant_cols:
                for row_info in body:
                    cells = row_info["cells"]
                    if len(cells) != len(header) or not self._has_digit(cells):
                        continue
                    label = self._clean_row_label(cells[0])
                    values = [
                        f"{header[c]}: {cells[c]}"
                        for c in relevant_cols
                        if c < len(cells) and cells[c]
                    ]
                    if values:
                        segments.append(
                            self._attach_section(
                                f"{label} | " + " | ".join(values),
                                row_info["section"],
                            ),
                        )

        return segments

    @staticmethod
    def _attach_section(segment: str, section: str | None) -> str:
        """Prefix a row segment with its section label, if any."""
        if not section:
            return segment
        return f"{section} — {segment}"

    @staticmethod
    def _is_header_candidate(cells) -> bool:
        """True when a row looks like a column-header row.

        Header rows are multi-cell and the majority of cells contain
        letters (labels). This is lenient enough to accept headers with
        embedded digits ("Threshold (50% payout)", "Q1 2024") while
        rejecting pure-data rows like ``['NPS', '80', '100', '140']``
        where only the label cell has letters.
        """
        if len(cells) < 2:
            return False
        label_like = sum(
            1 for c in cells if any(ch.isalpha() for ch in c)
        )
        return label_like * 2 >= len(cells)

    @classmethod
    def _canonical_column_count(cls, rows) -> int:
        """Return the most common cell count among digit-bearing rows.

        Falls back to 0 when no data row exists, letting the header
        detector accept any multi-cell non-numeric row.
        """
        counts = {}
        for r in rows:
            if cls._has_digit(r):
                counts[len(r)] = counts.get(len(r), 0) + 1
        if not counts:
            return 0
        return max(counts, key=counts.get)

    @classmethod
    def _clean_row_label(cls, text: str) -> str:
        """Strip trailing footnote markers and colons from a row label."""
        text = cls._TRAILING_FOOTNOTE_RE.sub("", text)
        return text.rstrip(":").strip()

    @classmethod
    def _normalize_header_cell(cls, text: str) -> str:
        """Normalize a header cell: drop trailing ':' and footnote refs."""
        text = cls._TRAILING_FOOTNOTE_RE.sub("", text)
        return text.rstrip(":").strip()

    # Minimum word count for a cell to count as "prose". Data-table cells
    # (numbers, short labels, compound headers like "Three Months Ended
    # December 31, 2024") stay well below this; a full sentence always
    # clears it.
    _PROSE_CELL_WORD_THRESHOLD = 15

    @classmethod
    def _is_layout_table(cls, table) -> bool:
        """True when a <table> is used as a layout container for prose.

        Detects the SEC-filing pattern of rendering bulleted lists as
        tables: the majority of alnum-bearing cells are full sentences
        rather than compact data values. Pure-punctuation cells (bullet
        glyphs, dividers) are ignored so a two-column "bullet | sentence"
        row counts as a single prose cell.
        """
        content_cells = []
        for row in table.find_all("tr"):
            for cell in row.find_all(["td", "th"]):
                text = cell.get_text(" ", strip=True)
                if any(ch.isalnum() for ch in text):
                    content_cells.append(text)
        if not content_cells:
            return False
        prose_count = sum(
            1 for c in content_cells
            if len(c.split()) >= cls._PROSE_CELL_WORD_THRESHOLD
        )
        return prose_count * 2 >= len(content_cells)

    @staticmethod
    def _is_noise_cell(text: str) -> bool:
        """True for empty or pure-punctuation cells ("$", "%", "—", "(", ")")."""
        return not any(ch.isalnum() for ch in text)

    @staticmethod
    def _has_digit(cells) -> bool:
        """True if any cell contains a digit."""
        return any(any(ch.isdigit() for ch in c) for c in cells)

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

    @classmethod
    def _format_row(cls, cells, header_cells) -> str:
        """Format a row as ``'Col1: Val1 | Col2: Val2'`` (no trailing period).

        The first cell is treated as the row label and has its trailing
        footnote marker / colon stripped. Falls back to a plain pipe-joined
        list when header length doesn't match the row length.
        """
        cells = list(cells)
        if cells:
            cells[0] = cls._clean_row_label(cells[0])
        if header_cells and len(header_cells) == len(cells):
            parts = [f"{h}: {v}" for h, v in zip(header_cells, cells) if h and v]
        else:
            parts = [c for c in cells if c]
        return " | ".join(parts)
