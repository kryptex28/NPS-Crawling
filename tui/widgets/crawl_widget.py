from __future__ import annotations
import logging
from textual import on
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.worker import Worker, WorkerState
from textual.widgets import Button, Static, Label
from models.crawl_model import CrawlModel
from models.query_model import QueryModel


class CrawlWidget(Container):

    elapsed: reactive[int] = reactive(0)

    def __init__(self):
        super().__init__()
        self.model = CrawlModel()
        self._crawl_worker: Worker | None = None  # ← track the worker
        self._timer = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield Static("Crawl", classes="section-header")
                with Horizontal():
                    yield Button("Configure Crawl", id="btn-configure-crawl")
                    yield Button("Start Crawl Process", id="btn-start-crawl")
                    yield Button("Stop Crawl Process", id="btn-stop-crawl")
                    yield Label("", id="crawl-timer")

    @on(Button.Pressed, "#btn-configure-crawl")
    def open_crawl_config(self) -> None:
        from screens.crawl_config_screen import CrawlConfigScreen
        self.app.push_screen(CrawlConfigScreen())

    @on(Button.Pressed, "#btn-start-crawl")
    async def start_crawl(self) -> None:
        self._start_timer()

        self._crawl_worker = self.run_worker(
            lambda: self.model.start_crawl(),
            thread=True
        )

    def watch_elapsed(self, value: int) -> None:
        hours, remainder = divmod(value, 3600)
        mins, secs = divmod(remainder, 60)
        self.query_one("#crawl-timer", Label).update(f"{hours:02d}:{mins:02d}:{secs:02d}")
        
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
        if event.worker != self._crawl_worker:
            return  
        if event.state == WorkerState.SUCCESS:
            self.app.notify("Crawl process finished", title="Complete")
        elif event.state == WorkerState.ERROR:
            self.app.notify("Crawl failed", title="Error", severity="error")
        elif event.state == WorkerState.CANCELLED:
            self.app.notify("Crawl stopped", title="Stopped")
        else:
            return
        
        self._stop_timer()

    @on(Button.Pressed, "#btn-stop-crawl")
    async def stop_crawl(self) -> None:
        self.model.stop_crawl() 
        self._stop_timer()
        if self._crawl_worker:
            terminal_states = (WorkerState.SUCCESS, WorkerState.ERROR, WorkerState.CANCELLED)
            if self._crawl_worker.state not in terminal_states:
                self._crawl_worker.cancel() 
            self._stop_timer()
        self.app.notify("Crawl stop requested", title="Requested")