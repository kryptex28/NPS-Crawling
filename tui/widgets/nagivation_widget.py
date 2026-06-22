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

from dataclasses import dataclass

@dataclass
class NavigationItem:
    id: str
    label: str


class NavigationWidget(Widget):

    CSS: str = """
#navigation {
    height: 3;
}
NavigationWidget {
    height: auto;
}
"""
    NAVIGATION_ITEMS: list[NavigationItem] = [
        NavigationItem("nav-project", "Project"),
        NavigationItem("nav-query", "Query"),
        NavigationItem("nav-crawl", "Crawl"),
        NavigationItem("nav-preprocessing", "Preprocessing"),
        NavigationItem("nav-classification", "Classification"),
        NavigationItem("nav-results", "Results"),
        NavigationItem("nav-database", "Database"),
    ]


    class Navigate(Message):
        def __init__(self, page: str) -> None:
            self.page = page
            super().__init__()

    def compose(self):
        with Horizontal(id="navigation"):
            for item in self.NAVIGATION_ITEMS:
                yield Button(f"{item.label}", id=item.id)
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.post_message(self.Navigate(event.button.id))