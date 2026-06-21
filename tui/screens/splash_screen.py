from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.app import ComposeResult
from textual import on
import pyfiglet

class SplashScreen(ModalScreen):
    CSS = """
    SplashScreen {
        align: center middle;
        background: $background;
    }

    #splash-box {
        width: auto;
        height: auto;
        padding: 2 4;
        border: round $accent;
        align: center middle;
    }

    #splash-logo {
        text-align: center;
        color: $accent;
        text-style: bold;
        width: auto;
        margin-bottom: 1;
    }

    #splash-subtitle {
        text-align: center;
        color: $text-muted;
        width: auto;
        margin-bottom: 2;
    }

    #splash-continue {
        width: auto;
        min-width: 20;
        height: 3;
        align-horizontal: center;
    }
    """
    LOGO = pyfiglet.figlet_format("SEC Crawler\nTHU")

    def compose(self) -> ComposeResult:
        yield Container(
            Static(self.LOGO, id="splash-logo"),
            Button("Continue", id="splash-continue"),
            id="splash-box"
        )

    def on_mount(self) -> None:
        self._timer = self.set_timer(5, self._dismiss)

    @on(Button.Pressed, "#splash-continue")
    def _dismiss(self) -> None:
        self._timer.stop()
        self.dismiss()