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

from models.crawl_model import CrawlModel

class CrawlWidget(Container):

    def __init__(self):
        super().__init__()
        self.model = CrawlModel()

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield Static("Crawl", classes="section-header")

                yield Button("Start Crawl Process", id="btn-start-crawl")
                yield Button("Stop Crawl Process", id="btn-stop-crawl")

    @on(Button.Pressed, "#btn-start-crawl")
    async def start_crawl(self) -> None:
        ids: list = ["123"]

        worker = self.run_worker(
            lambda: self.model.start_crawl(ids=ids),
            thread=True
        )

        await worker.wait()
        self.app.notify("Crawl process finished", title="Complete")

    @on(Button.Pressed, "#btn-stop-crawl")
    async def stop_crawl(self) -> None:
        worker = self.run_worker(
            lambda: self.model.stop_crawl(),
            thread=True
        )
        self.app.notify("Crawl process stop requested", title="Requested")
        await worker.wait()