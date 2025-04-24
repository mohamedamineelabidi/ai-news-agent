import pytest
from unittest.mock import patch # Import patch
from responses.formatter import ResponseFormatter
from api.models import ArticleRecommendation

# --- Sample Data ---

SAMPLE_FULL_ARTICLE_DATA = {
    'title': 'Full Article',
    'url': 'http://example.com/full',
    'source': {'id': 'src-1', 'name': 'Source One'},
    'summary': 'This is a summary.',
    'keywords': ['full', 'test', 'data'],
    'sentiment': 'positive',
    'category': 'technology',
    'relevance_score': 4.2,
    'other_field': 'should be ignored' # Extra field
}

SAMPLE_MINIMAL_ARTICLE_DATA = {
    'title': 'Minimal Article',
    'url': 'http://example.com/minimal',
    'source': {'name': 'Source Two'}
    # Missing summary, keywords, sentiment, category, score
}

SAMPLE_ARTICLE_NO_SOURCE_NAME = {
    'title': 'No Source Name',
    'url': 'http://example.com/no-source-name',
    'source': {'id': 'src-3'} # Missing 'name'
}

SAMPLE_ARTICLE_NO_SOURCE_DICT = {
    'title': 'No Source Dict',
    'url': 'http://example.com/no-source-dict',
    'source': None # Source is None
}

SAMPLE_ARTICLE_INVALID_DATA = {
    'title': 'Invalid Data Article',
    'url': 'http://example.com/invalid',
    'relevance_score': 'not-a-float' # Invalid type for score
}

# --- Fixtures ---

@pytest.fixture
def formatter():
    """Pytest fixture to create a ResponseFormatter instance."""
    return ResponseFormatter()

# --- Test Cases ---

# --- Tests for format_single_article ---

def test_format_single_article_full(formatter):
    """Test formatting a single article with all expected fields."""
    formatted = formatter.format_single_article(SAMPLE_FULL_ARTICLE_DATA)

    assert isinstance(formatted, ArticleRecommendation)
    assert formatted.title == 'Full Article'
    assert formatted.url == 'http://example.com/full'
    assert formatted.source == 'Source One'
    assert formatted.summary == 'This is a summary.'
    assert formatted.keywords == ['full', 'test', 'data']
    assert formatted.sentiment == 'positive'
    assert formatted.category == 'technology'
    assert formatted.relevance_score == pytest.approx(4.2)

def test_format_single_article_minimal(formatter):
    """Test formatting an article with only minimal required fields."""
    formatted = formatter.format_single_article(SAMPLE_MINIMAL_ARTICLE_DATA)

    assert isinstance(formatted, ArticleRecommendation)
    assert formatted.title == 'Minimal Article'
    assert formatted.url == 'http://example.com/minimal'
    assert formatted.source == 'Source Two'
    # Optional fields should be None
    assert formatted.summary is None
    assert formatted.keywords is None
    assert formatted.sentiment is None
    assert formatted.category is None
    assert formatted.relevance_score is None

def test_format_single_article_missing_source_name(formatter):
    """Test formatting when the source dictionary is missing the 'name' key."""
    formatted = formatter.format_single_article(SAMPLE_ARTICLE_NO_SOURCE_NAME)
    assert formatted.source == 'N/A' # Default value

def test_format_single_article_missing_source_dict(formatter):
    """Test formatting when the source field itself is missing or None."""
    formatted = formatter.format_single_article(SAMPLE_ARTICLE_NO_SOURCE_DICT)
    assert formatted.source == 'N/A' # Default value

def test_format_single_article_handles_exception(formatter):
    """Test that formatting handles unexpected errors gracefully."""
    # Pydantic validation should catch the type error here
    # We test if our wrapper logs and returns a placeholder
    with patch('responses.formatter.logger') as mock_logger:
        formatted = formatter.format_single_article(SAMPLE_ARTICLE_INVALID_DATA)

        assert isinstance(formatted, ArticleRecommendation)
        assert formatted.title == "Error Formatting Article"
        assert formatted.url == 'http://example.com/invalid'
        assert formatted.source == "N/A"
        assert formatted.summary == "Could not format article details."
        # Check if error was logged
        mock_logger.error.assert_called_once()
        # Check if the log message contains the error details (optional)
        args, kwargs = mock_logger.error.call_args
        assert "Error formatting article data" in args[0]
        assert "not-a-float" in args[0] # Check if problematic data is logged

# --- Tests for format_recommendation_list ---

def test_format_recommendation_list_success(formatter):
    """Test formatting a list of valid article data dictionaries."""
    articles_list = [SAMPLE_FULL_ARTICLE_DATA, SAMPLE_MINIMAL_ARTICLE_DATA]
    formatted_list = formatter.format_recommendation_list(articles_list)

    assert isinstance(formatted_list, list)
    assert len(formatted_list) == 2
    assert all(isinstance(item, ArticleRecommendation) for item in formatted_list)
    # Check titles to ensure order and content
    assert formatted_list[0].title == 'Full Article'
    assert formatted_list[1].title == 'Minimal Article'

def test_format_recommendation_list_with_error(formatter):
    """Test formatting a list containing one article that causes an error."""
    articles_list = [SAMPLE_FULL_ARTICLE_DATA, SAMPLE_ARTICLE_INVALID_DATA, SAMPLE_MINIMAL_ARTICLE_DATA]
    formatted_list = formatter.format_recommendation_list(articles_list)

    assert len(formatted_list) == 3
    assert formatted_list[0].title == 'Full Article'
    assert formatted_list[1].title == 'Error Formatting Article' # The placeholder
    assert formatted_list[2].title == 'Minimal Article'

def test_format_recommendation_list_empty(formatter):
    """Test formatting an empty list."""
    formatted_list = formatter.format_recommendation_list([])
    assert isinstance(formatted_list, list)
    assert len(formatted_list) == 0
