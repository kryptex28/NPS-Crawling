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

class QueryWidget(Container):

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

                # Exec offices / incorporated
                with Horizontal(classes="grid-2 form-row"):
                    with Vertical():
                        yield Label("Principal executive offices in")
                        yield Select(
                            [("View all", "")] + [(s, s) for s in US_STATES],
                            id="sel-exec-office",
                            value="",
                        )
                    with Vertical():
                        yield Label("Incorporated in")
                        yield Select(
                            [("View all", "")] + [(s, s) for s in US_STATES],
                            id="sel-incorporated",
                            value="",
                        )

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
                yield Button("▶  Start Search", id="start-search-btn", variant="success")



