import os

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from torch import Tensor
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel

from nps_crawling.classification.models.model import ClassificationModel, SEED
from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    DataEntry,
    ClassificationProperty,
)
from nps_crawling.classification.categories.registry import ClassificationTask

class QWEN_Advanced(ClassificationModel):
    """Hugging Face Model class."""
    def __init__(self, model_name: str, classification_categories: list[ClassificationCategory], **kwargs):
        super().__init__(model_name, **kwargs)
        # load the tokenizer and the model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=self.cache_dir, padding_side="left")
        self.model = AutoModel.from_pretrained(model_name, cache_dir=self.cache_dir)
        self.model.eval()

    @staticmethod
    def _last_token_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
        left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
        if left_padding:
            return last_hidden_states[:, -1]
        else:
            sequence_lengths = attention_mask.sum(dim=1) - 1
            batch_size = last_hidden_states.shape[0]
            return last_hidden_states[
                torch.arange(batch_size, device=last_hidden_states.device),
                sequence_lengths
            ]

    @staticmethod
    def _format_instruction(task_description: str, text: str) -> str:
        return f"Instruct: {task_description}\nQuery: {text}"

    def _get_instruction(self, classification_property: ClassificationProperty) -> str:
        CATEGORY_INSTRUCTIONS = {
            "KPI_CURRENT_VALUE": (
                "Represent the text for classifying whether it contains explicit current "
                "Net Promoter Score (NPS) values or KPI measurements, including numerical "
                "scores, percentages, or reported NPS metrics."
            ),
            "KPI_TREND": (
                "Represent the text for classifying whether it describes changes, developments, "
                "or trends in Net Promoter Score (NPS) over time, including improvements, declines, "
                "increases, decreases, or stability."
            ),
            "KPI_HISTORICAL_COMPARISON": (
                "Represent the text for classifying whether it contains explicit comparisons between "
                "current and past Net Promoter Score (NPS) values, including year-over-year, "
                "quarter-over-quarter, or historical comparisons."
            ),
            "TARGET_OUTLOOK": (
                "Represent the text for classifying whether it contains future Net Promoter Score (NPS) "
                "goals, targets, ambitions, expectations, forecasts, or planned improvements."
            ),
            "NPS_GOAL_REACHED": (
                "Represent the text for classifying whether it states that a Net Promoter Score (NPS) "
                "target, goal, threshold, or benchmark has been achieved, reached, met, or exceeded."
            ),
            "METHODOLOGY_DEFINITION": (
                "Represent the text for classifying whether it explains, defines, or describes what "
                "Net Promoter Score (NPS) is, how it works, or how it is calculated."
            ),
            "QUALITATIVE_ONLY": (
                "Represent the text for classifying whether it discusses Net Promoter Score (NPS) "
                "qualitatively without explicit numerical values, historical comparisons, trends, "
                "targets, or goal achievement."
            ),
        }
        return CATEGORY_INSTRUCTIONS.get(classification_property.name, "Represent the text for classification.")

    def _get_embedding(self, text: str, classification_property: ClassificationProperty):
        instruction = self._get_instruction(classification_property)
        formatted_text = self._format_instruction(instruction, text)

        encoded_input = self.tokenizer(
            formatted_text,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )

        with torch.no_grad():
            model_output = self.model(**encoded_input)
            sentence_embedding = self._last_token_pool(
                model_output.last_hidden_state,
                encoded_input["attention_mask"]
            )

        sentence_embedding = F.normalize(sentence_embedding, p=2, dim=1)
        return sentence_embedding.squeeze(0).float().cpu().numpy()

    def classify(self, text: str, category: ClassificationCategory) -> DataEntry:
        # prepare the model input
        
        svm_paths = [self.cache_dir / f"{class_property.name}.joblib" for class_property in category.properties]
        for svm_path in svm_paths:
            if not svm_path.exists():
                raise RuntimeError(f"SVM model for {svm_path} not found in cache. Please train the model first.")
        
        data_entries = []
        for class_property in category.properties:
            embedding = self._get_embedding(text, class_property).reshape(1, -1)
            svm_model = joblib.load(self.cache_dir / f"{class_property.name}.joblib")
            prediction = svm_model.predict(embedding)
            data_entries.append(DataEntry(column_name=class_property.name, value=prediction[0]))

        return data_entries
    
    def train(self, category: ClassificationCategory, text_column : str, test_size = 0.2) -> None:
        """Train SVM model for given classification option."""
        if not category.csv_path:
            raise ValueError("No csv as groundtruth provided")

        df = pd.read_csv(category.csv_path)
        train_df, test_df = train_test_split(df, test_size=test_size, random_state=SEED)
        texts = train_df["snippet_text_short"].tolist()

        for class_property in category.properties:
            labels = df[class_property.name].tolist()
            embeddings = [self._get_embedding(text, class_property) for text in texts]
            svm_model = make_pipeline(StandardScaler(), SVC(kernel='linear', random_state=42))
            svm_model.fit(embeddings, labels)
            joblib.dump(svm_model, self.cache_dir / f"{class_property.name}.joblib")
    