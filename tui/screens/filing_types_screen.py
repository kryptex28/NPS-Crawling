from __future__ import annotations


from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Static,
)
from textual.widgets import SelectionList
from textual.widgets.selection_list import Selection

from constants import FILING_TYPES

class FilingTypesScreen(ModalScreen):
    CSS_PATH = "filing_types_screen.tcss"

    def __init__(self, selected: list[str] | None = None) -> None:
        """Initialize the FilingTypesScreen."""
        super().__init__()
        self._pre_selected = set(selected or [])

    
    def compose(self) -> ComposeResult:
        """Compose the filing types selection dialog layout."""
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
        """Select all filing types in the list."""
        sl = self.query_one("#filing-types-list", SelectionList)
        sl.select_all()

    @on(Button.Pressed, "#pick-none")
    def select_none(self) -> None:
        """Deselect all filing types in the list."""
        sl = self.query_one("#filing-types-list", SelectionList)
        sl.deselect_all()

    @on(Button.Pressed, "#pick-confirm")
    def confirm(self) -> None:
        """Dismiss the screen, returning the list of selected filing types."""
        sl = self.query_one("#filing-types-list", SelectionList)

        self.dismiss(list(sl.selected))

    @on(Button.Pressed, "#pick-cancel")
    def cancel(self) -> None:
        """Dismiss the screen without returning any selection."""
        self.dismiss(None)