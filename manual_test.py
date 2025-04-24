import os
import json
from datetime import datetime
from dotenv import load_dotenv
from api.models import UserPreferences
from processing.preference_processor import PreferenceProcessor
from fetchers.newsapi_client import NewsApiClient
from analysis.llm_analyzer import LlmAnalyzer
from recommendations.engine import RecommendationEngine
from responses.formatter import ResponseFormatter

# Load environment variables
load_dotenv()

# Initialize components
processor = PreferenceProcessor()
news_client = NewsApiClient()
analyzer = LlmAnalyzer()
engine = RecommendationEngine()
formatter = ResponseFormatter()

# Example preferences with full parameters
test_prefs = UserPreferences(
    user_id="manual_test_user",
    preferred_categories=["technology", "science"],
    excluded_sources=["Daily Bugle"],
    preferred_authors=["John Doe"],
    min_reading_level=2,
    max_article_length=500,
    language="en",
    sources=["techcrunch", "reuters"],
    keywords=["AI", "machine learning"]
)

print("Processing preferences...")
query_params = processor.transform_for_fetching(test_prefs)
print(f"NewsAPI query params: {json.dumps(query_params, indent=2)}")

print("\nFetching articles...")
try:
    articles = news_client.fetch_articles(query_params)
    if not articles:
        print("No articles found matching preferences")
        exit()
    print(f"Found {len(articles)} raw articles")
except Exception as e:
    print(f"Failed to fetch articles: {str(e)}")
    exit()

if articles:
    print("\nAnalyzing articles...")
    analyzed_articles = []
    for article in articles[:5]:  # Limit to first 5 for demo
        text = article.get('content') or article.get('description') or article.get('title') or ""
        if text:
            article['summary'] = analyzer.generate_summary(text)
            article['keywords'] = analyzer.extract_keywords(text)
            analyzed_articles.append(article)
    print(f"Analyzed {len(analyzed_articles)} articles")

    print("\nGenerating recommendations...")
    recommendations = engine.generate_recommendations(
        articles=analyzed_articles,
        preferences=test_prefs,
        num_recommendations=3
    )
    
    print("\nFormatted recommendations:")
    formatted_recommendations = formatter.format_recommendation_list(recommendations)
    print(json.dumps(formatted_recommendations, indent=2))
else:
    print("No articles found matching preferences")
