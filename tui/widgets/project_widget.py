

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

            yield Static("Crawl Config File Path", id="project-crawl-label")
            with Horizontal(classes="config-row"):
                yield Input(placeholder="projects/configs/crawl/default.json", id="project-crawl-input")
                yield Button("Add", id="add-crawl-config-btn", variant="primary")

            yield Static("Preprocess Config File Path", id="project-preprocess-label")
            with Horizontal(classes="config-row"):
                yield Input(placeholder="projects/configs/preprocess/version_2.json", id="project-preprocess-input")
                yield Button("Add", id="add-preprocess-config-btn", variant="primary")

            yield Static("Classification Config File Path", id="project-classification-label")
            with Horizontal(classes="config-row"):
                yield Input(placeholder="projects/configs/classification/version_1.json", id="project-classification-input")
                yield Button("Add", id="add-classification-config-btn", variant="primary")

            yield Static("", id="project-active-label")

            with Horizontal():
                yield Button("Save Project", id="save-project-btn", variant="success")
                yield Button("Load Project", id="load-project-btn", variant="primary")
                yield Button("Clear Form", id="clear-form-btn", variant="warning")
                yield Button("Show Projects", id="show-projects-btn")

    @on(Button.Pressed, "#add-crawl-config-btn")
    def create_crawl_config(self) -> None:
        inp = self.query_one("#project-crawl-input", Input)
        try:
            created_path = self.model.create_config_file(inp.value, "crawl")
            inp.value = created_path
            self.app.notify(f"Created Crawl config at: {created_path}", severity="information")
        except FileExistsError as e:
            self.app.notify(str(e), severity="warning")
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#add-preprocess-config-btn")
    def create_preprocess_config(self) -> None:
        inp = self.query_one("#project-preprocess-input", Input)
        try:
            created_path = self.model.create_config_file(inp.value, "preprocess")
            inp.value = created_path
            self.app.notify(f"Created Preprocess config at: {created_path}", severity="information")
        except FileExistsError as e:
            self.app.notify(str(e), severity="warning")
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#add-classification-config-btn")
    def create_classification_config(self) -> None:
        inp = self.query_one("#project-classification-input", Input)
        try:
            created_path = self.model.create_config_file(inp.value, "classification")
            inp.value = created_path
            self.app.notify(f"Created Classification config at: {created_path}", severity="information")
        except FileExistsError as e:
            self.app.notify(str(e), severity="warning")
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

    def on_mount(self) -> None:
        self._show_active_project()

    def _show_active_project(self) -> None:
        active = self.model.get_active_project()
        label = self.query_one("#project-active-label", Static)
        if active:
            label.update(f"Active project: {active.name}")
            self.query_one("#project-name-input", Input).value = active.name
            self.query_one("#project-desc-input", Input).value = active.description
            self.query_one("#project-crawl-input", Input).value = active.crawl_config
            self.query_one("#project-preprocess-input", Input).value = active.preprocess_config
            self.query_one("#project-classification-input", Input).value = active.classification_config
        else:
            label.update("No active project loaded.")

    @on(Button.Pressed, "#save-project-btn")
    def save_project(self):
        project_name: str = self.query_one("#project-name-input", Input).value.strip()
        project_description: str = self.query_one("#project-desc-input", Input).value.strip()
        crawl_config: str = self.query_one("#project-crawl-input", Input).value.strip()
        preprocess_config: str = self.query_one("#project-preprocess-input", Input).value.strip()
        classification_config: str = self.query_one("#project-classification-input", Input).value.strip()
        
        if not project_name:
            self.app.notify("Enter a project name.", severity="warning")
            return

        self.model.save_project(
            project_data=ProjectData(
                name=project_name,
                description=project_description,
                id=1,
                crawl_config=crawl_config,
                preprocess_config=preprocess_config,
                classification_config=classification_config,
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
        self.query_one("#project-crawl-input", Input).value = ""
        self.query_one("#project-preprocess-input", Input).value = ""
        self.query_one("#project-classification-input", Input).value = ""

    def on_show(self) -> None:
        self._show_active_project()
