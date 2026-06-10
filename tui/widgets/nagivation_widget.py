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
from textual.message import Message
from textual.widgets import Button
from textual.widget import Widget

class NavigationWidget(Widget):

    CSS: str = """
    #navigation {
        height: 3;
        padding-bottom: 1;
    }

    """

    class Navigate(Message):
        def __init__(self, page: str) -> None:
            self.page = page
            super().__init__()

    def compose(self):
        with Horizontal(id="navigation"):
            yield Button("Query", id="nav-query")
            yield Button("Crawl", id="nav-crawl")
            yield Button("Preprocessing", id="nav-preprocessing")
            yield Button("Classification", id="nav-classification")
            yield Button("Results", id="nav-results")
            yield Button("Database", id="nav-database")
            yield Button("Settings", id="nav-settings")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        assert button_id is not None

        self.post_message(self.Navigate(button_id))