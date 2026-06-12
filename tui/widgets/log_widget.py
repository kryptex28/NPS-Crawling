import logging
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import (
    Static,
    RichLog
)

LEVEL_COLORS = {
    logging.DEBUG: "dim white",
    logging.INFO: "cyan",
    logging.WARNING: "yellow",
    logging.ERROR: "bold red",
    logging.CRITICAL: "bold white on red"
}

class TextualLogHandler(logging.Handler):
    def __init__(self, widget: RichLog) -> None:
        super().__init__()
        self._widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            color = LEVEL_COLORS.get(record.levelno, "white")

            self._widget.app.call_from_thread(
                self._widget.write, f"[{color}]{msg}[/{color}]"
            )

        except Exception as e:
            self.handleError(record=record)

class LogWidget(Vertical):
    DEFAULT_CSS = """
    LogWidget {
        height: 100%;
        border: solid $primary-darken-2;
    }
    LogWidget Static {
        text-style: bold;
        color: $accent;
        padding: 0 1;
    }
    LogWidget RichLog {
        height: 1fr;
        padding: 0 1;
        scrollbar-size: 1 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("--- Logs ---")
        yield RichLog(highlight=True, markup=True, wrap=True, id="log-output")