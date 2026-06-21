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

from nps_crawling.config import Config
from data_package.config_data import ConfigData
from data_package.prompt_data import PromptData
from models.config_model import ConfigModel
from data_package.table_data import TableData

class ConfigScreen(ModalScreen):
    DEFAULT_CSS = """
    ConfigScreen {
        align: center middle;
    }
    ConfigScreen > Container {
        width: 75%;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 0 1;
    }
    ConfigScreen .dialog-title {
        background: $primary;
        color: $text;
        text-align: center;
        padding: 0 1;
        height: 3;
        content-align: center middle;
    }
    ConfigScreen .section-header {
        color: $accent;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }
    ConfigScreen .config-row {
        height: auto;
        margin-bottom: 1;
    }
    ConfigScreen .config-row Label {
        margin-bottom: 0;
    }
    ConfigScreen .config-row Input,
    ConfigScreen .config-row Select {
        width: 100%;
    }
    ConfigScreen .switch-row {
        height: 3;
        layout: horizontal;
        align: left middle;
    }
    ConfigScreen .switch-row Label {
        width: 1fr;
        content-align: left middle;
    }
    ConfigScreen .dialog-footer {
        height: 3;
        layout: horizontal;
        align: right middle;
        margin-top: 1;
        margin-bottom: 1;
    }
    ConfigScreen .dialog-footer Button {
        margin-left: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.model = ConfigModel()

    def compose(self) -> ComposeResult: 
        with Container():
            yield Static("Configuration", classes="dialog-title")
            with ScrollableContainer():
                yield Static("General configuration", classes="section-header")    
                with Vertical(classes="config-row"):
                    yield Label("Universal Mode")
                    yield Switch(False, id="cfg-universal-mode")

                with Vertical(classes="config-row"):
                    yield Label("Log Level")
                    yield Select(
                        [("DEBUG", "debug"), ("INFO", "info"), ("WARNING", "warning"), ("ERROR", "error")],
                        id="cfg-log-level",
                        value="info",
                    ) 

                yield Static("Crawler Configuration", classes="section-header")

                with Vertical(classes="config-row"):
                    yield Label("Result limit")
                    yield Input(str(Config.CRAWLER_GLOBAL_LIMIT), id="cfg-global-limit", validators=[Number(minimum=-1)])

                with Vertical(classes="config-row"):
                    yield Label("Recovery attempts")
                    yield Input("10", id="cfg-recovery-attempts", validators=[Number(minimum=0)])
                
                with Vertical(classes="config-row"):
                    yield Label("Recovery timeout (s)")
                    yield Input("5", id="cfg-recovery-timeout", validators=[Number(minimum=0)])

                with Horizontal(classes="switch-row"):
                    yield Label("Dry run")
                    yield Switch(False, id="cfg-dry-run") # TODO: Crawler Dry Run

                with Vertical(classes="config-row"):
                    yield Label("Delay between requests (ms)")
                    yield Input("100", id="cfg-delay", validators=[Number(minimum=0)])

                with Horizontal(classes="switch-row"):
                    yield Label("Stats dump")
                    yield Switch(False, id="cfg-stats-dump") # TODO: Crawler Stats Dump

                yield Static("Database Configuration", classes="section-header")

                with Vertical(classes="config-row"):
                    yield Label("Table name")
                    yield Input(Config.DATABASE_TABLE_NAME, id="cfg-table-name")

                with Vertical(classes="config-row"):
                    yield Label("Connection string")
                    yield Input(Config.LOCAL_DB_CONNECTION, id="cfg-conn-string")

                with Horizontal(classes="switch-row"):
                    yield Label("Local mode")
                    yield Switch(Config.LOCAL_MODE, id="cfg-local-mode")

                yield Static("Preprocessing Configuration", classes="section-header")

                with Vertical(classes="config-row"):
                    yield Label("Keyword list (comma-separated)")
                    yield Input(
                        ", ".join(Config.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR)
                        if Config.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR
                        else "",
                        id="cfg-keyword-list",
                    )

                with Vertical(classes="config-row"):
                    yield Label("Keyword exclude list (comma-separated)")
                    yield Input(
                        ", ".join(Config.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR)
                        if Config.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR
                        else "",
                        id="cfg-keyword-exclude",
                    )

                with Vertical(classes="config-row"):
                    yield Label("Threshold value")
                    yield Input(
                        ", ".join(str(i) for i in Config.THRESHOLD_KEYWORD_SCOPE)
                        if Config.THRESHOLD_KEYWORD_SCOPE
                        else "",
                        id="cfg-threshold",
                        validators=[Number(minimum=0, maximum=1)],
                    )

                yield Static("Model Configuration", classes="section-header")

                with Vertical(classes="config-row"):
                    yield Label("Model selection")
                    yield Select(
                        [("SVM", "svm"), ("LLM", "llm"), ("REGEX", "REGEX")],
                        id="cfg-model-select",
                        value="svm",
                    )

                with Vertical(classes="config-row"):
                    yield Static("Experiment Versioning")
                    yield Label("Preprocessing Version")
                    yield Input(Config.PREPROCESSING_VERSION, id="cfg-preprocessing-version")

                    yield Label("Classification Version")
                    yield Input(Config.CLASSIFICATION_VERSION, id="cfg-classification-version")

            with Horizontal(classes="dialog-footer"):
                yield Button("Save", variant="primary", id="cfg-save")
                yield Button("Cancel", variant="default", id="cfg-cancel")

    @on(Button.Pressed, "#cfg-save")
    def save(self) -> None:
        self.app.notify("Configuration saved.", severity="information")

        global_limit_value = int(self.query_one("#cfg-global-limit", Input).value)
        # TODO
        #settings = ConfigData(
        #    crawler_limit=global_limit_value,
#
        #)

        self.model.update_config(ConfigData())
        
        self.dismiss(True)

    def on_mount(self) -> None:
        pass

    @on(Button.Pressed, "#cfg-cancel")
    def cancel(self) -> None:
        self.dismiss(False)
