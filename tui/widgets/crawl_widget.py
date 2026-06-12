from __future__ import annotations
import logging
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.worker import Worker, WorkerState
from textual.widgets import Button, Static
from models.crawl_model import CrawlModel
from models.query_model import QueryModel


class CrawlWidget(Container):
    def __init__(self):
        super().__init__()
        self.model = CrawlModel()
        self._crawl_worker: Worker | None = None  # ← track the worker

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield Static("Crawl", classes="section-header")
                yield Button("Start Crawl Process", id="btn-start-crawl")
                yield Button("Stop Crawl Process", id="btn-stop-crawl")

    @on(Button.Pressed, "#btn-start-crawl")
    async def start_crawl(self) -> None:
        self._crawl_worker = self.run_worker(
            lambda: self.model.start_crawl(),
            thread=True
        )
        # ← removed await worker.wait(), event loop stays free

    @on(Worker.StateChanged)
    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker != self._crawl_worker:
            return  # ← ignore workers from other widgets
        if event.state == WorkerState.SUCCESS:
            self.app.notify("Crawl process finished", title="Complete")
        elif event.state == WorkerState.ERROR:
            self.app.notify("Crawl failed", title="Error", severity="error")
        elif event.state == WorkerState.CANCELLED:
            self.app.notify("Crawl stopped", title="Stopped")

    @on(Button.Pressed, "#btn-stop-crawl")
    async def stop_crawl(self) -> None:
        self.model.stop_crawl()  # ← signal your package to stop gracefully
        if self._crawl_worker:
            # consider SUCCESS, ERROR, and CANCELLED as terminal states
            terminal_states = (WorkerState.SUCCESS, WorkerState.ERROR, WorkerState.CANCELLED)
            if self._crawl_worker.state not in terminal_states:
                self._crawl_worker.cancel()  # ← clean up the Textual worker
        self.app.notify("Crawl stop requested", title="Requested")