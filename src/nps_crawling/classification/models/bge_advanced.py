import os

import joblib
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
import torch
from transformers import AutoTokenizer, AutoModel

from nps_crawling.classification.models.model import ClassificationModel
from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    DataEntry,
    ClassificationProperty,
)
from nps_crawling.classification.categories.registry import ClassificationTask

class BGE_Advanced(ClassificationModel):
    """Hugging Face Model class."""
    def __init__(self, model_name: str, **kwargs):
        super().__init__(model_name, **kwargs)
        # load the tokenizer and the model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=self.cache_dir)
        self.model = AutoModel.from_pretrained(model_name, cache_dir=self.cache_dir)
        self.model.eval()

    def _get_embedding(self, text: str, classification_property : ClassificationProperty):
        """Get embedding for given text."""
        CATEGORY_INSTRUCTIONS = {
            "KPI_CURRENT_VALUE": (
                "Represent the sentence for detecting explicit current "
                "Net Promoter Score (NPS) values or KPI measurements, "
                "including numerical scores, percentages, or reported NPS metrics."
            ),

            "KPI_TREND": (
                "Represent the sentence for detecting changes, developments, "
                "or trends in Net Promoter Score (NPS) over time, including "
                "improvements, declines, increases, decreases, or stability."
            ),

            "KPI_HISTORICAL_COMPARISON": (
                "Represent the sentence for detecting explicit comparisons "
                "between current and past Net Promoter Score (NPS) values, "
                "including year-over-year, quarter-over-quarter, or historical comparisons."
            ),

            "TARGET_OUTLOOK": (
                "Represent the sentence for detecting future Net Promoter Score (NPS) "
                "goals, targets, ambitions, expectations, forecasts, or planned improvements."
            ),

            "NPS_GOAL_REACHED": (
                "Represent the sentence for detecting statements that a "
                "Net Promoter Score (NPS) target, goal, threshold, or benchmark "
                "has been achieved, reached, met, or exceeded."
            ),

            "METHODOLOGY_DEFINITION": (
                "Represent the sentence for detecting explanations, definitions, "
                "or descriptions of what Net Promoter Score (NPS) is, "
                "how it works, or how it is calculated."
            ),

            "QUALITATIVE_ONLY": (
                "Represent the sentence for detecting qualitative discussion "
                "of Net Promoter Score (NPS) without explicit numerical values, "
                "historical comparisons, trends, targets, or goal achievement."
            ),
        }
        input = CATEGORY_INSTRUCTIONS.get(classification_property.name, "") + " Sentence: " + text
        # Tokenize sentences
        encoded_input = self.tokenizer(input, padding=True, truncation=True, return_tensors='pt')
        # for s2p(short query to long passage) retrieval task, add an instruction to query (not add instruction for passages)
        # encoded_input = self.tokenizer([instruction + q for q in queries], padding=True, truncation=True, return_tensors='pt')

        # Compute token embeddings
        with torch.no_grad():
            model_output = self.model(**encoded_input)
            # Perform pooling. In this case, cls pooling.
            sentence_embeddings = model_output[0][:, 0]
        # normalize embeddings
        sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
        return sentence_embeddings.squeeze(0).cpu().numpy()

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
    
    def train(self, df : pd.DataFrame, category: ClassificationCategory) -> None:
        """Train SVM model for given classification option."""
        texts = df["snippet_text_short"].tolist()

        for class_property in category.properties:
            labels = df[class_property.name].tolist()
            embeddings = [self._get_embedding(text, class_property) for text in texts]
            svm_model = make_pipeline(StandardScaler(), SVC(kernel='linear', random_state=42))
            svm_model.fit(embeddings, labels)
            joblib.dump(svm_model, self.cache_dir / f"{class_property.name}.joblib")