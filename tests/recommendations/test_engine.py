import pytest
from recommendations.engine import RecommendationEngine
from api.models import UserPreferences # Import the model

# --- Sample Data ---

SAMPLE_PREFS_TECH = UserPreferences(
    user_id="tech_user",
    keywords=["ai", "gpu"],
    topics=["technology", "science"],
    sources=["nvidia news", "tech report"]
)

SAMPLE_PREFS_SPORTS = UserPreferences(
    user_id="sports_user",
    keywords=["goal", "match"],
    topics=["sports"],
    sources=["espn"]
)

ARTICLE_TECH_AI_GPU = {
    'title': 'New AI Chip uses Advanced GPU',
    'description': 'Breakthrough in AI processing.',
    'content': 'The new gpu accelerates AI tasks.',
    'source': {'name': 'Tech Report'},
    'category': 'technology' # Assuming analysis added this
}

ARTICLE_TECH_PYTHON = {
    'title': 'Python for Web Dev',
    'description': 'Using Python frameworks.',
    'content': 'Python is versatile.',
    'source': {'name': 'Coding Blog'},
    'category': 'technology'
}

ARTICLE_SPORTS_GOAL = {
    'title': 'Late Goal Wins the Match',
    'description': 'Exciting football match ends.',
    'content': 'A spectacular goal in the final minutes.',
    'source': {'name': 'ESPN'},
    'category': 'sports'
}

ARTICLE_BUSINESS = {
    'title': 'Market Trends Q3',
    'description': 'Economic overview.',
    'content': 'Stocks and bonds analysis.',
    'source': {'name': 'Financial Times'},
    'category': 'business'
}

ARTICLES_LIST = [
    ARTICLE_TECH_AI_GPU,
    ARTICLE_TECH_PYTHON,
    ARTICLE_SPORTS_GOAL,
    ARTICLE_BUSINESS
]

# --- Fixtures ---

@pytest.fixture
def engine():
    """Pytest fixture to create a RecommendationEngine instance."""
    return RecommendationEngine()

# --- Test Cases ---

# --- Tests for score_article ---

def test_score_article_high_match(engine):
    """Test scoring when article strongly matches preferences."""
    score = engine.score_article(ARTICLE_TECH_AI_GPU, SAMPLE_PREFS_TECH)
    # Expected: 1.0 (ai) + 1.0 (gpu) + 2.0 (category) + 0.5 (source) = 4.5
    assert score == pytest.approx(4.5)

def test_score_article_partial_match_category(engine):
    """Test scoring when only category matches."""
    score = engine.score_article(ARTICLE_TECH_PYTHON, SAMPLE_PREFS_TECH)
    # Expected: 2.0 (category) = 2.0
    assert score == pytest.approx(2.0)

def test_score_article_partial_match_keywords(engine):
    """Test scoring when only keywords match."""
    # Modify article to remove category/source match for this test
    article_modified = ARTICLE_TECH_AI_GPU.copy()
    article_modified['category'] = 'general'
    article_modified['source'] = {'name': 'Other Source'}
    score = engine.score_article(article_modified, SAMPLE_PREFS_TECH)
    # Expected: 1.0 (ai) + 1.0 (gpu) = 2.0
    assert score == pytest.approx(2.0)

def test_score_article_partial_match_source(engine):
    """Test scoring when only source matches."""
    # Modify article to remove category/keyword match for this test
    article_modified = ARTICLE_TECH_AI_GPU.copy()
    article_modified['category'] = 'general'
    article_modified['title'] = 'New Chip'
    article_modified['description'] = '...'
    article_modified['content'] = '...'
    score = engine.score_article(article_modified, SAMPLE_PREFS_TECH)
    # Expected: 0.5 (source) = 0.5
    assert score == pytest.approx(0.5)

def test_score_article_no_match(engine):
    """Test scoring when article does not match preferences."""
    score = engine.score_article(ARTICLE_BUSINESS, SAMPLE_PREFS_TECH)
    assert score == pytest.approx(0.0)

def test_score_article_different_prefs(engine):
    """Test scoring with a different set of preferences."""
    score = engine.score_article(ARTICLE_SPORTS_GOAL, SAMPLE_PREFS_SPORTS)
    # Expected: 1.0 (goal) + 1.0 (match) + 2.0 (category) + 0.5 (source) = 4.5
    assert score == pytest.approx(4.5)

# --- Tests for rank_articles ---

def test_rank_articles(engine):
    """Test ranking sorts articles correctly by score."""
    ranked = engine.rank_articles(ARTICLES_LIST, SAMPLE_PREFS_TECH)
    assert len(ranked) == 4
    # Scores based on SAMPLE_PREFS_TECH:
    # ARTICLE_TECH_AI_GPU: 4.5
    # ARTICLE_TECH_PYTHON: 2.0
    # ARTICLE_SPORTS_GOAL: 0.0
    # ARTICLE_BUSINESS: 0.0
    assert ranked[0]['title'] == ARTICLE_TECH_AI_GPU['title']
    assert ranked[1]['title'] == ARTICLE_TECH_PYTHON['title']
    # Order of 0-score articles might vary, check scores
    assert ranked[0]['relevance_score'] == pytest.approx(4.5)
    assert ranked[1]['relevance_score'] == pytest.approx(2.0)
    assert ranked[2]['relevance_score'] == pytest.approx(0.0)
    assert ranked[3]['relevance_score'] == pytest.approx(0.0)

def test_rank_articles_empty_list(engine):
    """Test ranking with an empty list of articles."""
    ranked = engine.rank_articles([], SAMPLE_PREFS_TECH)
    assert ranked == []

# --- Tests for generate_recommendations ---

def test_generate_recommendations_returns_correct_number(engine):
    """Test that generate_recommendations returns the specified number of articles."""
    recommendations = engine.generate_recommendations(ARTICLES_LIST, SAMPLE_PREFS_TECH, num_recommendations=2)
    assert len(recommendations) == 2
    # Check if they are the top 2
    assert recommendations[0]['title'] == ARTICLE_TECH_AI_GPU['title']
    assert recommendations[1]['title'] == ARTICLE_TECH_PYTHON['title']

def test_generate_recommendations_more_than_available(engine):
    """Test requesting more recommendations than available articles."""
    recommendations = engine.generate_recommendations(ARTICLES_LIST, SAMPLE_PREFS_TECH, num_recommendations=10)
    assert len(recommendations) == 4 # Should return all available articles, ranked
    assert recommendations[0]['title'] == ARTICLE_TECH_AI_GPU['title']

def test_generate_recommendations_empty_list(engine):
    """Test generating recommendations from an empty list."""
    recommendations = engine.generate_recommendations([], SAMPLE_PREFS_TECH)
    assert recommendations == []
