

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import (
    Input,
    Static,
    Button,
)
from models.project_model import ProjectModel
from data_package.project_data import ProjectData
from nps_crawling.config import Config

class ProjectWidget(Static):
    def __init__(self) -> None:
        super().__init__()

        self.model = ProjectModel()

    def compose(self) -> ComposeResult:
        with ScrollableContainer():
            yield Static("Project Name", id="project-name-label")
            yield Input(placeholder="Enter project name", id="project-name-input")
            yield Static("Project Description", id="project-desc-label")
            yield Input(placeholder="Enter project description", id="project-desc-input")
            yield Static("", id="project-active-label")

            with Horizontal():
                yield Button("Save Project", id="save-project-btn", variant="success")
                yield Button("Load Project", id="load-project-btn", variant="primary")
                yield Button("Clear Form", id="clear-form-btn", variant="warning")
                yield Button("Show Projects", id="show-projects-btn")

    def on_mount(self) -> None:
        self._show_active_project()

    def _show_active_project(self) -> None:
        active = self.model.get_active_project()
        label = self.query_one("#project-active-label", Static)
        if active:
            label.update(f"Active project: {active.name}")
            self.query_one("#project-name-input", Input).value = active.name
            self.query_one("#project-desc-input", Input).value = active.description
        else:
            label.update("No active project loaded.")

    @on(Button.Pressed, "#save-project-btn")
    def save_project(self):
        project_name: str = self.query_one("#project-name-input", Input).value.strip()
        project_description: str = self.query_one("#project-desc-input", Input).value.strip()
        if not project_name:
            self.app.notify("Enter a project name.", severity="warning")
            return

        self.model.save_project(
            project_data=ProjectData(
                name=project_name,
                description=project_description,
                id=1,
            ),
        )
        self._show_active_project()
        self.app.notify(f"Saved and loaded project '{project_name}'.", severity="information")

    @on(Button.Pressed, "#load-project-btn")
    def load_project(self):
        project_name: str = self.query_one("#project-name-input", Input).value.strip()
        if not project_name:
            self.app.notify("Enter a project name.", severity="warning")
            return

        self.model.load_project(
            ProjectData(
                name=project_name,
                description=self.query_one("#project-desc-input", Input).value.strip(),
                id=1,
            ),
        )
        self._show_active_project()
        self.app.notify(f"Loaded project '{project_name}'.", severity="information")

    @on(Button.Pressed, "#clear-form-btn")
    def clear_form(self):
        self.query_one("#project-name-input", Input).value = ""
        self.query_one("#project-desc-input", Input).value = ""

    def on_show(self) -> None:
        self._show_active_project()
