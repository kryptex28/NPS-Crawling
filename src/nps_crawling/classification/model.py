"""LLMBase abstract class."""
from abc import ABC, abstractmethod
from enum import Enum
from multiprocessing import context
from pathlib import Path
import re

from typing import List
import joblib
from sentence_transformers import SentenceTransformer
import torch
from transformers import AutoModelForCausalLM, AutoModelForQuestionAnswering, AutoTokenizer, pipeline
from ollama import ChatResponse, Client
from pathvalidate import sanitize_filename
from sklearn.svm import SVC
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report

from nps_crawling.classification.options import (
    ClassificationOption,
    ClassificationProperty,
    NPSCategory,
    HasNumericNPS,
    NPSValue
)

class DataEntry:
    """Data entry class."""
    def __init__(self, column_name: str, entry):
        self.column_name = column_name
        self.entry = entry

class ModelBase(ABC):
    """LLM Base abstract class."""
    @abstractmethod
    def __init__(self,
                 model,
                 temperature=0.0,
                 top_p=1.0,
                 top_k=1,
                 num_predict=128,
                 seed=42,
                 repeat_penalty=1.0,
                 **kwargs):
        """Abstract init function."""
        self.options = {
            'temperature': temperature,
            'top_p': top_p,
            'top_k': top_k,
            'num_predict': num_predict,
            'seed': seed,
            'repeat_penalty': repeat_penalty,
        }
        self.options.update(kwargs)

    @abstractmethod
    def classify(self, classification_option: ClassificationOption, text: str) -> List[DataEntry]:
        """Base abstract classify function."""
        pass

    def _convert_float_to_flag(self, labels: List[float], predictions: List[float]) -> tuple[List[int], List[int]]:
        # Convert float labels and predictions to binary flags
        converted_labels = []
        for label in labels:
            if label > 0.0:
                converted_labels.append(1)
            else:
                converted_labels.append(0)
        for i, label in enumerate(labels):
            print(f"Label before: {label}, converted label: {converted_labels[i]}")
        converted_predictions = []
        for i, prediction in enumerate(predictions):
            print(f"Prediction: {prediction} Label: {labels[i]}")
            if prediction == labels[i]:
                converted_predictions.append(converted_labels[i])
            else:
                converted_predictions.append(1 if converted_labels[i] == 0 else 0)
        return converted_labels, converted_predictions

    def evaluate(
        self,
        classification_option: ClassificationOption,
        classification_property: ClassificationProperty,
        texts: List[str],
        labels
    ) -> dict:
        """Evaluate model on given texts and labels."""
        predictions = []
        for text in texts:
            data_entries = self.classify(classification_option, text)
            for data_entry in data_entries:
                if data_entry.column_name == classification_property.name:
                    predictions.append(data_entry.entry)
                    break

        if isinstance(labels[0], float) and isinstance(predictions[0], float):
            labels, predictions = self._convert_float_to_flag(labels, predictions)

        evaluation_results = classification_report(labels, predictions, output_dict=True)
        print(classification_report(labels, predictions))
        return evaluation_results

class LLMBase(ModelBase):

    def _generate_response(self, classification_property: ClassificationProperty, text: str) -> str:
        """Generate response for given classification property and text."""
        pass

    def _classify_nps_category(self, classification_option: NPSCategory, text: str) -> List[DataEntry]:
        """Classify given text."""
        # Since persona is the same for all classification properties in NPSCategory, we can use the first one to generate the response
        classification_property = classification_option.get_classification_properties()[0]
        response = self._generate_response(classification_property, text)

        data_entries = []
        for option in classification_option.get_classification_properties():
            if option.name in response:
                data_entries.append(DataEntry(column_name=option.name, entry=option.options[1]))
            else:
                data_entries.append(DataEntry(column_name=option.name, entry=option.options[0]))

        return data_entries
    
    def _classify_has_numeric_nps(self, classification_option: HasNumericNPS, text: str) -> List[DataEntry]:
        """Classify given text."""
        # Since there is only one classification property for HasNumericNPS, we can use the first one to generate the response
        classification_property = classification_option.get_classification_properties()[0]
        response = self._generate_response(classification_property, text)
        class_properties = classification_option.get_classification_properties()
        for class_property in class_properties:
            for property_value in class_property.options:
                if str(property_value) in response:
                    return [DataEntry(column_name=class_property.name, entry=property_value)]
                return [DataEntry(column_name=class_property.name, entry=class_property.options[0])]
        return [DataEntry(column_name=class_properties[0].name, entry=class_properties[0].options[0])]
    
    def _classify_nps_value(self, classification_option: NPSValue, text: str) -> List[DataEntry]:
        """Classify given text."""
        data_entries = []
        for class_property in classification_option.get_classification_properties():
            response = self._generate_response(class_property, text)
            match = re.search(class_property.options, response)
            if match:
                property_value = float(match.group().replace(',', '.'))
                data_entries.append(DataEntry(column_name=class_property.name, entry=property_value))
            else:
                data_entries.append(DataEntry(column_name=class_property.name, entry=0.0))

        return data_entries

    def classify(self, classification_option: ClassificationOption, text: str) -> List[DataEntry]:
        """Classify given text."""
        if isinstance(classification_option, NPSCategory):
            return self._classify_nps_category(classification_option, text)
        elif isinstance(classification_option, HasNumericNPS):
            return self._classify_has_numeric_nps(classification_option, text)
        elif isinstance(classification_option, NPSValue):
            return self._classify_nps_value(classification_option, text)
        else:
            raise ValueError(f"Unsupported classification option type: {type(classification_option)}")

class LLMHuggingFace(LLMBase):
    """Huggingface LLM class."""
    def __init__(self,
                 temperature=0.0,
                 top_p=1.0,
                 top_k=1,
                 num_predict=128,
                 seed=42,
                 repeat_penalty=1.0,
                 model='mistralai/Mistral-7B-Instruct-v0.3',
                 device=None,
                 **kwargs,
                 ):
        """Initialize Huggingface LLM class."""
        super().__init__(
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            num_predict=num_predict,
            seed=seed,
            repeat_penalty=repeat_penalty,
            model=model,
            **kwargs
        )
        self.model_name = model
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        if torch.cuda.is_available():
            vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"VRAM: {vram:.1f} GB — {torch.cuda.get_device_name(0)}")
        else:
            print("No CUDA GPU detected")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto",
        )
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
        )

    def _generate_response(self, classification_property: ClassificationProperty, text: str) -> str:
        """Generate response for given classification option and text."""
        messages = [
            {"role": "system", "content": classification_property.persona},
            {"role": "user", "content": text},
        ]

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        result = self.pipe(
            prompt,
            max_new_tokens=self.options.get("num_predict", 128),
            temperature=max(self.options.get("temperature", 0.0), 1e-6),  # HF doesn't allow 0.0
            top_p=self.options.get("top_p", 1.0),
            top_k=self.options.get("top_k", 1),
            repetition_penalty=self.options.get("repeat_penalty", 1.0),
            do_sample=self.options.get("temperature", 0.0) > 0,
        )

        generated = result[0]["generated_text"]
        return generated[len(prompt):].strip()


class LLMOllama(LLMBase):
    """Ollama LLM class."""
    def __init__(self,
                 temperature=0.0,
                 top_p=1.0,
                 top_k=1,
                 num_predict=128,
                 seed=42,
                 repeat_penalty=1.0,
                 model='mistral',
                 host='localhost',
                 port=14000,
                 **kwargs,
                 ):
        """Initialize Ollama LLM class."""
        super().__init__(temperature=temperature,
                         model=model,
                         top_k=top_k,
                         top_p=top_p,
                         num_predict=num_predict,
                         seed=seed,
                         repeat_penalty=repeat_penalty,
                         **kwargs)
        self.model = model
        self.host = host
        self.port = port

    def _generate_response(self, classification_property: ClassificationProperty, text: str) -> str:
        """Generate response for given classification property and text."""
        client = Client(host=f"{self.host}:{self.port}")
        response: ChatResponse = client.chat(
            model=self.model,
            messages=[
                {'role': 'system', 'content': classification_property.persona},
                {'role': 'user', 'content': text},
            ],
            options=self.options,
        )
        return response['message']['content'].strip()


class SVMClassificationModel(ModelBase):
    """Classification model using SVM."""
    def __init__(self, model: str, **kwargs):
        BASE_DIR = Path(__file__).resolve().parent
        BGE_CACHE_DIR = BASE_DIR / "cache" / sanitize_filename(model)

        if not BGE_CACHE_DIR.exists():
            BGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            self.embedding_model = SentenceTransformer(model)
            self.embedding_model.save(str(BGE_CACHE_DIR))
        else:
            self.embedding_model = SentenceTransformer(str(BGE_CACHE_DIR))

        self.cache_dir = BASE_DIR / "cache"

    def classify(self, classification_option : ClassificationOption, text: str) -> List[DataEntry]:
        if isinstance(classification_option, NPSValue):
            raise NotImplementedError("SVMClassificationModel does not support NPSValue classification.")
        class_properties = classification_option.get_classification_properties()
        svm_paths = [self.cache_dir / f"{class_property.name}.joblib" for class_property in class_properties]
        for svm_path in svm_paths:
            if not svm_path.exists():
                raise RuntimeError(f"SVM model for {svm_path} not found in cache. Please train the model first.")
        
        embedding = self.embedding_model.encode([text])
        data_entries = []
        for class_property in class_properties:
            svm_model = joblib.load(self.cache_dir / f"{class_property.name}.joblib")
            prediction = svm_model.predict(embedding)
            data_entries.append(DataEntry(column_name=class_property.name, entry=prediction[0]))

        return data_entries

    
    def train(self, classification_property: ClassificationProperty, texts: List[str], labels: List[int]):
        """Train SVM model for given classification option."""
        embeddings = self.embedding_model.encode(texts)
        svm_model = make_pipeline(StandardScaler(), SVC(kernel='linear', random_state=42))
        svm_model.fit(embeddings, labels)
        joblib.dump(svm_model, self.cache_dir / f"{classification_property.name}.joblib")
    
class QAHuggingface(LLMBase):
    """Classification model using question answering."""
    def __init__(self,
                temperature=0.0,
                top_p=1.0,
                top_k=1,
                num_predict=128,
                seed=42,
                repeat_penalty=1.0,
                model='timpal0l/mdeberta-v3-base-squad2',
                device=None,
                **kwargs,
                ):
        """Initialize Huggingface LLM class."""
        super().__init__(temperature=temperature,
                            top_k=top_k,
                            top_p=top_p,
                            num_predict=num_predict,
                            seed=seed,
                            repeat_penalty=repeat_penalty,
                            model=model,
                            **kwargs)
        self.model_name = model
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        if torch.cuda.is_available():
            vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"VRAM: {vram:.1f} GB — {torch.cuda.get_device_name(0)}")
        else:
            print("No CUDA GPU detected")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForQuestionAnswering.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto",
        )
        self.pipe = pipeline(
            "question-answering",
            model=self.model,
            tokenizer=self.tokenizer,
        )

    def _generate_response(self, classification_property: ClassificationProperty, text: str) -> str:
        """Generate response for given classification property and text."""
        result = self.pipe(question = classification_property.persona, context = text)
        return result["answer"].strip()

class ClassificationClass(str, Enum):
    """Enum for classification classes."""
    LLMHUGGINGFACE = "LLMHuggingFace"
    LLMOLLAMA = "LLMOllama"
    SVM = "SVM"
    QAHUGGINGFACE = "QAHuggingFace"

_MODEL_CLASSES_MAP = {
    ClassificationClass.LLMHUGGINGFACE: LLMHuggingFace,
    ClassificationClass.LLMOLLAMA: LLMOllama,
    ClassificationClass.SVM: SVMClassificationModel,
    ClassificationClass.QAHUGGINGFACE: QAHuggingface,
}

def get_model_class(model_class: ClassificationClass, model_kwargs= dict()) -> ModelBase:
    """Get model class based on classification class."""
    if model_class not in _MODEL_CLASSES_MAP:
        raise ValueError(f"Unsupported model class: {model_class}")
    return _MODEL_CLASSES_MAP[model_class](**model_kwargs)