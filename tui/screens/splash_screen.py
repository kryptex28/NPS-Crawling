from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.app import ComposeResult
from textual import on
import pyfiglet

class SplashScreen(ModalScreen):
    CSS_PATH = "splash_screen.tcss"

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