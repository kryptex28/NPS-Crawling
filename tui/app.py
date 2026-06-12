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

from nps_crawling.db.db_adapter import DbAdapter



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

    CSS = """
    Screen {
        background: $background;
    }

    /* Reduce spacing between navigation bar and main content */
    #outer-layout {
        padding: 0;
        height: 20fr;        /* fills remaining space after Header/Footer */
    }

    #nav-container {
        width: 100%;
        height: 3;
        padding: 0;
        margin: 0;
    }

    /* ── Top layout ─────────────────────────────────────────────────── */
    #main-layout {
        layout: horizontal;
        height: 1fr;
    }
    #left-panel {
        width: 1fr;
        height: 1fr;
        overflow-y: auto;
        border-right: solid $primary-darken-2;
        padding: 0 1;
    }
    #right-panel {
        width: 55;
        height: 1fr;
        padding: 0 1;
    }

    /* ── Section headings ────────────────────────────────────────────── */
    .panel-title {
        text-style: bold;
        color: $accent;
        border-bottom: solid $primary-darken-2;
        padding: 0 0 1 0;
        margin-bottom: 1;
    }

    /* ── Form rows ───────────────────────────────────────────────────── */
    .form-row {
        height: auto;
        margin-bottom: 1;
    }
    .form-row Label {
        color: $text-muted;
        margin-bottom: 0;
    }
    .form-row Input,
    .form-row Select {
        width: 100%;
    }
    .grid-2 {
        layout: horizontal;
        height: auto;
    }
    .grid-2 > Vertical {
        height: auto;
    }
    .grid-2 > Vertical:last-child {
        height: auto;
    }
    .grid-2 Select {
        height: auto;
    }

    /* ── Date range ──────────────────────────────────────────────────── */
    #date-range-set {
        height: auto;
    }
    #date-range-set RadioButton {
        margin-right: 1;
    }
    #custom-dates {
        display: none;
        height: auto;
        layout: horizontal;
        margin-top: 1;
    }
    #custom-dates.visible {
        display: block;
    }

    /* ── Filing types badge ──────────────────────────────────────────── */
    #filing-types-badge {
        color: $text-muted;
        text-style: italic;
        height: 1;
        margin-top: 0;
    }

    /* ── Form actions ────────────────────────────────────────────────── */
    #form-actions {
        layout: horizontal;
        height: auto;
        margin-top: 2;
        margin-bottom: 1;
    }
    #form-actions Button {
        margin-right: 1;
    }

    /* ── Query list ──────────────────────────────────────────────────── */
    #query-toolbar {
        layout: horizontal;
        height: 3;
        align: left middle;
        margin-bottom: 1;
    }
    #query-toolbar Button {
        margin-right: 1;
        height: 3;
    }
    #query-table {
        height: 1fr;
    }
    #start-search-btn {
        margin-top: 1;
        width: 100%;
    }
    #right-panel-title {
        text-style: bold;
        color: $accent;
        border-bottom: solid $primary-darken-2;
        padding: 0 0 1 0;
        margin-bottom: 1;
    }

    /* ── Status bar ──────────────────────────────────────────────────── */
    #status-bar {
        height: 1;
        background: $primary-darken-3;
        color: $text-muted;
        padding: 0 1;
        dock: bottom;
    }
    """

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

        for v in self.widget_map.values():
            v.display = False

        self.query_widget.display = True

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
        rich_log = self.query_one("#log-output", RichLog)
        handler = TextualLogHandler(rich_log)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        ))

        # attach to your package's root logger so every sub-logger feeds in
        pkg_logger = logging.getLogger("nps_crawling") 
        pkg_logger.setLevel(logging.INFO)
        pkg_logger.addHandler(handler)


if __name__ == "__main__":
    CrawlerTuiApp().run()