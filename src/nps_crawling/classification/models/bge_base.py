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
)
from nps_crawling.classification.categories.registry import ClassificationTask

class BGE_Base(ClassificationModel):
    """Hugging Face Model class."""
    def __init__(self, model_name: str, **kwargs):
        super().__init__(model_name, **kwargs)
        # load the tokenizer and the model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=self.cache_dir)
        self.model = AutoModel.from_pretrained(model_name, cache_dir=self.cache_dir)
        self.model.eval()

    def _get_embedding(self, text: str):
        """Get embedding for given text."""
        # Tokenize sentences
        encoded_input = self.tokenizer(text, padding=True, truncation=True, return_tensors='pt')
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
        
        embedding = self._get_embedding(text).reshape(1, -1)
        data_entries = []
        for class_property in category.properties:
            svm_model = joblib.load(self.cache_dir / f"{class_property.name}.joblib")
            prediction = svm_model.predict(embedding)
            data_entries.append(DataEntry(column_name=class_property.name, value=prediction[0]))

        return data_entries
    
    def train(self, df : pd.DataFrame, category: ClassificationCategory) -> None:
        """Train SVM model for given classification option."""
        texts = df["snippet_text_short"].tolist()

        for class_property in category.properties:
            labels = df[class_property.name].tolist()
            embeddings = [self._get_embedding(text) for text in texts]
            svm_model = make_pipeline(StandardScaler(), SVC(kernel='linear', random_state=42))
            svm_model.fit(embeddings, labels)
            joblib.dump(svm_model, self.cache_dir / f"{class_property.name}.joblib")