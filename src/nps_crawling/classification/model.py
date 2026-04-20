"""LLMBase abstract class."""
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

from git import List
import joblib
from sentence_transformers import SentenceTransformer
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from ollama import ChatResponse, Client
from pathvalidate import sanitize_filename

class ClassificationClass(Enum, str):
    """Enum for classification classes."""
    HUGGINGFACE = "HuggingFace"
    OLLAMA = "Ollama"
    SVM = "SVM"

class ClassificationProperty():
    """Class for classification properties."""
    def __init__(self, name: str, options: list, description = "", example = ""):
        self.name = name
        self.options = options
        self.description = description
        self.example = example


class ClassificationOptionName(Enum, str):
    """Enum for classification labels."""
    NPS_CATEGORY = "nps_category"
    HAS_NUMERIC_NPS = "has_numeric_nps"
    NPS_VALUE = "nps_value"

class ClassificationOption():

    @abstractmethod
    def get_classification_properties(self) -> List[ClassificationProperty]:
        """Get classification properties."""
        pass

class NPSCategory(ClassificationOption):

    def get_classification_properties(self) -> List[ClassificationProperty]:
        """Get classification properties for NPS category."""
        return [
            ClassificationProperty(
                name="KPI_CURRENT_VALUE",
                options=[0, 1],
                description="Reports a specific NPS value.",
                example="We achieved a Net Promoter Score of 60.",
            ),
            ClassificationProperty(
                name="KPI_TREND",
                options=[0, 1],
                description="Describes change over time (increase, decrease, improvement).",
                example="The Net Promoter Score declined in 2023.",
            ),
            ClassificationProperty(
                name="KPI_HISTORICAL_COMPARISON",
                options=[0, 1],
                description="Explicit comparison to past values (year, quarter, etc.).",
                example="Compared to Q3, our NPS increased by 10%.",
            ),
            ClassificationProperty(
                name="BENCHMARK_COMPARISON_POSITIVE",
                options=[0, 1],
                description="NPS is described as higher than or outperforming competitors, industry, or benchmarks.",
                example="Our NPS is higher than the industry average.",
            ),
            ClassificationProperty(
                name="BENCHMARK_COMPARISON_NEGATIVE",
                options=[0, 1],
                description="NPS is described as lower than or underperforming relative to competitors, industry, or benchmarks.",
                example="Our NPS is below the industry average.",
            ),
            ClassificationProperty(
                name="TARGET_OUTLOOK",
                options=[0, 1],
                description="Future goals, targets, or ambitions related to NPS.",
                example="We aim to improve our NPS to 70 next year.",
            ),
            ClassificationProperty(
                name="NPS_GOAL_REACHED",
                options=[0, 1],
                description="Indicates that the company explicitly states it has met or exceeded a predefined NPS target, goal, or threshold.",
                example="Our annual NPS target was reached.",
            ),
            ClassificationProperty(
                name="MGMT_COMPENSATION_GOVERNANCE",
                options=[0, 1],
                description="NPS linked to compensation, incentives, or governance.",
                example=r"20% of the incentive plan is based on Net Promoter Score.",
            ),
            ClassificationProperty(
                name="CUSTOMER_CASE_EVIDENCE",
                options=[0, 1],
                description="NPS used in customer stories, testimonials, or case examples.",
                example="Our tool helped a retailer boost its NPS by 10 points.",
            ),
            ClassificationProperty(
                name="NPS_SERVICE_PROVIDER",
                options=[0, 1],
                description="Company provides NPS-related services or tools.",
                example="We provide consulting on Net Promoter Score programs.",
            ),
            ClassificationProperty(
                name="METHODOLOGY_DEFINITION",
                options=[0, 1],
                description="Explains what NPS is or how it works.",
                example="NPS measures customer loyalty.",
            )
        ]
        

class ModelBase(ABC):
    """LLM Base abstract class."""
    @abstractmethod
    def __init__(self,
                 persona,
                 model,
            )
        ]
        

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
    def classify(self, text):
        """Base abstract classify function."""
        pass

class LLMHuggingFace(ModelBase):
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

    def classify(self, text):
        """Classify given text."""
        messages = [
            {"role": "system", "content": self.persona},
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
        response = generated[len(prompt):].strip()
        return response

class LLMOllama(ModelBase):
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

    def classify(self, text):
        """Classify given text."""
        client = Client(host=f"{self.host}:{self.port}")

        response: ChatResponse = client.chat(
            model=self.model,
            messages=[
                {'role': 'system', 'content': self.persona},
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

        SVM_CACHE_DIR = BASE_DIR / "cache" / "svm_pipeline.joblib"
        if not SVM_CACHE_DIR.exists():
            raise FileNotFoundError(
                f"SVM model cache file not found at {SVM_CACHE_DIR}. "
                "Please ensure the model is trained and saved correctly.",
            )

        self.svm_model = joblib.load(SVM_CACHE_DIR)

        LABEL_ENCODER_CACHE_DIR = BASE_DIR / "cache" / "label_encoder.joblib"
        if not LABEL_ENCODER_CACHE_DIR.exists():
            raise FileNotFoundError(
                f"Label encoder cache file not found at {LABEL_ENCODER_CACHE_DIR}. "
                "Please ensure the label encoder is saved correctly.",
            )

        self.label_encoder = joblib.load(LABEL_ENCODER_CACHE_DIR)

    def classify(self, text: str) -> str:
        embedding = self.embedding_model.encode([text])
        prediction = self.svm_model.predict(embedding)
        prediction_label = self.label_encoder.inverse_transform(prediction)
        return prediction_label[0]

_MODEL_CLASSES_MAP = {
    ClassificationClass.HUGGINGFACE: LLMHuggingFace,
    ClassificationClass.OLLAMA: LLMOllama,
    ClassificationClass.SVM: SVMClassificationModel,
}

def get_model_class(model_class: ClassificationClass) -> ModelBase:
    """Get model class based on classification class."""
    if model_class not in _MODEL_CLASSES_MAP:
        raise ValueError(f"Unsupported model class: {model_class}")
    return _MODEL_CLASSES_MAP[model_class]