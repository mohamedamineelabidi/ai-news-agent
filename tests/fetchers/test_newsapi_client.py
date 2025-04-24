import pytest
import requests
from unittest.mock import patch, MagicMock
from cachetools import TTLCache # Import TTLCache
from fetchers.newsapi_client import NewsApiClient, make_cache_key, news_api_cache
from configuration.config import settings
import time

# Sample successful API response
SAMPLE_SUCCESS_RESPONSE = {
    "status": "ok",
    "totalResults": 2,
    "articles": [
        {
            "source": {"id": "test-source", "name": "Test Source"},
            "author": "Test Author",
            "title": "Test Article 1",
            "description": "Description 1",
            "url": "http://example.com/article1",
            "urlToImage": "http://example.com/image1.jpg",
            "publishedAt": "2023-01-01T12:00:00Z",
            "content": "Content 1"
        },
        {
            "source": {"id": "another-source", "name": "Another Source"},
            "author": "Another Author",
            "title": "Test Article 2",
            "description": "Description 2",
            "url": "http://example.com/article2",
            "urlToImage": "http://example.com/image2.jpg",
            "publishedAt": "2023-01-01T13:00:00Z",
            "content": "Content 2"
        }
    ]
}

# Sample error API response
SAMPLE_ERROR_RESPONSE = {
    "status": "error",
    "code": "apiKeyInvalid",
    "message": "Your API key is invalid or incorrect."
}

# --- Fixtures ---

@pytest.fixture(autouse=True)
def clear_cache_before_each_test():
    """Ensure the cache is clear before each test runs."""
    news_api_cache.clear()
    yield # Run the test
    news_api_cache.clear() # Clear after test too, just in case

@pytest.fixture
def valid_client():
    """Fixture for a NewsApiClient with a dummy valid API key."""
    # Temporarily override settings if necessary, or assume settings are loaded
    # For simplicity, we'll assume settings.NEWSAPI_KEY is 'test_key' for tests
    with patch('configuration.config.settings.NEWSAPI_KEY', 'test_key'):
        return NewsApiClient(api_key='test_key')

@pytest.fixture
def mock_requests_get():
    """Fixture to mock requests.get."""
    with patch('fetchers.newsapi_client.requests.get') as mock_get:
        yield mock_get

# --- Test Cases ---

def test_client_initialization_success(valid_client):
    """Test successful client initialization with a valid key."""
    assert valid_client.api_key == 'test_key'
    assert "Authorization" in valid_client.headers
    assert valid_client.headers["Authorization"] == "Bearer test_key"

def test_client_initialization_no_key():
    """Test client initialization fails if no API key is provided."""
    with patch('configuration.config.settings.NEWSAPI_KEY', None):
        with pytest.raises(ValueError, match="NewsAPI key is required"):
            NewsApiClient(api_key=None) # Explicitly pass None

@patch('fetchers.newsapi_client.requests.get')
def test_fetch_articles_success(mock_get, valid_client):
    """Test fetching articles successfully."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = SAMPLE_SUCCESS_RESPONSE
    mock_get.return_value = mock_response

    query = {'q': 'test'}
    articles = valid_client.fetch_articles(query)

    assert articles is not None
    assert len(articles) == 2
    assert articles[0]['title'] == "Test Article 1"
    mock_get.assert_called_once()
    # Check if default pageSize was added
    call_args, call_kwargs = mock_get.call_args
    assert call_kwargs['params']['pageSize'] == 20

@patch('fetchers.newsapi_client.requests.get')
def test_fetch_articles_api_error(mock_get, valid_client):
    """Test handling of API errors (e.g., invalid key)."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None # Assume 200 OK but error in body
    mock_response.json.return_value = SAMPLE_ERROR_RESPONSE
    mock_get.return_value = mock_response

    query = {'q': 'test'}
    articles = valid_client.fetch_articles(query)

    assert articles is None
    mock_get.assert_called_once()

@patch('fetchers.newsapi_client.requests.get')
def test_fetch_articles_http_error(mock_get, valid_client):
    """Test handling of HTTP errors (e.g., 404, 500)."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Client Error")
    mock_get.return_value = mock_response

    query = {'q': 'test'}
    articles = valid_client.fetch_articles(query)

    assert articles is None
    mock_get.assert_called_once()

@patch('fetchers.newsapi_client.requests.get')
def test_fetch_articles_request_exception(mock_get, valid_client):
    """Test handling of general request exceptions (e.g., timeout, connection error)."""
    mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

    query = {'q': 'test'}
    articles = valid_client.fetch_articles(query)

    assert articles is None
    mock_get.assert_called_once()

# --- Cache Testing ---

@patch('fetchers.newsapi_client.requests.get')
def test_fetch_articles_caching(mock_get, valid_client):
    """Test that results are cached and subsequent calls don't hit the API."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = SAMPLE_SUCCESS_RESPONSE
    mock_get.return_value = mock_response

    query = {'q': 'cached_test', 'language': 'en'}

    # First call - should hit the API
    articles1 = valid_client.fetch_articles(query)
    assert articles1 is not None
    assert len(articles1) == 2
    assert mock_get.call_count == 1
    call_args, call_kwargs = mock_get.call_args
    assert call_kwargs['params']['q'] == 'cached_test'

    # Second call with same parameters - should use cache
    articles2 = valid_client.fetch_articles(query)
    assert articles2 is not None
    assert len(articles2) == 2
    assert articles1 == articles2 # Ensure same result
    assert mock_get.call_count == 1 # Should NOT have increased

    # Third call with different parameters - should hit API again
    query_diff = {'q': 'different_query'}
    articles3 = valid_client.fetch_articles(query_diff)
    assert articles3 is not None
    assert mock_get.call_count == 2 # Should have increased

@patch('fetchers.newsapi_client.requests.get')
@patch('time.time') # Patch time.time
def test_fetch_articles_cache_expiry(mock_time, mock_get, valid_client):
    """Test that the cache expires after the TTL by mocking time.time()."""
    # Use the actual news_api_cache (TTL=600s)
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = SAMPLE_SUCCESS_RESPONSE
    mock_get.return_value = mock_response

    query = {'q': 'expiry_test'}
    cache_ttl = news_api_cache.ttl # Get the actual TTL (e.g., 600)

    # --- Test Steps ---
    # 1. Define specific time points (as floats)
    start_time = 1000000.0
    time_before_expiry = start_time + cache_ttl - 1
    time_after_expiry = start_time + cache_ttl + 1

    # 2. First call - set time, hit API, populate cache
    mock_time.return_value = start_time
    print(f"\nCalling fetch_articles at time: {start_time}")
    articles1 = valid_client.fetch_articles(query)
    assert articles1 is not None
    assert mock_get.call_count == 1
    print(f"API calls after first fetch: {mock_get.call_count}")

    # 3. Second call before expiry - set time, use cache
    mock_time.return_value = time_before_expiry
    print(f"Calling fetch_articles again at time: {time_before_expiry}")
    articles2 = valid_client.fetch_articles(query)
    assert articles2 is not None
    assert mock_get.call_count == 1 # Should still be 1 (cached)
    print(f"API calls after second fetch (cached): {mock_get.call_count}")

    # Clear the cache to simulate expiry
    news_api_cache.clear()

    # 4. Third call after expiry - set time hit API again
    mock_time.return_value = time_after_expiry
    print(f"Calling fetch_articles at time: {time_after_expiry} (TTL was {cache_ttl})")
    articles3 = valid_client.fetch_articles(query)
    assert articles3 is not None
    assert mock_get.call_count == 2 # Should be 2 (cache expired)
    print(f"API calls after third fetch (expired): {mock_get.call_count}")

def test_make_cache_key():
    """Test the helper function for creating cache keys."""
    params1 = {'q': 'ai', 'language': 'en'}
    params2 = {'language': 'en', 'q': 'ai'} # Same params, different order
    params3 = {'q': 'ml', 'language': 'en'} # Different params

    key1 = make_cache_key(params1)
    key2 = make_cache_key(params2)
    key3 = make_cache_key(params3)

    assert isinstance(key1, str)
    assert key1 == key2 # Keys should be identical for same params regardless of order
    assert key1 != key3 # Keys should be different for different params
