import pytest
from unittest.mock import patch, MagicMock, ANY
from analysis.llm_analyzer import LlmAnalyzer, llm_analysis_cache, generate_cache_key
from configuration.config import settings
from openai import OpenAIError
import time

# Sample text for testing
SAMPLE_TEXT = "This is a test news article about AI advancements."

# --- Fixtures ---

@pytest.fixture(autouse=True)
def clear_llm_cache():
    """Ensure the LLM analysis cache is clear before each test."""
    llm_analysis_cache.clear()
    yield
    llm_analysis_cache.clear()

@pytest.fixture
def mock_openai_client():
    """Fixture to mock the OpenAI client instance and its methods."""
    with patch('analysis.llm_analyzer.OpenAI') as mock_constructor:
        mock_instance = MagicMock()
        # Mock the specific method used for chat completions
        mock_instance.chat.completions.create = MagicMock()
        mock_constructor.return_value = mock_instance
        yield mock_instance # Yield the mocked client instance

@pytest.fixture
def analyzer_with_mock_client(mock_openai_client):
    """Fixture to create an LlmAnalyzer instance with a mocked OpenAI client."""
    # Ensure a dummy key is set for initialization to pass the initial check
    with patch('configuration.config.settings.OPENAI_API_KEY', 'fake_key'):
        analyzer = LlmAnalyzer(api_key='fake_key')
        # Replace the potentially real client with the mock one if initialization logic changes
        analyzer.client = mock_openai_client
        return analyzer

# --- Helper Function ---
def create_mock_openai_response(content: str):
    """Creates a mock OpenAI chat completion response object."""
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    return mock_completion

# --- Test Cases ---

def test_analyzer_initialization_success(mock_openai_client):
    """Test successful analyzer initialization with a valid key."""
    with patch('configuration.config.settings.OPENAI_API_KEY', 'fake_key'):
        analyzer = LlmAnalyzer(api_key='fake_key')
        assert analyzer.client is not None
        # Check if OpenAI constructor was called with the key
        from analysis.llm_analyzer import OpenAI # Import locally to check constructor call
        OpenAI.assert_called_once_with(api_key='fake_key')

def test_analyzer_initialization_no_key():
    """Test analyzer initialization logs warning and sets client to None if no key."""
    with patch('configuration.config.settings.OPENAI_API_KEY', None):
         with patch('analysis.llm_analyzer.logger') as mock_logger:
            analyzer = LlmAnalyzer(api_key=None)
            assert analyzer.client is None
            mock_logger.error.assert_called_with("OpenAI API key is not configured.")
            mock_logger.warning.assert_called_with("LlmAnalyzer initialized without a valid OpenAI API key. Analysis functions will fail.")

def test_analyzer_initialization_openai_error():
    """Test handling of errors during OpenAI client initialization."""
    with patch('analysis.llm_analyzer.OpenAI', side_effect=Exception("Init failed")):
        with patch('configuration.config.settings.OPENAI_API_KEY', 'fake_key'):
            with patch('analysis.llm_analyzer.logger') as mock_logger:
                analyzer = LlmAnalyzer(api_key='fake_key')
                assert analyzer.client is None
                mock_logger.error.assert_called_with("Failed to initialize OpenAI client: Init failed", exc_info=True)

# --- Test _make_llm_call ---

def test_make_llm_call_success(analyzer_with_mock_client):
    """Test successful internal LLM call."""
    mock_client = analyzer_with_mock_client.client
    mock_client.chat.completions.create.return_value = create_mock_openai_response(" LLM response ")

    result = analyzer_with_mock_client._make_llm_call("test prompt")

    assert result == "LLM response"
    mock_client.chat.completions.create.assert_called_once_with(
        model=ANY, messages=ANY, max_tokens=ANY, temperature=ANY, n=ANY, stop=ANY
    )

def test_make_llm_call_openai_error(analyzer_with_mock_client):
    """Test handling of OpenAIError during LLM call."""
    mock_client = analyzer_with_mock_client.client
    mock_client.chat.completions.create.side_effect = OpenAIError("API Error")

    with patch('analysis.llm_analyzer.logger') as mock_logger:
        result = analyzer_with_mock_client._make_llm_call("test prompt")
        assert result is None
        mock_logger.error.assert_called_with("OpenAI API error: API Error", exc_info=True)

def test_make_llm_call_no_client():
    """Test LLM call fails gracefully if client wasn't initialized."""
    with patch('configuration.config.settings.OPENAI_API_KEY', None):
        analyzer = LlmAnalyzer(api_key=None) # Ensure client is None
        with patch('analysis.llm_analyzer.logger') as mock_logger:
            result = analyzer._make_llm_call("test prompt")
            assert result is None
            mock_logger.error.assert_called_with("OpenAI client not initialized. Cannot make LLM call.")


# --- Test Analysis Functions ---

def test_extract_keywords_success(analyzer_with_mock_client):
    """Test successful keyword extraction."""
    mock_client = analyzer_with_mock_client.client
    mock_client.chat.completions.create.return_value = create_mock_openai_response("ai, advancements, test")

    keywords = analyzer_with_mock_client.extract_keywords(SAMPLE_TEXT)

    assert keywords == ["ai", "advancements", "test"]
    mock_client.chat.completions.create.assert_called_once()
    # Check prompt includes the text
    call_args, call_kwargs = mock_client.chat.completions.create.call_args
    assert SAMPLE_TEXT in call_kwargs['messages'][1]['content']

def test_extract_keywords_empty_response(analyzer_with_mock_client):
    """Test keyword extraction with empty LLM response."""
    mock_client = analyzer_with_mock_client.client
    mock_client.chat.completions.create.return_value = create_mock_openai_response("  ") # Empty/whitespace

    keywords = analyzer_with_mock_client.extract_keywords(SAMPLE_TEXT)
    assert keywords == [] # Should return empty list, not None

def test_generate_summary_success(analyzer_with_mock_client):
    """Test successful summary generation."""
    mock_client = analyzer_with_mock_client.client
    summary_text = "This is a summary."
    mock_client.chat.completions.create.return_value = create_mock_openai_response(summary_text)

    summary = analyzer_with_mock_client.generate_summary(SAMPLE_TEXT)
    assert summary == summary_text
    mock_client.chat.completions.create.assert_called_once()

def test_analyze_sentiment_success(analyzer_with_mock_client):
    """Test successful sentiment analysis."""
    mock_client = analyzer_with_mock_client.client
    mock_client.chat.completions.create.return_value = create_mock_openai_response(" positive ")

    sentiment = analyzer_with_mock_client.analyze_sentiment(SAMPLE_TEXT)
    assert sentiment == "positive"
    mock_client.chat.completions.create.assert_called_once()

def test_analyze_sentiment_invalid_response(analyzer_with_mock_client):
    """Test sentiment analysis with invalid LLM response."""
    mock_client = analyzer_with_mock_client.client
    mock_client.chat.completions.create.return_value = create_mock_openai_response("mostly okay")

    sentiment = analyzer_with_mock_client.analyze_sentiment(SAMPLE_TEXT)
    assert sentiment is None # Or 'neutral' depending on desired fallback

def test_categorize_article_success(analyzer_with_mock_client):
    """Test successful article categorization."""
    mock_client = analyzer_with_mock_client.client
    mock_client.chat.completions.create.return_value = create_mock_openai_response(" Technology ")

    category = analyzer_with_mock_client.categorize_article(SAMPLE_TEXT)
    assert category == "technology"
    mock_client.chat.completions.create.assert_called_once()

def test_categorize_article_invalid_response(analyzer_with_mock_client):
    """Test categorization with LLM response not in allowed categories."""
    mock_client = analyzer_with_mock_client.client
    mock_client.chat.completions.create.return_value = create_mock_openai_response("Artificial Intelligence")

    category = analyzer_with_mock_client.categorize_article(SAMPLE_TEXT)
    assert category is None # Or 'general' depending on fallback

# --- Test Caching ---

def test_analysis_function_caching(analyzer_with_mock_client):
    """Test that analysis function results are cached."""
    mock_client = analyzer_with_mock_client.client
    mock_client.chat.completions.create.return_value = create_mock_openai_response("positive")

    # First call - should hit LLM
    sentiment1 = analyzer_with_mock_client.analyze_sentiment(SAMPLE_TEXT)
    assert sentiment1 == "positive"
    assert mock_client.chat.completions.create.call_count == 1

    # Second call - should use cache
    sentiment2 = analyzer_with_mock_client.analyze_sentiment(SAMPLE_TEXT)
    assert sentiment2 == "positive"
    assert mock_client.chat.completions.create.call_count == 1 # No increase

    # Call a different function - should hit LLM again
    mock_client.chat.completions.create.return_value = create_mock_openai_response("tech") # For keywords
    analyzer_with_mock_client.extract_keywords(SAMPLE_TEXT)
    assert mock_client.chat.completions.create.call_count == 2 # Increased

def test_analysis_cache_key_generation():
    """Test the cache key generation function."""
    key1 = generate_cache_key("func1", "text a")
    key2 = generate_cache_key("func1", "text a")
    key3 = generate_cache_key("func2", "text a")
    key4 = generate_cache_key("func1", "text b")

    assert key1 == key2
    assert key1 != key3
    assert key1 != key4
