from __future__ import annotations

import logging
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
    RichLog
)
from textual.widgets import SelectionList
from textual.widgets.selection_list import Selection

from widgets.project_widget import ProjectWidget
from widgets.nagivation_widget import NavigationWidget
from widgets.query_widget import QueryWidget
from widgets.crawl_widget import CrawlWidget
from widgets.preprocessing_widget import PreprocessingWidget
from widgets.classification_widget import ClassificationWidget
from widgets.result_widget import ResultWidget
from widgets.database_widget import DatabaseWidget
from screens.filing_types_screen import FilingTypesScreen
from widgets.log_widget import (
    LogWidget,
    TextualLogHandler
)

from screens.config_screen import ConfigScreen
from screens.splash_screen import SplashScreen
from screens.project_screen import ProjectScreen

from nps_crawling.db.db_adapter import DbAdapter
from models.project_model import ProjectModel


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

    CSS_PATH = "app.tcss"

    def __init__(self) -> None:
        super().__init__()
        
        self.query_widget = QueryWidget()
        self.crawl_widget = CrawlWidget()
        self.preprocessing_widget = PreprocessingWidget()
        self.classification_widget = ClassificationWidget()
        self.result_widget = ResultWidget(id="result-widget")
        self.database_widget = DatabaseWidget()
        self.project_widget = ProjectWidget()

        self.widget_map: dict = {
            "nav-project": self.project_widget,
            "nav-query": self.query_widget,
            "nav-crawl": self.crawl_widget,
            "nav-preprocessing": self.preprocessing_widget,
            "nav-classification": self.classification_widget,
            "nav-results": self.result_widget,
            "nav-database": self.database_widget,
        }

        for v in self.widget_map.values():
            v.display = False

        self.project_widget.display = True

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="outer-layout"):
            with Container(id="nav-container"):
                yield NavigationWidget()
            with Horizontal(id="main-layout"):
                with Container(id="page-container"):
                    for v in self.widget_map.values():
                        yield v
            with Container(classes="log-container"):
                yield LogWidget(id="log-panel")

        yield Footer()

    @on(Button.Pressed, "#btn-config")
    @on(Button.Pressed, "#nav-settings")
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

    def on_mount(self) -> None:
        self.push_screen(SplashScreen(), callback=self._on_splash_dismissed())

        rich_log = self.query_one("#log-output", RichLog)
        handler = TextualLogHandler(rich_log)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        ))

        pkg_logger = logging.getLogger("nps_crawling") 
        pkg_logger.setLevel(logging.INFO)
        pkg_logger.addHandler(handler)

    def _on_splash_dismissed(self):
        if not ProjectModel().is_project_active():
            self.push_screen(ProjectScreen())
        else:
            self.notify("Project loaded", 
                        title="Project",
                        timeout=5)

    @on(Button.Pressed, "#show-projects-btn")
    def show_projects_view(self):
        self.push_screen(ProjectScreen())

if __name__ == "__main__":
    CrawlerTuiApp().run()