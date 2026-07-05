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

from models.database_model import DatabaseModel

class DatabaseWidget(Container):

    def __init__(self):
        super().__init__()
        self.model = DatabaseModel()

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield Static("Database", classes="panel-title")
                with Horizontal():
                    yield Button("Show Database", id="btn-show-database")
                    yield Button("Clear Database", id="btn-clear-database")
                yield DataTable(id="db-table")

    @on(Button.Pressed, "#btn-show-database")
    async def load(self) -> None:
        table = self.query_one("#db-table", DataTable)

        # create a Thread to fetch all database entries to avoid TUI freeze
        worker = self.run_worker(
            lambda: self.model.get_all_filings(),
            thread=True,
        )

        rows = await worker.wait()
        table.clear()
        if not rows:
            return
        
        columns = list(rows[0].keys())

        table.add_columns(*columns)

        for row in rows:
            table.add_row(*(str(row.get(col, "")) for col in columns))

    @on(Button.Pressed, "#btn-clear-database")
    def on_database_clear(self):
        database = self.query_one("#db-table", DataTable)
        database.clear()