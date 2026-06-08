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

class ConfigScreen(ModalScreen):
    def compose(self) -> ComposeResult: 
        with Container():
            yield Static("⚙  Configuration", classes="dialog-title")
            with ScrollableContainer():
                yield Static("Crawler Configuration", classes="section-header")

                with Vertical(classes="config-row"):
                    yield Label("Result limit")
                    yield Input("1000", id="cfg-global-limit", validators=[Number(minimum=1)])

                with Horizontal(classes="switch-row"):
                    yield Label("Dry run")
                    yield Switch(False, id="cfg-dry-run")

                with Vertical(classes="config-row"):
                    yield Label("Delay between requests (ms)")
                    yield Input("100", id="cfg-delay", validators=[Number(minimum=0)])

                with Vertical(classes="config-row"):
                    yield Label("User agent")
                    yield Input(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        id="cfg-user-agent",
                    )

                with Horizontal(classes="switch-row"):
                    yield Label("Stats dump")
                    yield Switch(False, id="cfg-stats-dump")

                yield Static("Database Configuration", classes="section-header")

                with Vertical(classes="config-row"):
                    yield Label("Table name")
                    yield Input("nps_filings_table", id="cfg-table-name")

                with Vertical(classes="config-row"):
                    yield Label("Connection string")
                    yield Input("crawler:crawler@localhost:5432/crawler", id="cfg-conn-string")

                with Horizontal(classes="switch-row"):
                    yield Label("Local mode")
                    yield Switch(False, id="cfg-local-mode")

                yield Static("Preprocessing Configuration", classes="section-header")

                with Vertical(classes="config-row"):
                    yield Label("Keyword list (comma-separated)")
                    yield Input("", id="cfg-keyword-list")

                with Vertical(classes="config-row"):
                    yield Label("Keyword exclude list (comma-separated)")
                    yield Input("", id="cfg-keyword-exclude")

                with Vertical(classes="config-row"):
                    yield Label("Threshold value")
                    yield Input("0.5", id="cfg-threshold", validators=[Number(minimum=0, maximum=1)])

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
                    yield Input("", id="cfg-persona-prompt")

            with Horizontal(classes="dialog-footer"):
                yield Button("Save", variant="primary", id="cfg-save")
                yield Button("Cancel", variant="default", id="cfg-cancel")

    @on(Button.Pressed, "#cfg-save")
    def save(self) -> None:
        self.app.notify("Configuration saved.", severity="information")
        self.dismiss(True)

    @on(Button.Pressed, "#cfg-cancel")
    def cancel(self) -> None:
        self.dismiss(False)
