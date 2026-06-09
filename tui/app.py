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
from widgets.crawl_widget import CrawlWidget
from widgets.preprocessing_widget import PreprocessingWidget
from widgets.classification_widget import ClassificationWidget
from widgets.result_widget import ResultWidget
from widgets.database_widget import DatabaseWidget
from screens.filing_types_screen import FilingTypesScreen

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
        
        self.query_widget = QueryWidget()
        self.crawl_widget = CrawlWidget()
        self.preprocessing_widget = PreprocessingWidget()
        self.classification_widget = ClassificationWidget()
        self.result_widget = ResultWidget(id="result-widget")
        self.database_widget = DatabaseWidget()

        self.widget_map: dict = {
            "nav-query": self.query_widget,
            "nav-crawl": self.crawl_widget,
            "nav-preprocessing": self.preprocessing_widget,
            "nav-classification": self.classification_widget,
            "nav-results": self.result_widget,
            "nav-database": self.database_widget,
        }

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="outer-layout"):
            with Container():
                yield NavigationWidget()
            with Horizontal(id="main-layout"):
                with Container(id="page-container"):
                    for v in self.widget_map.values():
                        yield v
        yield Footer()

    @on(Button.Pressed, "#btn-config")
    def _on_button_config(self):
        self.push_screen(ConfigScreen())


    @on(NavigationWidget.Navigate)
    async def handle_navigation(
        self,
        event: NavigationWidget.Navigate,
    ) -> None:
        for v in self.widget_map.values():
            v.display = False
        self.widget_map[event.page].display = True

        
    @on(Button.Pressed, "#btn-filing-types")
    def action_open_filing_types(self) -> None:
        self.push_screen(
            FilingTypesScreen([]),
        )

if __name__ == "__main__":
    CrawlerTuiApp().run()