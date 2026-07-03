from __future__ import annotations

import logging
import json
import uuid
import subprocess
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from textual.reactive import reactive
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
    RichLog
)
from textual.widgets import SelectionList
from textual.widgets.selection_list import Selection

from widgets.project_widget import ProjectWidget
from widgets.nagivation_widget import NavigationWidget
from widgets.query_widget import QueryWidget
from widgets.crawl_widget import CrawlWidget
from widgets.preprocessing_widget import PreprocessingWidget
from widgets.classification_widget import ClassificationWidget
from widgets.result_widget import ResultWidget
from widgets.database_widget import DatabaseWidget
from screens.filing_types_screen import FilingTypesScreen
from widgets.log_widget import (
    LogWidget,
    TextualLogHandler
)

from screens.config_screen import ConfigScreen
from screens.splash_screen import SplashScreen
from screens.project_screen import ProjectScreen

from nps_crawling.config import Config
from nps_crawling.db.db_adapter import DbAdapter
from models.project_model import ProjectModel
from models.query_model import QueryModel


class CrawlerTuiApp(App):

    TITLE = "EDGAR Search"
    SUB_TITLE = "THU"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("f1", "open_config", "Configuration"),
        Binding("f2", "open_filing_types", "Filing Types"),
        Binding("ctrl+r", "reset_form", "Reset form"),
    ]

    CSS_PATH = "app.tcss"

    PAGES_WITHOUT_LOG = {"nav-project", "nav-database"}

    current_page: reactive[str] = reactive("nav-project", init=False)

    def __init__(self) -> None:
        super().__init__()

        WIDGET_CLASSES: dict = {
            "nav-project": ProjectWidget,
            "nav-query": QueryWidget,
            "nav-crawl": CrawlWidget,
            "nav-preprocessing": PreprocessingWidget,
            "nav-classification": ClassificationWidget,
            "nav-results": lambda: ResultWidget(id="result-widget"),
            "nav-database": DatabaseWidget
        }

        self.widget_map = {
            item.id: (WIDGET_CLASSES[item.id]() if not callable(WIDGET_CLASSES[item.id]) 
                    else WIDGET_CLASSES[item.id]())
            for item in NavigationWidget.NAVIGATION_ITEMS
        }

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="outer-layout"):
            with Container(id="nav-container"):
                yield NavigationWidget()
            with Horizontal(id="main-layout"):
                with Container(id="page-container"):
                    for key, widget in self.widget_map.items():
                        widget.display = key == "nav-project"
                        yield widget
            with Container(classes="log-container"):
                yield LogWidget(id="log-panel")
        yield Footer()

    @on(Button.Pressed, "#btn-config")
    @on(Button.Pressed, "#nav-settings")
    def _on_button_config(self):
        self.push_screen(ConfigScreen())

    @on(NavigationWidget.Navigate)
    async def handle_navigation(
        self,
        event: NavigationWidget.Navigate,
    ) -> None:
        for v in self.widget_map.values():
            v.display = False
        self.widget_map[event.page].display = True

        
    @on(Button.Pressed, "#btn-filing-types")
    def action_open_filing_types(self) -> None:
        self.push_screen(
            FilingTypesScreen(),
            self._on_filing_types_confirmed,
        )

    def _on_filing_types_confirmed(self, results: list[str] | None) -> None:
        if results is None:
            return
        
        QueryModel().add_filing_categories(results)

        self.query_one("#filing-types-label", Label).update(
            ", ".join(results) or "None"
        )

    def on_mount(self) -> None:
        Config.reload_config()
        show_log = self.current_page not in self.PAGES_WITHOUT_LOG
        self.query_one("#log-panel", LogWidget).display = show_log
        self.query_one(".log-container", Container).display = show_log
        self._setup_logging()
        self.push_screen(SplashScreen(), callback=self._on_splash_dismissed())
        
    def _on_splash_dismissed(self):
        if not ProjectModel().is_project_active():
            self.push_screen(ProjectScreen())
        else:
            Config.reload_config()
            active = ProjectModel().get_active_project()
            title = active.name if active else "Project"
            self.notify(
                f"Loaded project '{title}'",
                title="Project",
                timeout=5,
            )
            
    def _setup_logging(self):
        rich_log = self.query_one("#log-output", RichLog)
        handler = TextualLogHandler(rich_log)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        ))

        pkg_logger = logging.getLogger("nps_crawling") 
        pkg_logger.setLevel(logging.INFO)
        pkg_logger.addHandler(handler)

    @on(Button.Pressed, "#show-projects-btn")
    def show_projects_view(self):
        self.push_screen(ProjectScreen())

    def watch_current_page(self, page: str) -> None:
        for key, widget in self.widget_map.items():
            widget.display = key == page
        
        show_log = page not in self.PAGES_WITHOUT_LOG
        self.query_one("#log-panel", LogWidget).display = show_log
        self.query_one(".log-container", Container).display = show_log

    @on(NavigationWidget.Navigate)
    def handle_navigation(self, event: NavigationWidget.Navigate) -> None:
        self.current_page = event.page


def _ensure_docker_db_running() -> None:
    """Startet den Docker-Postgres-Container wenn er noch nicht laeuft.

    Prueft zuerst via ``docker compose ps`` ob der Container bereits laeuft.
    Falls ja: kein Start, kein Warten - sofort weiter.
    Falls nein: ``docker compose up -d`` und kurz warten bis Postgres bereit ist.
    """
    import time

    compose_file = Config.ROOT_DIR / "docker" / "database" / "docker-compose.yml"

    # Pruefen ob der Container bereits laeuft
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "ps", "--services", "--filter", "status=running"],
            capture_output=True,
            text=True,
            check=True,
        )
        already_running = bool(result.stdout.strip())
    except FileNotFoundError:
        raise RuntimeError(
            "'docker' wurde nicht gefunden. Bitte Docker Desktop installieren und starten.",
        ) from None
    except subprocess.CalledProcessError:
        already_running = False

    if already_running:
        print("Docker-Postgres laeuft bereits.", flush=True)
        return

    # Container starten
    print("LOCAL_MODE aktiv - starte Docker-Postgres...", flush=True)
    try:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d"],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"'docker compose up -d' ist fehlgeschlagen (Exit-Code {exc.returncode}). "
            "Bitte Docker Desktop starten und erneut versuchen.",
        ) from exc

    # Kurz warten, bis Postgres vollstaendig hochgefahren ist
    time.sleep(3)
    print("Docker-Postgres laeuft.", flush=True)


if __name__ == "__main__":
    if Config.LOCAL_MODE:
        _ensure_docker_db_running()
    CrawlerTuiApp().run()