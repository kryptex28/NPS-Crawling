from __future__ import annotations

import asyncio
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

from constants import FILING_CATEGORIES
from constants import US_STATES

from models.preprocessing_model import PreprocessingModel

class PreprocessingWidget(Container):

    def __init__(self):
        super().__init__()
        self.model = PreprocessingModel()

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield Static("Preprocessing", classes="section-header")

                yield Button("Start Preprocessing", id="btn-start-preprocessing")
                yield Button("Stop Preprocessing", id="btn-stop-preprocessing")


    @on(Button.Pressed, "#btn-start-preprocessing")
    async def start_preprocessing(self):
        worker = self.run_worker(
            lambda: self.model.run_preprocessing(),
            thread=True,
        )

        self.app.notify("Preprocessing started", title="Running")
        button = self.query_one("#btn-start-preprocessing")
        button.disabled = True

        await worker.wait()
        self.app.notify("Preprocessing finished", title="Complete")
        button.disabled = False
