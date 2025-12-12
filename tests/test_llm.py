"""Tests for the LLMOllama class and LLM."""

from unittest.mock import patch

import pytest

from nps_crawling.llm.llm_ollama import LLMOllama


@pytest.fixture
def mock_client():
    """Create a mock Ollama client."""
    with patch('nps_crawling.llm.llm_ollama.Client') as mock:
        yield mock


@pytest.fixture
def llm_instance() -> LLMOllama:
    """Create an LLMOllama instance with default parameters."""
    return LLMOllama(
        persona="You are a helpful assistant.",
        model='mistral',
        host='localhost',
        port=14000,
    )


def utils_create_deterministic_llm(persona: str) -> LLMOllama:
    """Utility function to create a deterministic LLMOllama instance."""
    return LLMOllama(
        persona=persona,
        temperature=0.0,
        top_k=1,
        seed=42,
        model='mistral',
        host='localhost',
        port=14000,
    )


def utils_create_nondeterministic_llm(persona: str) -> LLMOllama:
    """Utility function to create a non-deterministic LLMOllama instance."""
    return LLMOllama(
        persona=persona,
        temperature=0.7,
        top_k=40,
        seed=123,
        model='mistral',
        host='localhost',
        port=14000,
    )


class TestLLMOllamaInit:
    """Tests for LLMOllama initialization."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        llm = LLMOllama(persona="Test persona")

        assert llm.persona == "Test persona"
        assert llm.options['temperature'] == 0.0
        assert llm.options['top_p'] == 1.0
        assert llm.options['top_k'] == 1
        assert llm.options['num_predict'] == 128
        assert llm.options['seed'] == 42
        assert llm.options['repeat_penalty'] == 1.0
        assert llm.model == 'mistral'
        assert llm.host == 'localhost'
        assert llm.port == 14000

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        llm = LLMOllama(
            persona="Custom persona",
            temperature=0.7,
            top_p=0.9,
            top_k=50,
            num_predict=256,
            seed=123,
            repeat_penalty=1.1,
            model='llama2',
            host='192.168.1.1',
            port=11434,
        )

        assert llm.persona == "Custom persona"
        assert llm.options['temperature'] == 0.7
        assert llm.options['top_p'] == 0.9
        assert llm.options['top_k'] == 50
        assert llm.options['num_predict'] == 256
        assert llm.options['seed'] == 123
        assert llm.options['repeat_penalty'] == 1.1
        assert llm.model == 'llama2'
        assert llm.host == '192.168.1.1'
        assert llm.port == 11434

    def test_init_with_kwargs(self):
        """Test initialization with additional kwargs."""
        llm = LLMOllama(
            persona="Test persona",
            custom_param="custom_value",
        )

        assert llm.persona == "Test persona"
        # kwargs should be passed to parent class


class TestLLM:
    """Tests for LLM functionality."""
    def test_deterministic_same_seed_direct(self):
        """Test that deterministic LLM produces same output for same input."""
        prompt = "Classify: This is a test."

        llm = utils_create_deterministic_llm(persona="You are a classifier.")

        result1 = llm.classify(prompt)
        result2 = llm.classify(prompt)

        assert result1 == result2

    def test_non_deterministic_diff_seed(self):
        """Test that non-deterministic LLM produces different outputs for same input."""
        prompt = "Classify: This is a test."

        llm = utils_create_nondeterministic_llm(persona="You are a classifier.")

        result1 = llm.classify(prompt)
        result2 = llm.classify(prompt)

        assert result1 != result2

    def test_multiple_class_consistent_direct(self):
        """Test that multiple classifications are consistent for deterministic LLM."""
        prompt = "Translate to French: This is a test."

        llm = utils_create_deterministic_llm(persona="You are a translator and must translate text to French.")

        SAMPLE_COUNT = 5

        outputs = [llm.classify(prompt) for _ in range(SAMPLE_COUNT)]

        assert len(set(outputs)) == 1

    def test_classification(self):
        """Test classification functionality."""
        persona = """You are a classifier and must classify the given text into one of the following categories:
        Positive, Negative, Neutral.
        You are only allowed to respond with one of these categories and nothing else."""

        llm = utils_create_deterministic_llm(persona=persona)

        text_positive = "I love programming!"
        text_negative = "I hate bugs!"
        text_neutral = "Programming is a skill."

        result_positive = llm.classify(text_positive)
        result_negative = llm.classify(text_negative)
        result_neutral = llm.classify(text_neutral)

        assert result_positive == "Positive"
        assert result_negative == "Negative"
        assert result_neutral == "Neutral"

    def test_classification_determinism(self):
        """Test that deterministic LLM produces consistent classifications."""
        SAMPLE_COUNT = 5
        persona = """You are a classifier and must classify the given text into one of the following categories:
        Positive, Negative, Neutral.
        You are only allowed to respond with one of these categories and nothing else."""

        llm = utils_create_deterministic_llm(persona=persona)

        text_positive = "I love programming!"
        text_negative = "I hate bugs!"
        text_neutral = "Programming is a skill."

        results_positive = [llm.classify(text_positive) for _ in range(SAMPLE_COUNT)]
        results_negative = [llm.classify(text_negative) for _ in range(SAMPLE_COUNT)]
        results_neutral = [llm.classify(text_neutral) for _ in range(SAMPLE_COUNT)]

        assert len(set(results_positive)) == 1
        assert len(set(results_negative)) == 1
        assert len(set(results_neutral)) == 1

    def test_classification_non_determinism(self):
        """Test that non-deterministic LLM produces varied classifications."""
        SAMPLE_COUNT = 5
        persona = """You are a classifier and must classify the given text into one of the following categories:
        Positive, Negative, Neutral.
        You are only allowed to respond with one of these categories and nothing else."""

        llm = utils_create_nondeterministic_llm(persona=persona)

        text_positive = "I love programming!"
        text_negative = "I hate bugs!"
        text_neutral = "Programming is a skill."

        results_positive = [llm.classify(text_positive) for _ in range(SAMPLE_COUNT)]
        results_negative = [llm.classify(text_negative) for _ in range(SAMPLE_COUNT)]
        results_neutral = [llm.classify(text_neutral) for _ in range(SAMPLE_COUNT)]

        assert len(set(results_positive)) > 1
        assert len(set(results_negative)) > 1
        assert len(set(results_neutral)) > 1
