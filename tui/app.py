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

from widgets.nagivation_widget import NavigationWidget
from widgets.query_widget import QueryWidget
from widgets.preprocessing_widget import PreprocessingWidget

from screens.config_screen import ConfigScreen

class CrawlerTuiApp(App):

    TITLE = "EDGAR Search"
    SUB_TITLE = "THU"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("f1", "open_config", "Configuration"),
        Binding("f2", "open_filing_types", "Filing Types"),
        Binding("ctrl+r", "reset_form", "Reset form"),
    ]

    def __init__(self) -> None:
        super().__init__()
        
        self.query_widget = QueryWidget(id="query-widget")
        self.preprocessing_widget = PreprocessingWidget(id="preprocessing-widget")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="outer-layout"):
            with Container():
                yield NavigationWidget()
            with Horizontal(id="main-layout"):
                with Container(id="page-container"):
                    yield self.query_widget
                    yield self.preprocessing_widget
        yield Footer()

    @on(Button.Pressed, "#btn-config")
    def _on_button_config(self):
        self.push_screen(ConfigScreen())


    @on(NavigationWidget.Navigate)
    async def handle_navigation(
        self,
        event: NavigationWidget.Navigate,
    ) -> None:

        container = self.query_one("#page-container", Container)
        await container.remove_children()
        match event.page:
            case "nav-query":
                await container.mount(QueryWidget())

            case "nav-preprocessing":
                await container.mount(PreprocessingWidget())

if __name__ == "__main__":
    CrawlerTuiApp().run()