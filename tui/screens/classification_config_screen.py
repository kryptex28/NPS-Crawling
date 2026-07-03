from __future__ import annotations
import json
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Label, Input, Switch
from textual import on

from models.classification_model import ClassificationModel


class ClassificationConfigScreen(ModalScreen):
    CSS_PATH = "classification_config_screen.tcss"

    def __init__(self) -> None:
        super().__init__()
        self.model = ClassificationModel()
        self.config_path = self.model.get_config_path()
        self.config_data = self.model.get_config()

    def compose(self) -> ComposeResult:
        with Container():
            yield Static(f"Configure Classification ({self.config_path.name})", classes="modal-title")
            
            with ScrollableContainer(id="classification-config-form"):
                # Version
                with Horizontal(classes="form-row"):
                    yield Label("Version:")
                    yield Input(self.config_data.get("version", ""), id="class-version")

                # Random Seed
                with Horizontal(classes="form-row"):
                    yield Label("Random Seed:")
                    yield Input(str(self.config_data.get("random_seed", 42)), id="class-random-seed")

                # Ground Truth Test Size
                with Horizontal(classes="form-row"):
                    yield Label("Ground Truth Test Size:")
                    yield Input(str(self.config_data.get("ground_truth_test_size", 0.5)), id="class-ground-truth-size")

                # Few Shot Num Examples
                with Horizontal(classes="form-row"):
                    yield Label("Few Shot Num Examples:")
                    yield Input(str(self.config_data.get("few_shot_num_examples", 8)), id="class-few-shot-examples")

                # Few Shot Text Column
                with Horizontal(classes="form-row"):
                    yield Label("Few Shot Text Column:")
                    yield Input(self.config_data.get("few_shot_text_column", "snippet_text_short"), id="class-few-shot-column")

                # Few Shot Sample Seed
                with Horizontal(classes="form-row"):
                    yield Label("Few Shot Sample Seed:")
                    yield Input(str(self.config_data.get("few_shot_sample_seed", 43)), id="class-few-shot-seed")

                # Config Use Name Files
                with Horizontal(classes="form-row"):
                    yield Label("Config Use Name Files:")
                    yield Switch(value=bool(self.config_data.get("config_use_name_files", False)), id="class-use-name-files")

                # Embedding Batch Size
                with Horizontal(classes="form-row"):
                    yield Label("Embedding Batch Size:")
                    yield Input(str(self.config_data.get("embedding_batch_size", 32)), id="class-embedding-batch")

                # LLM Batch Size
                with Horizontal(classes="form-row"):
                    yield Label("LLM Batch Size:")
                    yield Input(str(self.config_data.get("llm_batch_size", 8)), id="class-llm-batch")

                # Classification Configuration (JSON string)
                with Horizontal(classes="form-row"):
                    yield Label("Configuration (JSON Array):")
                    config_val = json.dumps(self.config_data.get("classification_configuration", []))
                    yield Input(config_val, id="class-config-conf")

            with Horizontal(classes="modal-footer"):
                yield Button("Save", variant="success", id="save-config-btn")
                yield Button("Cancel", variant="error", id="cancel-config-btn")

    @on(Button.Pressed, "#cancel-config-btn")
    def cancel(self) -> None:
        self.dismiss()

    @on(Button.Pressed, "#save-config-btn")
    def save(self) -> None:
        try:
            # Parse numeric/bool/json fields
            config_conf_raw = self.query_one("#class-config-conf", Input).value.strip()
            config_conf = json.loads(config_conf_raw) if config_conf_raw else []

            updates = {
                "version": self.query_one("#class-version", Input).value.strip(),
                "random_seed": int(self.query_one("#class-random-seed", Input).value),
                "ground_truth_test_size": float(self.query_one("#class-ground-truth-size", Input).value),
                "few_shot_num_examples": int(self.query_one("#class-few-shot-examples", Input).value),
                "few_shot_text_column": self.query_one("#class-few-shot-column", Input).value.strip(),
                "few_shot_sample_seed": int(self.query_one("#class-few-shot-seed", Input).value),
                "config_use_name_files": self.query_one("#class-use-name-files", Switch).value,
                "embedding_batch_size": int(self.query_one("#class-embedding-batch", Input).value),
                "llm_batch_size": int(self.query_one("#class-llm-batch", Input).value),
                "classification_configuration": config_conf,
            }

            self.model.save_config(updates)
            self.app.notify("Classification configuration saved successfully.", severity="information")
            self.dismiss(True)
        except ValueError:
            self.app.notify("Invalid number value: please verify numeric fields.", severity="error")
        except json.JSONDecodeError:
            self.app.notify("Invalid JSON format in configuration field.", severity="error")
        except Exception as e:
            self.app.notify(f"Error saving configuration: {e}", severity="error")
