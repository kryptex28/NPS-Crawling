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

from constants import FILING_CATEGORIES
from constants import US_STATES

from models.classification_model import ClassificationModel

class ClassificationWidget(Container):

    def __init__(self):
        super().__init__()
        self.model = ClassificationModel()

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield Static("Classification", classes="section-header")

                yield Button("Start Classification", id="btn-start-classification")
                yield Button("Stop Classification", id="btn-stop-classification")

    @on(Button.Pressed, "#btn-start-classification")
    async def start_classification(self) -> None:

        worker = self.run_worker(
            lambda: self.model.start_classification(),
            thread=True
        )
        self.app.notify("Classification process started", title="Started")
        
        button = self.query_one("#btn-start-classification")
        button.disabled = True

        await worker.wait()
        self.app.notify("Classification process finished", title="Complete")
        button.disabled = False
