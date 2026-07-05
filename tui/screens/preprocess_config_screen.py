from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Label, Input, Switch
from textual import on

from models.preprocessing_model import PreprocessingModel


class PreprocessConfigScreen(ModalScreen):
    CSS_PATH = "preprocess_config_screen.tcss"

    def __init__(self) -> None:
        super().__init__()
        self.model = PreprocessingModel()
        self.config_path = self.model.get_config_path()
        self.config_data = self.model.get_config()

    def compose(self) -> ComposeResult:
        with Container():
            yield Static(f"Configure Preprocess ({self.config_path.name})", classes="modal-title")
            
            with ScrollableContainer(id="preprocess-config-form"):
                # Version
                with Horizontal(classes="form-row"):
                    yield Label("Version:")
                    yield Input(self.config_data.get("version", ""), id="prep-version")

                # Single Keyword Filter
                with Horizontal(classes="form-row"):
                    yield Label("Single Keyword Filter:")
                    yield Input(self.config_data.get("single_keyword_filter") or "", id="prep-single-keyword-filter")

                # Single Keyword Filter Strict
                with Horizontal(classes="form-row"):
                    yield Label("Single Keyword Filter Strict:")
                    yield Switch(value=bool(self.config_data.get("single_keyword_filter_strict", True)), id="prep-single-keyword-filter-strict")

                # Threshold Keyword Scope
                with Horizontal(classes="form-row"):
                    yield Label("Threshold Keyword Scope (comma-separated):")
                    scope_val = ", ".join(self.config_data.get("threshold_keyword_scope") or [])
                    yield Input(scope_val, id="prep-threshold-keyword-scope")

                # Threshold Keyword Scope Strict
                with Horizontal(classes="form-row"):
                    yield Label("Threshold Keyword Scope Strict:")
                    yield Switch(value=bool(self.config_data.get("threshold_keyword_scope_strict", True)), id="prep-threshold-keyword-scope-strict")

                # Similarity Threshold Context Window
                with Horizontal(classes="form-row"):
                    yield Label("Similarity Threshold Context Window:")
                    yield Input(str(self.config_data.get("similarity_threshold_context_window", 0.8)), id="prep-similarity-threshold")

                # Similarity Reference Text
                with Horizontal(classes="form-row"):
                    yield Label("Similarity Reference Text:")
                    yield Input(self.config_data.get("similarity_reference_text", ""), id="prep-similarity-reference-text")

                # Similarity Embedding Model
                with Horizontal(classes="form-row"):
                    yield Label("Similarity Embedding Model:")
                    yield Input(self.config_data.get("similarity_embedding_model", ""), id="prep-similarity-embedding-model")

                # Amount Sentences Included Before
                with Horizontal(classes="form-row"):
                    yield Label("Amount Sentences Included Before:")
                    yield Input(str(self.config_data.get("amount_sentences_included_before", 2)), id="prep-sentences-before")

                # Amount Sentences Included After
                with Horizontal(classes="form-row"):
                    yield Label("Amount Sentences Included After:")
                    yield Input(str(self.config_data.get("amount_sentences_included_after", 2)), id="prep-sentences-after")

                # Max Context Chars Before Keyword
                with Horizontal(classes="form-row"):
                    yield Label("Max Context Chars Before Keyword:")
                    yield Input(str(self.config_data.get("max_context_chars_before_keyword", 600)), id="prep-chars-before")

                # Max Context Chars After Keyword
                with Horizontal(classes="form-row"):
                    yield Label("Max Context Chars After Keyword:")
                    yield Input(str(self.config_data.get("max_context_chars_after_keyword", 600)), id="prep-chars-after")

                # Files Per Chunk
                with Horizontal(classes="form-row"):
                    yield Label("Files Per Chunk:")
                    yield Input(str(self.config_data.get("files_per_chunk", 1000)), id="prep-files-per-chunk")

                # Phrases to Filter Filings For
                with Horizontal(classes="form-row"):
                    yield Label("Phrases to Filter Filings For (comma-separated):")
                    phrases_val = ", ".join(self.config_data.get("list_of_phrases_to_filter_filings_for") or [])
                    yield Input(phrases_val, id="prep-phrases-filter")

                # Phrases to Exclude
                with Horizontal(classes="form-row"):
                    yield Label("Phrases to Exclude (comma-separated):")
                    exclude_val = ", ".join(self.config_data.get("list_of_phrases_to_exclude") or [])
                    yield Input(exclude_val, id="prep-phrases-exclude")

            with Horizontal(classes="modal-footer"):
                yield Button("Save", variant="success", id="save-config-btn")
                yield Button("Cancel", variant="error", id="cancel-config-btn")

    @on(Button.Pressed, "#cancel-config-btn")
    def cancel(self) -> None:
        self.dismiss()

    @on(Button.Pressed, "#save-config-btn")
    def save(self) -> None:
        try:
            # Parse list fields
            scope_raw = self.query_one("#prep-threshold-keyword-scope", Input).value
            scope = [s.strip() for s in scope_raw.split(",") if s.strip()]

            phrases_filter_raw = self.query_one("#prep-phrases-filter", Input).value
            phrases_filter = [p.strip() for p in phrases_filter_raw.split(",") if p.strip()]

            phrases_exclude_raw = self.query_one("#prep-phrases-exclude", Input).value
            phrases_exclude = [p.strip() for p in phrases_exclude_raw.split(",") if p.strip()]

            # Single keyword filter can be null/None or string
            skf = self.query_one("#prep-single-keyword-filter", Input).value.strip()
            single_keyword_filter = skf if skf else None

            # Parse numeric/bool fields
            updates = {
                "version": self.query_one("#prep-version", Input).value.strip(),
                "single_keyword_filter": single_keyword_filter,
                "single_keyword_filter_strict": self.query_one("#prep-single-keyword-filter-strict", Switch).value,
                "threshold_keyword_scope": scope,
                "threshold_keyword_scope_strict": self.query_one("#prep-threshold-keyword-scope-strict", Switch).value,
                "similarity_threshold_context_window": float(self.query_one("#prep-similarity-threshold", Input).value),
                "similarity_reference_text": self.query_one("#prep-similarity-reference-text", Input).value,
                "similarity_embedding_model": self.query_one("#prep-similarity-embedding-model", Input).value.strip(),
                "amount_sentences_included_before": int(self.query_one("#prep-sentences-before", Input).value),
                "amount_sentences_included_after": int(self.query_one("#prep-sentences-after", Input).value),
                "max_context_chars_before_keyword": int(self.query_one("#prep-chars-before", Input).value),
                "max_context_chars_after_keyword": int(self.query_one("#prep-chars-after", Input).value),
                "files_per_chunk": int(self.query_one("#prep-files-per-chunk", Input).value),
                "list_of_phrases_to_filter_filings_for": phrases_filter,
                "list_of_phrases_to_exclude": phrases_exclude,
            }

            self.model.save_config(updates)
            self.app.notify("Preprocess configuration saved successfully.", severity="information")
            self.dismiss(True)
        except ValueError:
            self.app.notify("Invalid number value: please verify numeric fields.", severity="error")
        except Exception as e:
            self.app.notify(f"Error saving configuration: {e}", severity="error")
