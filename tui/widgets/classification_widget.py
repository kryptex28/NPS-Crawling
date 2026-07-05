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


from models.classification_model import ClassificationModel

class ClassificationWidget(Container):

    elapsed: reactive[int] = reactive(0)

    def __init__(self):
        """Initialize the ClassificationWidget."""
        super().__init__()
        self.model = ClassificationModel()
        self._classification_worker: Worker | None = None

    def compose(self) -> ComposeResult:
        """Compose the classification interface layout, buttons, and progress status."""
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
        """Open the classification configuration settings screen."""
        from screens.classification_config_screen import ClassificationConfigScreen
        self.app.push_screen(ClassificationConfigScreen())


    def watch_elapsed(self, value: int) -> None:
        """Update the elapsed timer label in the UI."""
        hours, remainder = divmod(value, 3600)
        mins, secs = divmod(remainder, 60)
        self.query_one("#classification-timer", Label).update(f"{hours:02d}:{mins:02d}:{secs:02d}")
        
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
        """Start the classification pipeline in a background worker thread."""
        self._start_timer()

        self._classification_worker = self.run_worker(
            lambda: self.model.start_classification(),
            thread=True
        )
