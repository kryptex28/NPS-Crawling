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
)
from textual.widgets import SelectionList
from textual.widgets.selection_list import Selection

from constants import FILING_CATEGORIES
from constants import US_STATES

from models.query_model import QueryModel
from screens.filing_types_screen import FilingTypesScreen

class QueryWidget(Container):

    def __init__(self):
        super().__init__()
        self.model = QueryModel()
        self._selected_ids: set[str] = set()

    def compose(self) -> ComposeResult:

        with Horizontal(id="crawl-layout"):
            with ScrollableContainer(id="left-panel"):
                yield Static("Search Parameters", classes="panel-title")

                # Query
                with Vertical(classes="form-row"):
                    yield Label("Document word or phrase")
                    yield Input(
                        placeholder="Keywords",
                        id="inp-query"
                    )
                # Entity
                with Vertical(classes="form-row"):
                    yield Label("Company Name, ticker, CIK, or individual's name")
                    yield Input(
                        placeholder="Company, ticker, CIK or name",
                        id="inp-entity"
                    )
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
                        yield Static("None selected", id="filing-types-badge")

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
                yield DataTable(id="query-table", cursor_type="row", zebra_stripes=True)
                yield Button("Accept Queries", id="accept-queries-btn", variant="success")

    @on(Button.Pressed, "#btn-create")
    async def query_create(self):
        
        data: dict[str, object] = {
            "query": self.query_one("#inp-query", Input).value,
            "entity": self.query_one("#inp-entity", Input).value,
            "filing_category": self.query_one("#sel-category", Select).value,
            "filing_types": [],  # fill later
            "date_range": self._get_date_range(),
            "from_date": self.query_one("#inp-from-date", Input).value,
            "to_date": self.query_one("#inp-to-date", Input).value,
        }
        # create the query in the model
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
            table.add_row(q.id, query_display, date_range)

    @on(DataTable.RowSelected, "#query-table")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#query-table", DataTable)

        row_id = str(table.get_cell(event.row_key, table.ordered_columns[0].key))

        if row_id in self._selected_ids:
            self._selected_ids.remove(row_id)
        else:
            self._selected_ids.add(row_id)
        
        self._update_row_highlight(event.row_key, row_id)

    def _update_row_highlight(self, row_key, row_id: str) -> None:
        table = self.query_one("#query-table", DataTable)
        #selected_label = self.query_one("#selected-count", Static)
        #selected_label.update(f"{len(self._selected_ids)} selected")

    @on(Button.Pressed, "#btn-select-all")
    def select_all(self) -> None:
        table = self.query_one("#query-table", DataTable)
        col_key = table.ordered_columns[0].key
        self._selected_ids = {
            str(table.get_cell(rk, col_key))
            for rk in table.rows
        }
        #self.query_one("#selected-count", Static).update(
        #    f"{len(self._selected_ids)} selected"
        #)

    @on(Button.Pressed, "#btn-delete")
    def delete_selected(self) -> None:
        #for query_id in self._selected_ids:
            #self.model.delete_query(query_id)   # add this to QueryModel
        self._selected_ids.clear()
        self._refresh_table()



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
