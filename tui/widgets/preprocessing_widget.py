from __future__ import annotations

import asyncio
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

from models.preprocessing_model import PreprocessingModel

class PreprocessingWidget(Container):

    elapsed: reactive[int] = reactive(0)

    def __init__(self):
        super().__init__()
        self.model = PreprocessingModel()
        self._preprocessing_worker: Worker | None = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield Static("Preprocessing", classes="panel-title")
                with Horizontal():
                    yield Button("Configure Preprocess", id="btn-configure-preprocessing")
                    yield Button("Start Preprocessing", id="btn-start-preprocessing")
                    yield Button("Stop Preprocessing", id="btn-stop-preprocessing")
                    yield Label("", id="preprocessing-timer")

    @on(Button.Pressed, "#btn-configure-preprocessing")
    def open_preprocess_config(self) -> None:
        from screens.preprocess_config_screen import PreprocessConfigScreen
        self.app.push_screen(PreprocessConfigScreen())


    def watch_elapsed(self, value: int) -> None:
        hours, remainder = divmod(value, 3600)
        mins, secs = divmod(remainder, 60)
        self.query_one("#preprocessing-timer", Label).update(f"{hours:02d}:{mins:02d}:{secs:02d}")
        
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
        if event.worker != self._preprocessing_worker:
            return  
        if event.state == WorkerState.SUCCESS:
            self.app.notify("Preprocessing finished", title="Complete")
        elif event.state == WorkerState.ERROR:
            self.app.notify("Preprocessing failed", title="Error", severity="error")
        elif event.state == WorkerState.CANCELLED:
            self.app.notify("Preprocessing stopped", title="Stopped")
        else:
            return
        
        self._stop_timer()

    @on(Button.Pressed, "#btn-start-preprocessing")
    async def start_preprocessing(self):
        self._start_timer()

        self._preprocessing_worker = self.run_worker(
            lambda: self.model.run_preprocessing(),
            thread=True,
        )

