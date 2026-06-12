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
        width: 80;
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
                yield Static("Crawler Configuration", classes="section-header")

                with Vertical(classes="config-row"):
                    yield Label("Result limit")
                    yield Input(str(Config.CRAWLER_GLOBAL_LIMIT), id="cfg-global-limit", validators=[Number(minimum=-1)])

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
                    yield Label("Persona prompt")
                    yield Input(Config.OLLAMA_PERSONA, id="cfg-persona-prompt")

                with Vertical(classes="config-row"):
                    yield Static("Experiment Versioning")
                    yield Label("Preprocessing Version")
                    yield Input(Config.PREPROCESSING_VERSION, id="cfg-preprocessing-version")

                    yield Label("Classification Version")
                    yield Input(Config.CLASSIFICATION_VERSION, id="cfg-classification-version")

                with Vertical(classes="config-row"):
                    yield Static("Class")
                    yield Input("", id="cfg-prompt-class")
                    yield Static("Prompt")
                    yield Input("", id="cfg-prompt-prompt")
                    yield Button("Add Class with Prompt", id="cfg-prompt-confirm", variant="success")
                    yield DataTable(id="cfg-prompt-table", cursor_type="row", zebra_stripes=True)
                    
                with Vertical(classes="config-row"):
                    yield Static("Database definition")
                    yield Static("Column Name")
                    yield Input("", id="cfg-table-col-name")
                    yield Static("Column Datatype")
                    yield Select(
                        [("Boolean", "boolean"), ("Integer", "integer")],
                        id="cfg-table-col-datatype",
                        value="boolean",
                    ) 
                    yield Button("Add column to database", id="cfg-table-confirm", variant="success")
                    
                    yield DataTable(id="cfg-table-table", cursor_type="row", zebra_stripes=True)

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

        #self.model.update_config()

        self.dismiss(True)

    @on(Button.Pressed, "#cfg-prompt-confirm")
    def add_prompts(self):
        class_text: str = self.query_one("#cfg-prompt-class", Input).value.strip()
        prompt_text: str = self.query_one("#cfg-prompt-prompt", Input).value.strip()

        prompt_data: PromptData = PromptData(prompt_class=class_text,
                                             prompt=prompt_text)

        self.model.add_prompt(prompt_data)

        self._refresh_prompt_table()

    @on(Button.Pressed, "#cfg-table-confirm")
    def add_column(self):
        col_name: str = self.query_one("#cfg-table-col-name", Input).value.strip()
        datatype: str = self.query_one("#cfg-table-col-datatype", Select).value.strip()

        prompt_data: TableData = TableData(column_name=col_name,
                                           datatype=datatype)

        self.model.add_column(prompt_data)

        self._refresh_table_table()


    def _refresh_table_table(self):
        table: DataTable = self.query_one("#cfg-table-table", DataTable)
        table.clear()

        for c in self.model.columns:
            column_name = getattr(c, "column_name", None)
            datatype = getattr(c, "datatype", None)
            if column_name and datatype:
                table.add_row(c.column_name, c.datatype)


    def _refresh_prompt_table(self):
        table: DataTable = self.query_one("#cfg-prompt-table", DataTable)
        table.clear()

        for p in self.model.prompts:
            class_text = getattr(p, "prompt_class", None)
            prompt_text = getattr(p, "prompt", None)
            if class_text and prompt_text:
                table.add_row(p.prompt_class, p.prompt)

    def on_mount(self) -> None:
        table: DataTable = self.query_one("#cfg-prompt-table", DataTable)
        table.add_columns("Class", "Prompt")
        self.model.load_prompts()
        self._refresh_prompt_table()

        table: DataTable = self.query_one("#cfg-table-table", DataTable)
        table.add_columns("Column Name", "Datatype")
        self.model.load_columns()
        self._refresh_table_table()

    @on(Button.Pressed, "#cfg-cancel")
    def cancel(self) -> None:
        self.dismiss(False)
