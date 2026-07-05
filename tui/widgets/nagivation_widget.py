from __future__ import annotations

from dataclasses import dataclass

from textual.containers import Horizontal
from textual.widgets import (
    Button,
)
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
            """Initialize the NavigationWidget."""
            self.page = page
            super().__init__()

    def compose(self):
        """Compose the navigation sidebar buttons."""
        with Horizontal(id="navigation"):
            for item in self.NAVIGATION_ITEMS:
                yield Button(f"{item.label}", id=item.id)
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle navigation button press and post a Navigate event."""
        event.stop()
        self.post_message(self.Navigate(event.button.id))