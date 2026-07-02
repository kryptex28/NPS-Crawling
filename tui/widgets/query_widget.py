from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.validation import Number
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RadioButton,
    RadioSet,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
    OptionList
)
from rich.text import Text
from textual.widgets import SelectionList
from textual.widgets.selection_list import Selection

from constants import FILING_CATEGORIES
from constants import US_STATES

from models.query_model import QueryModel
from screens.filing_types_screen import FilingTypesScreen
from data_package.query_data import QueryData
from data_package.entity_data import EntityData

class QueryWidget(Container):

    DEFAULT_CSS = """
    QueryWidget #entity-fuzzy-results {
        display: none;
        height: auto;
        max-height: 8;
        margin-top: 1;
        border: round $primary-darken-2;
        background: $panel;
    }
    QueryWidget #entity-fuzzy-results.visible {
        display: block;
    }

    """

    def __init__(self):
        super().__init__()
        self.model = QueryModel()
        self._selected_ids: set[str] = set()
        self._fuzzy_results: dict[str, EntityData] = {}

    def compose(self) -> ComposeResult:
        with Horizontal(id="crawl-layout"):
            with ScrollableContainer(id="left-panel"):
                yield Static("Search Parameters", classes="panel-title")

                # Query Base
                with Vertical(classes="form-row"):
                    yield Label("Query Base URL")
                    yield Input(
                        placeholder="default: https://efts.sec.gov/LATEST/search-index?",
                        id="inp-query-base"
                    )

                # Keyword
                with Vertical(classes="form-row"):
                    yield Label("Document word or phrase")
                    yield Input(
                        placeholder="Keywords",
                        id="inp-keyword"
                    )
                # Entity
                with Vertical(classes="form-row"):
                    yield Label("Company Name, ticker, CIK, or individual's name")
                    yield Input(
                        placeholder="Company, ticker, CIK or name",
                        id="inp-entity"
                    )
                    yield Button("Start Fuzzy Search", id="inp-entity-fuzzy")
                    yield OptionList(id="entity-fuzzy-results")
                # Filing category + types
                with Horizontal(classes="grid-2 form-row"):
                    with Vertical():
                        yield Label("Filing category")
                        yield Select(
                            [(label, val) for label, val in FILING_CATEGORIES],
                            id="sel-category",
                            value="",
                        )
                    with Vertical():
                        yield Label("Filing types  [F2 to browse]")
                        yield Button(
                            "Browse filing types…",
                            id="btn-filing-types",
                            variant="default",
                        )
                        yield Label("None selected", id="filing-types-label")

                # Date range
                with Vertical(classes="form-row"):
                    yield Label("Filed date range")
                    with RadioSet(id="date-range-set"):
                        yield RadioButton("All (since 2001)", value=True, id="dr-all")
                        yield RadioButton("Last 10 years", id="dr-10y")
                        yield RadioButton("Last 5 years", id="dr-5y")
                        yield RadioButton("Last year", id="dr-1y")
                        yield RadioButton("Last 30 days", id="dr-30d")
                        yield RadioButton("Custom", id="dr-custom")

                # Custom dates (hidden until Custom is chosen)
                with Horizontal(id="custom-dates"):
                    with Vertical(classes="form-row"):
                        yield Label("Filed from")
                        yield Input(placeholder="YYYY-MM-DD", id="inp-from-date")
                    with Vertical(classes="form-row"):
                        yield Label("Filed to")
                        yield Input(placeholder="YYYY-MM-DD", id="inp-to-date")

                with Vertical(classes="form-row"):
                    yield Static("Query Filing Limit")
                    yield Input("", placeholder="default: -1 (no limit)", id="query-filing-limit", validators=[Number(minimum=-1)])

                # Actions
                with Horizontal(id="form-actions"):
                    yield Button("Create Query", variant="primary", id="btn-create")
                    yield Button("Clear all", variant="default", id="btn-clear")
                    yield Button("Configuration", variant="default", id="btn-config")

            # Right: query list
            with Vertical(id="right-panel"):
                yield Static("Query Queue", id="right-panel-title")
                with Horizontal(id="query-toolbar"):
                    yield Button("Select All", id="btn-select-all", variant="default")
                    yield Button("Delete", id="btn-delete", variant="error")
                    yield Button("Refresh", id="btn-refresh", variant="default")
                    yield Button("View", id="btn-view", variant="default")
                yield DataTable(id="query-table", cursor_type="row", zebra_stripes=True)
                yield Button("Accept Queries", id="accept-queries-btn", variant="success")

    @on(Button.Pressed, "#btn-refresh")
    async def query_refresh(self):
        self._refresh_table()

    @on(Button.Pressed, "#accept-queries-btn")
    async def accept_queries(self):
        self.model.accept_queries()
        self.notify(title="Query", message="Queries accepted for Crawling")

    @on(Button.Pressed, "#btn-create")
    async def query_create(self):
        query_base: str = self.query_one("#inp-query-base", Input).value.strip()
        keyword: str = self.query_one("#inp-keyword", Input).value.strip()
        from_date: str = self.query_one("#inp-from-date", Input).value.strip()
        to_date: str = self.query_one("#inp-to-date", Input).value.strip()
        entity: str = self.query_one("#inp-entity", Input).value.strip()
        limit: int = int(self.query_one("#query-filing-limit", Input).value)

        cat_sel = self.query_one("#sel-category", Select)
        filing_category: str = str(cat_sel.value) if cat_sel.value != Select.BLANK else ""
        filing_categories: list[str] = self.model.get_filing_categories()

        if filing_categories:
            filing_category = "custom"


        if not keyword:
            self.notify("Please fill in at least one search field.", severity="warning")
            return

        rs = self.query_one("#date-range-set", RadioSet)
        date_range_map = {
            "dr-all": "all", "dr-10y": "10y", "dr-5y": "5y",
            "dr-1y": "1y", "dr-30d": "30d", "dr-custom": "custom",
        }
        date_range = "all"
        if rs.pressed_button:
            date_range = date_range_map.get(rs.pressed_button.id, "all")

        data = QueryData(
            id="",
            query_base=query_base,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            date_range=date_range,
            entity=entity,
            filing_category=filing_category,
            filing_types=filing_categories,
            selected=False,
            limit=limit,
        )

        self.model.create_query(data=data)
        self._refresh_table()

    def _refresh_table(self) -> None:
        table = self.query_one("#query-table", DataTable)
        table.clear(columns=False)
        for q in self.model.get_queries():
            query_display = getattr(q, "query", None)
            if query_display is None:
                query_display = getattr(q, "keyword", "")
            date_range = getattr(q, "date_range", "")

            row_id = q.id

            if row_id in self._selected_ids:
                table.add_row(
                    Text(str(row_id), style="bold green"),
                    Text(query_display, style="bold green"), 
                    Text(date_range, style="bold green"),
                    key=row_id
                )
            else:
                table.add_row(
                    Text(str(row_id)),
                    Text(query_display), 
                    Text(date_range),
                    key=row_id
                )

    @on(DataTable.RowSelected, "#query-table")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#query-table", DataTable)

        row_id = str(table.get_cell(event.row_key, table.ordered_columns[0].key))

        if row_id in self._selected_ids:
            self.model.remove_selected(row_id)
            style = ""
        else:
            self.model.add_selected(row_id)
            style = "bold white on green"
        
        table = self.query_one("#query-table", DataTable)
        cols = table.ordered_columns
        for col in cols:
            current = table.get_cell(event.row_key, col.key)
            # strip Rich markup to get plain text back
            plain = current.plain if hasattr(current, "plain") else str(current)
            table.update_cell(event.row_key, col.key, Text(plain, style=style))

        self._update_row_highlight(event.row_key, row_id)

    def _update_row_highlight(self, row_key, row_id: str) -> None:
        table = self.query_one("#query-table", DataTable)
        #selected_label = self.query_one("#selected-count", Static)
        #selected_label.update(f"{len(self._selected_ids)} selected")

    @on(Button.Pressed, "#btn-select-all")
    def select_all(self) -> None:
        table = self.query_one("#query-table", DataTable)
        col_key = table.ordered_columns[0].key
        all_ids = {
            str(table.get_cell(rk, col_key).plain) 
            for rk in table.rows
        }

        if self._selected_ids == all_ids:
            self._selected_ids.clear()
            self.model.selected_queries.clear()
            style = ""
        else:
            self._selected_ids = all_ids
            self.model.selected_queries = set(all_ids)
            style = "bold white on green"

        cols = table.ordered_columns
        for row_key in table.rows:
            for col in cols:
                current = table.get_cell(row_key, col.key)
                plain = current.plain if hasattr(current, "plain") else str(current)
                table.update_cell(row_key, col.key, Text(plain, style=style))

    @on(Button.Pressed, "#btn-delete")
    def delete_selected(self) -> None:
        for query_id in self.model.selected_queries:
            self.model.delete_query(query_id)  

        self.model.selected_queries.clear()
        self._selected_ids.clear()
        self._refresh_table()

        self.notify(title="Queries deleted", message="All selected queries were deleted successfully")

    def on_mount(self) -> None:
        table = self.query_one("#query-table", DataTable)
        table.add_columns("ID", "Query", "Date range")

    def _get_date_range(self) -> str:
        """Return the selected date range key from the radio buttons.

        Possible return values: 'all', '10y', '5y', '1y', '30d', 'custom'.
        """
        # map of selector to return value
        mapping = {
            "#dr-all": "all",
            "#dr-10y": "10y",
            "#dr-5y": "5y",
            "#dr-1y": "1y",
            "#dr-30d": "30d",
            "#dr-custom": "custom",
        }
        for sel, name in mapping.items():
            try:
                rb = self.query_one(sel, RadioButton)
            except Exception:
                rb = None
            if rb is None:
                continue
            # RadioButton implementations may expose different properties for selection
            if getattr(rb, "value", False) is True:
                return name
            if getattr(rb, "pressed", False):
                return name
            if getattr(rb, "selected", False):
                return name
        return "all"

    @on(Button.Pressed, "#inp-entity-fuzzy")
    def _fuzzy_search(self):
        entity_text: str = self.query_one("#inp-entity", Input).value.strip()

        if not entity_text:
            self.notify("Enter a name, ticker, or CIK first.", severity="warning")
            return

        results: list[EntityData] = self.model.fuzzy_search(entity_text)

        option_list = self.query_one("#entity-fuzzy-results", OptionList)
        option_list.clear_options()

        if not results:
            option_list.remove_class("visible")
            self.notify("No matches found.", severity="warning")
            return

        self._fuzzy_results = {}  # map prompt -> EntityData
        for entity in results:
            label = f"{entity.title}  (CIK: {entity.cik} TICKER: {entity.ticker})"
            option_list.add_option(label)
            self._fuzzy_results[label] = entity

        option_list.add_class("visible")

    @on(OptionList.OptionSelected, "#entity-fuzzy-results")
    def _on_entity_selected(self, event: OptionList.OptionSelected) -> None:
        label = str(event.option.prompt)
        entity = self._fuzzy_results.get(label)

        if entity:
            self.query_one("#inp-entity", Input).value = entity.ticker

        option_list = self.query_one("#entity-fuzzy-results", OptionList)
        option_list.clear_options()
        option_list.remove_class("visible")