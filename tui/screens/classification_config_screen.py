from __future__ import annotations
import json
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Label, Input, Switch, Select
from textual import on

from models.classification_model import ClassificationModel


class ClassificationConfigScreen(ModalScreen):
    CSS_PATH = "classification_config_screen.tcss"

    def __init__(self) -> None:
        super().__init__()
        self.model = ClassificationModel()
        self.config_path = self.model.get_config_path()
        self.config_data = self.model.get_config()
        self.current_class, self.current_model = self._get_current_model_info()

    def _get_current_model_info(self) -> tuple[str, str]:
        entries = self.config_data.get("classification_configuration", [])
        if not entries:
            return "HF_LLM", ""
        
        first_entry = entries[0]
        model_ref = first_entry.get("model")
        if not model_ref:
            return "HF_LLM", ""
            
        if isinstance(model_ref, dict):
            class_name = model_ref.get("class_name", "HF_LLM")
            model_name = model_ref.get("model_name", "")
            return class_name, model_name
        
        try:
            from nps_crawling.project_config import resolve_config_path
            path = resolve_config_path(str(model_ref))
            if path.is_file():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("class_name", "HF_LLM"), data.get("model_name", "")
        except Exception:
            pass
            
        return "HF_LLM", ""

    def compose(self) -> ComposeResult:
        display_class = "HF_LLM"
        if self.current_class in ("OpenAIModel", "OpenAI", "openai"):
            display_class = "OpenAI"
        elif self.current_class in ("QWEN_Unified", "qwen_concatinated", "Qwen_concat", "qwen_concat"):
            display_class = "Qwen_concat"

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

                # Model Type (Selection)
                with Horizontal(classes="form-row"):
                    yield Label("Model Type:")
                    yield Select(
                        options=[
                            ("OpenAI", "OpenAI"),
                            ("HF_LLM", "HF_LLM"),
                            ("Qwen_concat", "Qwen_concat")
                        ],
                        value=display_class,
                        id="class-model-type",
                        allow_blank=False
                    )

                # Model Name (Input)
                with Horizontal(classes="form-row"):
                    yield Label("Model Name:")
                    yield Input(self.current_model, id="class-model-name")

            with Horizontal(classes="modal-footer"):
                yield Button("Save", variant="success", id="save-config-btn")
                yield Button("Cancel", variant="error", id="cancel-config-btn")

    @on(Button.Pressed, "#cancel-config-btn")
    def cancel(self) -> None:
        self.dismiss()

    @on(Button.Pressed, "#save-config-btn")
    def save(self) -> None:
        try:
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
            }

            self.model.save_config(updates)
            self.app.notify("Classification configuration saved successfully.", severity="information")
            self.dismiss(True)
        except ValueError:
            self.app.notify("Invalid number value: please verify numeric fields.", severity="error")
        except Exception as e:
            self.app.notify(f"Error saving configuration: {e}", severity="error")
