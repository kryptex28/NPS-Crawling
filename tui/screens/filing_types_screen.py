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

from constants import FILING_TYPES

class FilingTypesScreen(ModalScreen):
    DEFAULT_CSS = """
        FilingTypesScreen {
            align: center middle;
        }
        FilingTypesScreen > Container {
            width: 30%;
            height: 60%;
            background: $surface;
            border: thick $primary;
            padding: 0 1;
        }
        FilingTypesScreen .picker-title {
            background: $primary;
            color: $text;
            text-align: center;
            padding: 0 1;
            height: 3;
            content-align: center middle;
        }
        FilingTypesScreen SelectionList {
            height: 1fr;
            border: none;
        }
        FilingTypesScreen .picker-footer {
            height: 3;
            layout: horizontal;
            align: right middle;
            margin: 1 0;
        }
        FilingTypesScreen .picker-footer Button {
            margin-left: 1;
        }
        """

    def __init__(self, selected: list[str]) -> None:
        super().__init__()
        self._pre_selected = set(selected)

    def compose(self) -> ComposeResult:
        with Container():
            yield Static("Select Filing Types", classes="picker-title")
            yield SelectionList(
                *[
                    Selection(ft, ft, initial_state=(ft in self._pre_selected))
                    for ft in FILING_TYPES
                ],
                id="filing-types-list",
            )
            with Horizontal(classes="picker-footer"):
                yield Button("Select All", variant="default", id="pick-all")
                yield Button("Clear All", variant="default", id="pick-none")
                yield Button("Confirm", variant="primary", id="pick-confirm")
                yield Button("Cancel", variant="default", id="pick-cancel")

    @on(Button.Pressed, "#pick-all")
    def select_all(self) -> None:
        sl = self.query_one("#filing-types-list", SelectionList)
        sl.select_all()

    @on(Button.Pressed, "#pick-none")
    def select_none(self) -> None:
        sl = self.query_one("#filing-types-list", SelectionList)
        sl.deselect_all()

    @on(Button.Pressed, "#pick-confirm")
    def confirm(self) -> None:
        sl = self.query_one("#filing-types-list", SelectionList)
        self.dismiss(list(sl.selected))

    @on(Button.Pressed, "#pick-cancel")
    def cancel(self) -> None:
        self.dismiss(None)