"""LLMBase abstract class."""
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
import re
from turtle import pd

from git import List
import joblib
from sympy import re
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
                 persona,
                 model,
                 temperature=0.0,
                 top_p=1.0,
                 top_k=1,
                 num_predict=128,
                 seed=42,
                 repeat_penalty=1.0,
                 **kwargs):
        """Abstract init function."""
        self.persona = persona
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

        evaluation_results = classification_report(labels, predictions, output_dict=True)
        print(classification_report(labels, predictions))
        return evaluation_results

class LLMBase(ModelBase):

    def _generate_response(self, classification_option: ClassificationOption, text: str) -> str:
        """Generate response for given classification option and text."""
        pass

    def classify(self, classification_option: NPSCategory, text: str) -> List[DataEntry]:
        """Classify given text."""
        response = self._generate_response(classification_option, text)

        data_entries = List[DataEntry]()

        for option in classification_option.get_classification_properties():
            if option.name in response:
                data_entries.append(DataEntry(column_name=option.name, entry=option.options[1]))
            else:
                data_entries.append(DataEntry(column_name=option.name, entry=option.options[0]))

        return data_entries

    def classify(self, classification_option: HasNumericNPS, text: str) -> List[DataEntry]:
        """Classify given text."""
        response = self._generate_response(classification_option, text)
        class_properties = classification_option.get_classification_properties()
        for class_property in class_properties:
            match = re.search(class_property.options, response)
            if match:
                property_value = float(match.group().replace(',', '.'))
                return [DataEntry(column_name=class_property.name, entry=property_value)]
        return [DataEntry(column_name=class_properties[0].name, entry=-1)]

    def classify(self, classification_option: NPSValue, text: str) -> List[DataEntry]:
        """Classify given text."""
        response = self._generate_response(classification_option, text)
        class_properties = classification_option.get_classification_properties()
        for class_property in class_properties:
            for property_value in class_property.options:
                if str(property_value) in response:
                    return [DataEntry(column_name=class_property.name, entry=property_value)]
                return [DataEntry(column_name=class_property.name, entry=class_property.options[0])]
        return [DataEntry(column_name=class_properties[0].name, entry=class_properties[0].options[0])]

class LLMHuggingFace(LLMBase):
    """Huggingface LLM class."""
    def __init__(self,
                 persona,
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
        super().__init__(persona=persona,
                         temperature=temperature,
                         top_k=top_k,
                         top_p=top_p,
                         num_predict=num_predict,
                         seed=seed,
                         repeat_penalty=repeat_penalty,
                         **kwargs)
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

    def _generate_response(self, classification_option: ClassificationOption, text: str) -> str:
        """Generate response for given classification option and text."""
        messages = [
            {"role": "system", "content": classification_option.get_persona()},
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
                 persona,
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
        super().__init__(persona=persona,
                         temperature=temperature,
                         top_k=top_k,
                         top_p=top_p,
                         num_predict=num_predict,
                         seed=seed,
                         repeat_penalty=repeat_penalty,
                         **kwargs)
        self.model = model
        self.host = host
        self.port = port

    def _generate_response(self, classification_option: ClassificationOption, text: str) -> str:
        """Generate response for given classification option and text."""
        client = Client(host=f"{self.host}:{self.port}")
        response: ChatResponse = client.chat(
            model=self.model,
            messages=[
                {'role': 'system', 'content': classification_option.get_persona()},
                {'role': 'user', 'content': text},
            ],
            options=self.options,
        )
        return response['message']['content'].strip()


class SVMClassificationModel(ModelBase):
    """Classification model using SVM."""
    def __init__(self, model: str, qa_model: str, **kwargs):
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
        class_properties = classification_option.get_classification_properties()
        svm_paths = [self.cache_dir / class_property.name for class_property in class_properties]
        for svm_path in svm_paths:
            if not svm_path.exists():
                raise RuntimeError(f"SVM model for {svm_path.stem} not found in cache. Please train the model first.")
        
        embedding = self.embedding_model.encode([text])
        data_entries = List[DataEntry]()
        for class_property in class_properties:
            svm_model = joblib.load(self.cache_dir / f"{class_property.name}.joblib")
            prediction = svm_model.predict(embedding)
            data_entries.append(DataEntry(column_name=class_property.name, entry=prediction[0]))

        return data_entries
    
    def classify(self, classification_option: NPSValue, text: str) -> List[DataEntry]:
        raise NotImplementedError("SVMClassificationModel does not support NPSValue classification.")
    
    def train(self, classification_property: ClassificationProperty, texts: List[str], labels: List[int]):
        """Train SVM model for given classification option."""
        embeddings = self.embedding_model.encode(texts)
        svm_model = make_pipeline(StandardScaler(), SVC(kernel='linear', random_state=42))
        svm_model.fit(embeddings, labels)
        joblib.dump(svm_model, self.cache_dir / f"{classification_property.name}.joblib")
    
class QAHuggingface(LLMBase):
    """Classification model using question answering."""
    def __init__(self,
                persona,
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
        super().__init__(persona=persona,
                            temperature=temperature,
                            top_k=top_k,
                            top_p=top_p,
                            num_predict=num_predict,
                            seed=seed,
                            repeat_penalty=repeat_penalty,
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

def get_model_class(model_class: ClassificationClass) -> ModelBase:
    """Get model class based on classification class."""
    if model_class not in _MODEL_CLASSES_MAP:
        raise ValueError(f"Unsupported model class: {model_class}")
    return _MODEL_CLASSES_MAP[model_class]