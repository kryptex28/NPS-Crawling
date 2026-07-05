from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from textual.reactive import reactive
from textual.worker import Worker, WorkerState
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

    elapsed: reactive[int] = reactive(0)

    def __init__(self):
        super().__init__()
        self.model = ClassificationModel()
        self._classification_worker: Worker | None = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield Static("Classification", classes="panel-title")
                with Horizontal():
                    yield Button("Configure Classification", id="btn-configure-classification")
                    yield Button("Start Classification", id="btn-start-classification")
                    yield Button("Stop Classification", id="btn-stop-classification")
                    yield Label("", id="classification-timer")

    @on(Button.Pressed, "#btn-configure-classification")
    def open_classification_config(self) -> None:
        from screens.classification_config_screen import ClassificationConfigScreen
        self.app.push_screen(ClassificationConfigScreen())


    def watch_elapsed(self, value: int) -> None:
        hours, remainder = divmod(value, 3600)
        mins, secs = divmod(remainder, 60)
        self.query_one("#classification-timer", Label).update(f"{hours:02d}:{mins:02d}:{secs:02d}")
        
    def _start_timer(self) -> None:
        self.elapsed = 0
        self._timer = self.set_interval(1, self._tick)

    def _stop_timer(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None

    def _tick(self) -> None:
        self.elapsed += 1

    @on(Worker.StateChanged)
    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker != self._classification_worker:
            return  
        if event.state == WorkerState.SUCCESS:
            self.app.notify("Classification process finished", title="Complete")
        elif event.state == WorkerState.ERROR:
            self.app.notify("Classification failed", title="Error", severity="error")
        elif event.state == WorkerState.CANCELLED:
            self.app.notify("Classification stopped", title="Stopped")
        else:
            return
        
        self._stop_timer()

    @on(Button.Pressed, "#btn-start-classification")
    async def start_classification(self) -> None:
        self._start_timer()

        self._classification_worker = self.run_worker(
            lambda: self.model.start_classification(),
            thread=True
        )
