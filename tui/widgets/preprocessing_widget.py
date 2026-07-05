from __future__ import annotations


from textual.reactive import reactive
from textual.worker import Worker, WorkerState
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Button,
    Label,
    Static,
)


from models.preprocessing_model import PreprocessingModel

class PreprocessingWidget(Container):

    elapsed: reactive[int] = reactive(0)

    def __init__(self):
        """Initialize the PreprocessingWidget."""
        super().__init__()
        self.model = PreprocessingModel()
        self._preprocessing_worker: Worker | None = None

    def compose(self) -> ComposeResult:
        """Compose the preprocessing interface layout, buttons, and progress status."""
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
        """Open the preprocessing configuration settings screen."""
        from screens.preprocess_config_screen import PreprocessConfigScreen
        self.app.push_screen(PreprocessConfigScreen())


    def watch_elapsed(self, value: int) -> None:
        """Update the elapsed timer label in the UI."""
        hours, remainder = divmod(value, 3600)
        mins, secs = divmod(remainder, 60)
        self.query_one("#preprocessing-timer", Label).update(f"{hours:02d}:{mins:02d}:{secs:02d}")
        
    def _start_timer(self) -> None:
        """Start the elapsed timer."""
        self.elapsed = 0
        self._timer = self.set_interval(1, self._tick)

    def _stop_timer(self) -> None:
        """Stop the elapsed timer."""
        if self._timer:
            self._timer.stop()
            self._timer = None

    def _tick(self) -> None:
        """Increment the elapsed timer value."""
        self.elapsed += 1

    @on(Worker.StateChanged)
    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle pipeline worker status changes, enabling/disabling UI buttons."""
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
        """Start the preprocessing pipeline in a background worker thread."""
        self._start_timer()

        self._preprocessing_worker = self.run_worker(
            lambda: self.model.run_preprocessing(),
            thread=True,
        )

