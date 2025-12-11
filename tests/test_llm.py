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