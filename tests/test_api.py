import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from api.main import app, user_preferences_db # Import the FastAPI app instance and the in-memory db
from api.models import UserPreferences, ArticleRecommendation, RecommendationResponse
from configuration.config import settings # To get the API key for testing

# Fixture to create a TestClient instance for the tests
@pytest.fixture(scope="module")
def client():
    """Create a TestClient instance for the FastAPI app."""
    with TestClient(app) as c:
        yield c

# Fixture for providing the valid API key
@pytest.fixture(scope="module")
def api_key_headers():
    """Return headers containing the valid API key."""
    return {"X-API-Key": settings.API_KEY}

# --- Basic API Tests ---

def test_read_root(client):
    """Test the root endpoint '/'."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the AI News Recommendation Agent API"}

# --- Tests for /api/preferences Endpoint ---

def test_receive_preferences_success(client, api_key_headers):
    """Test successful submission of user preferences."""
    user_prefs = {
        "user_id": "testuser123",
        "topics": ["technology", "finance"],
        "keywords": ["AI", "blockchain"],
        "sources": ["techcrunch", "wsj"],
        "language": "en"
    }
    response = client.post("/api/preferences", headers=api_key_headers, json=user_prefs)
    assert response.status_code == 201
    assert response.json() == {"message": "Preferences received for user testuser123"}
    # Optionally, check if prefs were stored in the in-memory db (requires access or modification)
    # from api.main import user_preferences_db
    # assert "testuser123" in user_preferences_db
    # assert user_preferences_db["testuser123"].dict(exclude_none=True) == user_prefs

def test_receive_preferences_no_api_key(client):
    """Test submitting preferences without an API key."""
    user_prefs = {"user_id": "testuser_no_key"}
    response = client.post("/api/preferences", json=user_prefs) # No headers
    assert response.status_code == 401
    assert "API Key required" in response.json()["detail"]

def test_receive_preferences_invalid_api_key(client):
    """Test submitting preferences with an invalid API key."""
    user_prefs = {"user_id": "testuser_invalid_key"}
    invalid_headers = {"X-API-Key": "invalid-key-123"}
    response = client.post("/api/preferences", headers=invalid_headers, json=user_prefs)
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["detail"]

def test_receive_preferences_invalid_data(client, api_key_headers):
    """Test submitting preferences with invalid data (missing user_id)."""
    invalid_prefs = {
        # Missing user_id which is required by UserPreferences model
        "topics": ["sports"]
    }
    response = client.post("/api/preferences", headers=api_key_headers, json=invalid_prefs)
    assert response.status_code == 422 # Unprocessable Entity for validation errors

# --- Tests for /api/recommendations Endpoint ---

# Sample data for mocking
MOCK_USER_ID = "testuser_rec"
MOCK_PREFERENCES = UserPreferences(
    user_id=MOCK_USER_ID,
    topics=["business"],
    keywords=["startup funding"],
    language="en"
)
MOCK_QUERY_PARAMS = {"q": "startup funding", "language": "en", "category": "business"}
MOCK_FETCHED_ARTICLES = [
    {'title': 'Article 1', 'url': 'http://ex.com/1', 'content': 'Content 1', 'source': {'name': 'Source A'}},
    {'title': 'Article 2', 'url': 'http://ex.com/2', 'content': 'Content 2', 'source': {'name': 'Source B'}}
]
MOCK_ANALYZED_ARTICLES = [
    {'title': 'Article 1', 'url': 'http://ex.com/1', 'content': 'Content 1', 'source': {'name': 'Source A'}, 'summary': 'S1', 'keywords': ['k1'], 'sentiment': 'positive', 'category': 'business'},
    {'title': 'Article 2', 'url': 'http://ex.com/2', 'content': 'Content 2', 'source': {'name': 'Source B'}, 'summary': 'S2', 'keywords': ['k2'], 'sentiment': 'neutral', 'category': 'business'}
]
MOCK_RANKED_ARTICLES = MOCK_ANALYZED_ARTICLES # Assume engine just passes through in this mock
MOCK_FORMATTED_RECOMMENDATIONS = [
    ArticleRecommendation(title='Article 1', url='http://ex.com/1', source='Source A', summary='S1', keywords=['k1'], sentiment='positive', category='business', relevance_score=5.0),
    ArticleRecommendation(title='Article 2', url='http://ex.com/2', source='Source B', summary='S2', keywords=['k2'], sentiment='neutral', category='business', relevance_score=4.0)
]

@pytest.fixture(autouse=True)
def setup_test_db():
    """Clear and setup the in-memory DB for each test."""
    user_preferences_db.clear()
    user_preferences_db[MOCK_USER_ID] = MOCK_PREFERENCES
    yield # Run the test
    user_preferences_db.clear() # Clean up after test

# Use patch to mock dependencies within the endpoint's scope
@patch('api.main.PreferenceProcessor')
@patch('api.main.NewsApiClient')
@patch('api.main.LlmAnalyzer')
@patch('api.main.RecommendationEngine')
@patch('api.main.ResponseFormatter')
def test_get_recommendations_success(
    MockResponseFormatter, MockRecommendationEngine, MockLlmAnalyzer,
    MockNewsApiClient, MockPreferenceProcessor, client, api_key_headers
):
    """Test successful retrieval of recommendations with mocking."""
    # Configure mock instances and their return values
    mock_processor_instance = MockPreferenceProcessor.return_value
    mock_processor_instance.transform_for_fetching.return_value = MOCK_QUERY_PARAMS

    mock_news_client_instance = MockNewsApiClient.return_value
    mock_news_client_instance.fetch_articles.return_value = MOCK_FETCHED_ARTICLES

    mock_analyzer_instance = MockLlmAnalyzer.return_value
    # Simulate analysis by returning pre-defined analyzed articles
    # We mock the methods called inside the loop in main.py
    mock_analyzer_instance.client = True # Simulate client is available
    mock_analyzer_instance.generate_summary.side_effect = ['S1', 'S2']
    mock_analyzer_instance.extract_keywords.side_effect = [['k1'], ['k2']]
    mock_analyzer_instance.analyze_sentiment.side_effect = ['positive', 'neutral']
    mock_analyzer_instance.categorize_article.side_effect = ['business', 'business']

    mock_engine_instance = MockRecommendationEngine.return_value
    # Add relevance scores during mock ranking
    ranked_with_scores = [
        {**MOCK_ANALYZED_ARTICLES[0], 'relevance_score': 5.0},
        {**MOCK_ANALYZED_ARTICLES[1], 'relevance_score': 4.0}
    ]
    mock_engine_instance.generate_recommendations.return_value = ranked_with_scores

    mock_formatter_instance = MockResponseFormatter.return_value
    mock_formatter_instance.format_recommendation_list.return_value = MOCK_FORMATTED_RECOMMENDATIONS

    # Make the API call
    response = client.get(f"/api/recommendations?user_id={MOCK_USER_ID}", headers=api_key_headers)

    # Assertions
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["user_id"] == MOCK_USER_ID
    assert len(response_data["recommendations"]) == 2
    assert response_data["recommendations"][0]["title"] == "Article 1"
    assert response_data["recommendations"][1]["title"] == "Article 2"
    assert response_data["recommendations"][0]["summary"] == "S1" # Check formatted data

    # Check that mocks were called correctly
    mock_processor_instance.transform_for_fetching.assert_called_once_with(MOCK_PREFERENCES)
    mock_news_client_instance.fetch_articles.assert_called_once_with(MOCK_QUERY_PARAMS)
    assert mock_analyzer_instance.generate_summary.call_count == 2
    mock_engine_instance.generate_recommendations.assert_called_once()
    # Check args passed to engine (analyzed articles, preferences)
    engine_call_args = mock_engine_instance.generate_recommendations.call_args[1] # kwargs
    assert len(engine_call_args['articles']) == 2
    assert engine_call_args['articles'][0]['summary'] == 'S1' # Verify analyzed data passed
    assert engine_call_args['preferences'] == MOCK_PREFERENCES
    mock_formatter_instance.format_recommendation_list.assert_called_once_with(ranked_with_scores)


def test_get_recommendations_user_not_found(client, api_key_headers):
    """Test getting recommendations for a user_id with no stored preferences."""
    response = client.get("/api/recommendations?user_id=nonexistent_user", headers=api_key_headers)
    assert response.status_code == 404
    assert "Preferences not found" in response.json()["detail"]

def test_get_recommendations_no_api_key(client):
    """Test getting recommendations without providing an API key."""
    response = client.get(f"/api/recommendations?user_id={MOCK_USER_ID}") # No headers
    assert response.status_code == 401
    assert "API Key required" in response.json()["detail"]

def test_get_recommendations_invalid_api_key(client):
    """Test getting recommendations with an invalid API key."""
    invalid_headers = {"X-API-Key": "invalid-key-456"}
    response = client.get(f"/api/recommendations?user_id={MOCK_USER_ID}", headers=invalid_headers)
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["detail"]

# Add test for case where NewsAPI fetch fails (returns None)
@patch('api.main.PreferenceProcessor')
@patch('api.main.NewsApiClient')
def test_get_recommendations_news_fetch_fails(
    MockNewsApiClient, MockPreferenceProcessor, client, api_key_headers
):
    """Test scenario where news fetching returns None."""
    mock_processor_instance = MockPreferenceProcessor.return_value
    mock_processor_instance.transform_for_fetching.return_value = MOCK_QUERY_PARAMS

    mock_news_client_instance = MockNewsApiClient.return_value
    mock_news_client_instance.fetch_articles.return_value = None # Simulate fetch failure

    response = client.get(f"/api/recommendations?user_id={MOCK_USER_ID}", headers=api_key_headers)

    assert response.status_code == 200 # Should return success but empty list
    response_data = response.json()
    assert response_data["user_id"] == MOCK_USER_ID
    assert response_data["recommendations"] == [] # Expect empty list

    mock_news_client_instance.fetch_articles.assert_called_once()

# Add test for case where LLM Analyzer client is not available
@patch('api.main.PreferenceProcessor')
@patch('api.main.NewsApiClient')
@patch('api.main.LlmAnalyzer')
@patch('api.main.RecommendationEngine')
@patch('api.main.ResponseFormatter')
def test_get_recommendations_llm_analyzer_unavailable(
    MockResponseFormatter, MockRecommendationEngine, MockLlmAnalyzer,
    MockNewsApiClient, MockPreferenceProcessor, client, api_key_headers
):
    """Test scenario where LLM Analyzer client is unavailable."""
    mock_processor_instance = MockPreferenceProcessor.return_value
    mock_processor_instance.transform_for_fetching.return_value = MOCK_QUERY_PARAMS

    mock_news_client_instance = MockNewsApiClient.return_value
    mock_news_client_instance.fetch_articles.return_value = MOCK_FETCHED_ARTICLES

    mock_analyzer_instance = MockLlmAnalyzer.return_value
    mock_analyzer_instance.client = None # Simulate client unavailable

    # Mocks for downstream components
    mock_engine_instance = MockRecommendationEngine.return_value
    # Engine should receive raw fetched articles if analysis skipped
    ranked_raw_with_scores = [
        {**MOCK_FETCHED_ARTICLES[0], 'relevance_score': 3.0},
        {**MOCK_FETCHED_ARTICLES[1], 'relevance_score': 2.5}
    ]
    mock_engine_instance.generate_recommendations.return_value = ranked_raw_with_scores

    mock_formatter_instance = MockResponseFormatter.return_value
    # Formatter receives articles without analysis fields
    formatted_raw = [
        ArticleRecommendation(title='Article 1', url='http://ex.com/1', source='Source A', relevance_score=3.0),
        ArticleRecommendation(title='Article 2', url='http://ex.com/2', source='Source B', relevance_score=2.5)
    ]
    mock_formatter_instance.format_recommendation_list.return_value = formatted_raw

    response = client.get(f"/api/recommendations?user_id={MOCK_USER_ID}", headers=api_key_headers)

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["recommendations"]) == 2
    # Check that analysis fields are missing/None
    assert response_data["recommendations"][0]["summary"] is None
    assert response_data["recommendations"][0]["keywords"] is None

    # Verify analysis methods were NOT called
    assert mock_analyzer_instance.generate_summary.call_count == 0
    # Verify engine received raw articles
    engine_call_args = mock_engine_instance.generate_recommendations.call_args[1]
    assert len(engine_call_args['articles']) == 2
    assert 'summary' not in engine_call_args['articles'][0] # Check raw data passed
