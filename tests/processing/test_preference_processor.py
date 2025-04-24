import pytest
from processing.preference_processor import PreferenceProcessor
from api.models import UserPreferences # Import the model for type hints if needed

# Sample valid preference data
VALID_PREFS_DATA_FULL = {
    "user_id": "test_user_1",
    "topics": ["technology", "business"],
    "keywords": ["AI", "startups"],
    "sources": ["techcrunch", "wired"],
    "language": "en"
}

VALID_PREFS_DATA_MINIMAL = {
    "user_id": "test_user_2"
}

# Sample invalid preference data
INVALID_PREFS_DATA_MISSING_ID = {
    "topics": ["sports"]
}

INVALID_PREFS_DATA_WRONG_TYPE = {
    "user_id": "test_user_3",
    "language": 123 # Should be string
}

@pytest.fixture
def processor():
    """Pytest fixture to create a PreferenceProcessor instance."""
    return PreferenceProcessor()

# --- Tests for parse_and_validate ---

def test_parse_and_validate_valid_full(processor):
    """Test parsing and validation with full, valid data."""
    prefs = processor.parse_and_validate(VALID_PREFS_DATA_FULL)
    assert prefs.user_id == "test_user_1"
    assert prefs.topics == ["technology", "business"]
    assert prefs.keywords == ["AI", "startups"]
    assert prefs.sources == ["techcrunch", "wired"]
    assert prefs.language == "en"

def test_parse_and_validate_valid_minimal(processor):
    """Test parsing and validation with minimal valid data (only user_id)."""
    prefs = processor.parse_and_validate(VALID_PREFS_DATA_MINIMAL)
    assert prefs.user_id == "test_user_2"
    assert prefs.topics is None
    assert prefs.keywords is None
    assert prefs.sources is None
    assert prefs.language == "en" # Default value

def test_parse_and_validate_invalid_missing_id(processor):
    """Test validation fails when user_id is missing."""
    with pytest.raises(ValueError, match="Invalid preference data"):
        processor.parse_and_validate(INVALID_PREFS_DATA_MISSING_ID)

def test_parse_and_validate_invalid_wrong_type(processor):
    """Test validation fails when a field has the wrong type."""
    with pytest.raises(ValueError, match="Invalid preference data"):
        processor.parse_and_validate(INVALID_PREFS_DATA_WRONG_TYPE)

# --- Tests for transform_for_fetching ---

def test_transform_keywords_only(processor):
    """Test transforming preferences with only keywords."""
    prefs = UserPreferences(user_id="user_kw", keywords=["python", "fastapi"])
    query = processor.transform_for_fetching(prefs)
    assert query == {"q": "python AND fastapi", "language": "en"}

def test_transform_topics_only(processor):
    """Test transforming preferences with only topics."""
    prefs = UserPreferences(user_id="user_topic", topics=["health", "science"])
    query = processor.transform_for_fetching(prefs)
    assert query == {"q": "health OR science", "language": "en"}

def test_transform_sources_only(processor):
    """Test transforming preferences with only sources."""
    prefs = UserPreferences(user_id="user_src", sources=["bbc-news", "cnn"])
    query = processor.transform_for_fetching(prefs)
    assert query == {"sources": "bbc-news,cnn", "language": "en"}

def test_transform_language_only(processor):
    """Test transforming preferences with only language."""
    prefs = UserPreferences(user_id="user_lang", language="es")
    query = processor.transform_for_fetching(prefs)
    assert query == {"language": "es"}

def test_transform_keywords_and_topics(processor):
    """Test transforming preferences with keywords and topics."""
    prefs = UserPreferences(user_id="user_kw_topic", keywords=["solar", "wind"], topics=["energy", "environment"])
    query = processor.transform_for_fetching(prefs)
    # Note: Order might vary slightly depending on dict implementation details before Python 3.7
    # but the content should be the same. The current implementation adds topics after keywords.
    assert query == {"q": "solar AND wind OR (energy OR environment)", "language": "en"}

def test_transform_all_fields(processor):
    """Test transforming preferences with all fields populated."""
    prefs = UserPreferences(**VALID_PREFS_DATA_FULL)
    query = processor.transform_for_fetching(prefs)
    assert query == {
        "q": "AI AND startups OR (technology OR business)",
        "sources": "techcrunch,wired",
        "language": "en"
    }

def test_transform_minimal(processor):
    """Test transforming preferences with only user_id (and default language)."""
    prefs = UserPreferences(**VALID_PREFS_DATA_MINIMAL)
    query = processor.transform_for_fetching(prefs)
    assert query == {"language": "en"}
