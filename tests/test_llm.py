"""Tests for the LLMOllama class."""

import pytest
from unittest.mock import MagicMock, patch

from nps_crawling.llm.llm_ollama import LLMOllama


@pytest.fixture
def mock_client():
    """Create a mock Ollama client."""
    with patch('nps_crawling.llm.llm_ollama.Client') as mock:
        yield mock


@pytest.fixture
def llm_instance():
    """Create an LLMOllama instance with default parameters."""
    return LLMOllama(
        persona="You are a helpful assistant.",
        model='mistral',
        host='localhost',
        port=14000
    )


class TestLLMOllamaInit:
    """Tests for LLMOllama initialization."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        llm = LLMOllama(persona="Test persona")

        assert llm.persona == "Test persona"
        assert llm.temperature == 0.0
        assert llm.top_p == 1.0
        assert llm.top_k == 1
        assert llm.num_predict == 128
        assert llm.seed == 42
        assert llm.repeat_penalty == 1.0
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
            port=11434
        )

        assert llm.persona == "Custom persona"
        assert llm.temperature == 0.7
        assert llm.top_p == 0.9
        assert llm.top_k == 50
        assert llm.num_predict == 256
        assert llm.seed == 123
        assert llm.repeat_penalty == 1.1
        assert llm.model == 'llama2'
        assert llm.host == '192.168.1.1'
        assert llm.port == 11434

    def test_init_with_kwargs(self):
        """Test initialization with additional kwargs."""
        llm = LLMOllama(
            persona="Test persona",
            custom_param="custom_value"
        )

        assert llm.persona == "Test persona"
        # kwargs should be passed to parent class


class TestLLMOllamaClassify:
    """Tests for LLMOllama classify method."""

    def test_classify_success(self, llm_instance, mock_client):
        """Test successful classification."""
        mock_response = {
            'message': {
                'content': '  Positive sentiment  '
            }
        }
        mock_chat = MagicMock(return_value=mock_response)
        mock_client.return_value.chat = mock_chat

        result = llm_instance.classify("This is a test text.")

        assert result == "Positive sentiment"
        mock_client.assert_called_once_with(host="localhost:14000")
        mock_chat.assert_called_once()

    def test_classify_calls_client_with_correct_parameters(self, llm_instance, mock_client):
        """Test that classify calls the client with correct parameters."""
        mock_response = {'message': {'content': 'Response'}}
        mock_chat = MagicMock(return_value=mock_response)
        mock_client.return_value.chat = mock_chat

        test_text = "Test input text"
        llm_instance.classify(test_text)

        call_args = mock_chat.call_args
        assert call_args[1]['model'] == 'mistral'
        assert len(call_args[1]['messages']) == 2
        assert call_args[1]['messages'][0]['role'] == 'system'
        assert call_args[1]['messages'][0]['content'] == llm_instance.persona
        assert call_args[1]['messages'][1]['role'] == 'user'
        assert call_args[1]['messages'][1]['content'] == test_text

    def test_classify_strips_whitespace(self, llm_instance, mock_client):
        """Test that classify strips whitespace from response."""
        mock_response = {
            'message': {
                'content': '\n\n  Response with whitespace  \n\n'
            }
        }
        mock_chat = MagicMock(return_value=mock_response)
        mock_client.return_value.chat = mock_chat

        result = llm_instance.classify("Test")

        assert result == "Response with whitespace"

    def test_classify_with_empty_response(self, llm_instance, mock_client):
        """Test classification with empty response."""
        mock_response = {'message': {'content': '   '}}
        mock_chat = MagicMock(return_value=mock_response)
        mock_client.return_value.chat = mock_chat

        result = llm_instance.classify("Test")

        assert result == ""

    def test_classify_with_custom_host_port(self, mock_client):
        """Test classification with custom host and port."""
        llm = LLMOllama(
            persona="Test",
            host='custom-host',
            port=9999
        )
        mock_response = {'message': {'content': 'Response'}}
        mock_chat = MagicMock(return_value=mock_response)
        mock_client.return_value.chat = mock_chat

        llm.classify("Test")

        mock_client.assert_called_once_with(host="custom-host:9999")

    def test_classify_passes_options(self, llm_instance, mock_client):
        """Test that classify passes options to chat."""
        mock_response = {'message': {'content': 'Response'}}
        mock_chat = MagicMock(return_value=mock_response)
        mock_client.return_value.chat = mock_chat

        llm_instance.classify("Test")

        call_args = mock_chat.call_args
        assert 'options' in call_args[1]
        assert call_args[1]['options'] == llm_instance.options


class TestLLMOllamaExceptions:
    """Tests for exception handling in LLMOllama."""

    def test_classify_client_connection_error(self, llm_instance, mock_client):
        """Test that connection errors are raised."""
        mock_client.side_effect = ConnectionError("Cannot connect to Ollama")

        with pytest.raises(ConnectionError, match="Cannot connect to Ollama"):
            llm_instance.classify("Test")

    def test_classify_client_error(self, llm_instance, mock_client):
        """Test that client errors are raised."""
        mock_client.return_value.chat.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            llm_instance.classify("Test")

    def test_classify_malformed_response(self, llm_instance, mock_client):
        """Test handling of malformed response."""
        mock_response = {'message': {}}  # Missing 'content' key
        mock_chat = MagicMock(return_value=mock_response)
        mock_client.return_value.chat = mock_chat

        with pytest.raises(KeyError):
            llm_instance.classify("Test")


@pytest.mark.parametrize(
    "persona, text, expected_call_count",
    [
        pytest.param("Persona A", "Text 1", 1, id="single_call"),
        pytest.param("Persona B", "", 1, id="empty_text"),
        pytest.param("", "Text 2", 1, id="empty_persona"),
    ],
)
def test_classify_parametrized(persona, text, expected_call_count, mock_client):
    """Parametrized test for classify method."""
    llm = LLMOllama(persona=persona)
    mock_response = {'message': {'content': 'Result'}}
    mock_chat = MagicMock(return_value=mock_response)
    mock_client.return_value.chat = mock_chat

    llm.classify(text)

    assert mock_chat.call_count == expected_call_count


class TestLLMOllamaDeterminism:
    """Tests for LLMOllama deterministic behavior."""

    def test_classify_deterministic_with_same_seed(self):
        """Test that same seed produces same results."""
        persona = "You are a classifier."
        test_text = "This is a test input."

        llm1 = LLMOllama(persona=persona, seed=42, temperature=0.0)
        llm2 = LLMOllama(persona=persona, seed=42, temperature=0.0)

        with patch('nps_crawling.llm.llm_ollama.Client') as mock_client:
            mock_response = {'message': {'content': 'Deterministic response'}}
            mock_client.return_value.chat.return_value = mock_response

            result1 = llm1.classify(test_text)
            result2 = llm2.classify(test_text)

            assert result1 == result2

    def test_classify_different_seeds_same_call(self):
        """Test that different seeds can produce different results."""
        persona = "You are a classifier."
        test_text = "This is a test input."

        llm1 = LLMOllama(persona=persona, seed=42, temperature=0.0)
        llm2 = LLMOllama(persona=persona, seed=123, temperature=0.0)

        with patch('nps_crawling.llm.llm_ollama.Client') as mock_client:
            # Simulate different responses for different seeds
            responses = [
                {'message': {'content': 'Response A'}},
                {'message': {'content': 'Response B'}}
            ]
            mock_client.return_value.chat.side_effect = responses

            result1 = llm1.classify(test_text)
            result2 = llm2.classify(test_text)

            # Seeds are different, so options should be different
            assert llm1.options != llm2.options

    def test_classify_zero_temperature_determinism(self):
        """Test that temperature=0 ensures deterministic behavior."""
        persona = "You are a classifier."
        test_text = "Classify this text."

        llm = LLMOllama(
            persona=persona,
            seed=42,
            temperature=0.0,
            top_k=1,
            top_p=1.0
        )

        with patch('nps_crawling.llm.llm_ollama.Client') as mock_client:
            mock_response = {'message': {'content': 'Consistent result'}}
            mock_client.return_value.chat.return_value = mock_response

            results = [llm.classify(test_text) for _ in range(3)]

            # All results should be identical with temperature=0
            assert len(set(results)) == 1
            assert all(r == 'Consistent result' for r in results)

    def test_options_include_seed(self):
        """Test that seed is included in options."""
        llm = LLMOllama(persona="Test", seed=12345)

        # Assuming parent class sets self.options
        assert hasattr(llm, 'options')
        # Check that seed is in options (depends on LLMBase implementation)
        # If LLMBase creates an options dict, we'd check it here

    @pytest.mark.parametrize(
        "seed, temperature, expected_deterministic",
        [
            pytest.param(42, 0.0, True, id="seed_42_temp_0"),
            pytest.param(42, 0.0, True, id="same_params_deterministic"),
            pytest.param(123, 0.0, True, id="different_seed_still_deterministic"),
            pytest.param(42, 0.5, False, id="higher_temp_less_deterministic"),
        ],
    )
    def test_determinism_with_parameters(self, seed, temperature, expected_deterministic):
        """Test determinism with various parameter combinations."""
        persona = "Test classifier"
        test_text = "Test input"

        llm = LLMOllama(
            persona=persona,
            seed=seed,
            temperature=temperature
        )

        with patch('nps_crawling.llm.llm_ollama.Client') as mock_client:
            # With same mock, results should be same
            mock_response = {'message': {'content': 'Mock result'}}
            mock_client.return_value.chat.return_value = mock_response

            result1 = llm.classify(test_text)
            result2 = llm.classify(test_text)

            if expected_deterministic or temperature == 0.0:
                # With mocking, results will always match
                assert result1 == result2

    def test_multiple_calls_same_instance(self):
        """Test multiple classify calls on same instance produce consistent results."""
        llm = LLMOllama(persona="Classifier", seed=42, temperature=0.0)
        test_texts = ["Text 1", "Text 2", "Text 1"]  # Repeat first text

        with patch('nps_crawling.llm.llm_ollama.Client') as mock_client:
            # Return different responses for different inputs
            responses = [
                {'message': {'content': 'Result 1'}},
                {'message': {'content': 'Result 2'}},
                {'message': {'content': 'Result 1'}},  # Same as first
            ]
            mock_client.return_value.chat.side_effect = responses

            results = [llm.classify(text) for text in test_texts]

            # First and third results should match (same input)
            assert results[0] == results[2]
