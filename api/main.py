import logging
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler # Import slowapi
from slowapi.util import get_remote_address # Import slowapi utility
from slowapi.errors import RateLimitExceeded
from .models import UserPreferences, RecommendationResponse, ArticleRecommendation
from configuration.config import settings
from processing.preference_processor import PreferenceProcessor
from fetchers.newsapi_client import NewsApiClient
from analysis.llm_analyzer import LlmAnalyzer # Import Analyzer (for future use)
from recommendations.engine import RecommendationEngine # Import Engine
from responses.formatter import ResponseFormatter # Import Formatter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Rate Limiting Setup ---
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"]) # Define limiter
# --- End Rate Limiting Setup ---

app = FastAPI(
    title="AI News Recommendation Agent API",
    description="API for fetching personalized news recommendations.",
    version="0.1.0"
)

# --- Add SlowAPI Middleware and Exception Handler ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# --- End Middleware ---

@app.get("/")
async def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the AI News Recommendation Agent API"}

# Generic Exception Handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred."},
    )

# --- Authentication Dependency ---
async def api_key_auth(x_api_key: str = Header(None)):
    """Dependency to validate API Key"""
    if not x_api_key:
        logger.warning("API key missing from request header")
        raise HTTPException(
            status_code=401,
            detail="API Key required in X-API-Key header",
        )
    # Use a secure comparison method in production if needed
    if x_api_key != settings.API_KEY:
        logger.warning("Invalid API key received")
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key",
        )
    logger.debug("API key validated successfully")
    return x_api_key
# --- End Authentication Dependency ---

# In-memory storage for preferences (replace with database later)
user_preferences_db = {}

@app.post("/api/preferences", status_code=201, dependencies=[Depends(api_key_auth)])
@limiter.limit("5/minute") # Apply rate limit (override default if needed)
async def receive_preferences(request: Request, preferences: UserPreferences): # Add request parameter for limiter
    """
    Receive and store user preferences. Requires API Key authentication and is rate limited.
    """
    logger.info(f"Received preferences for user {preferences.user_id}")
    try:
        # Store preferences (in-memory for now)
        user_preferences_db[preferences.user_id] = preferences
        logger.info(f"Preferences stored successfully for user {preferences.user_id}")
        return {"message": f"Preferences received for user {preferences.user_id}"}
    except Exception as e:
        logger.error(f"Error storing preferences for user {preferences.user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to store preferences")

@app.get("/api/recommendations", response_model=RecommendationResponse, dependencies=[Depends(api_key_auth)])
@limiter.limit("10/minute") # Apply rate limit
async def get_recommendations(request: Request, user_id: str): # Add request parameter for limiter
    """
    Retrieve news recommendations for a given user. Requires API Key authentication and is rate limited.
    (Placeholder implementation)
    """
    logger.info(f"Recommendation request received for user {user_id}")
    if user_id not in user_preferences_db:
        logger.warning(f"Preferences not found for user {user_id}")
        raise HTTPException(status_code=404, detail=f"Preferences not found for user {user_id}")

    # Retrieve stored preferences
    user_prefs: UserPreferences = user_preferences_db[user_id]
    logger.info(f"Retrieved preferences for user {user_id}: {user_prefs.dict()}")

    # Process preferences to get query parameters
    processor = PreferenceProcessor()
    try:
        query_params = processor.transform_for_fetching(user_prefs)
        logger.info(f"Transformed preferences into query params for user {user_id}: {query_params}")
        # Use these query_params to fetch news from NewsAPI
        news_client = NewsApiClient()
        fetched_articles_raw = news_client.fetch_articles(query_params)

    except ValueError as ve: # Catch specific config errors like missing API key
         logger.error(f"Configuration error for NewsAPI client: {ve}", exc_info=True)
         raise HTTPException(status_code=500, detail="NewsAPI client configuration error.")
    except Exception as e:
        logger.error(f"Error during preference processing or news fetching for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing preferences or fetching news")

    if fetched_articles_raw is None:
        logger.warning(f"News fetching failed for user {user_id} with params {query_params}. Returning empty list.")
        # Decide if we should return an error or empty list. Empty list might be better UX.
        return RecommendationResponse(user_id=user_id, recommendations=[])

    # --- Phase 8: Integrate Analysis ---
    analyzed_articles = []
    analyzer = LlmAnalyzer() # Initialize the analyzer

    if not analyzer.client:
        logger.warning("LLM Analyzer client not available. Skipping analysis.")
        # Proceed without analysis if the client failed to initialize
        articles_to_rank = fetched_articles_raw
    else:
        logger.info(f"Starting analysis for {len(fetched_articles_raw)} fetched articles.")
        for article in fetched_articles_raw:
            # Extract text content (prioritize content, then description, then title)
            text_content = article.get('content') or article.get('description') or article.get('title') or ""
            # Ensure we have some text to analyze
            if text_content:
                # Add analyzed fields (functions handle None return gracefully)
                # Use a copy to avoid modifying the original dict if needed elsewhere, though not strictly necessary here
                analyzed_article = article.copy()
                analyzed_article['summary'] = analyzer.generate_summary(text_content)
                analyzed_article['keywords'] = analyzer.extract_keywords(text_content)
                analyzed_article['sentiment'] = analyzer.analyze_sentiment(text_content)
                analyzed_article['category'] = analyzer.categorize_article(text_content)
                analyzed_articles.append(analyzed_article)
                logger.debug(f"Analyzed article: {analyzed_article.get('title', 'N/A')[:30]}...")
            else:
                logger.warning(f"Skipping analysis for article with no text content: {article.get('title', 'N/A')}")
                analyzed_articles.append(article) # Add article even if not analyzed
        articles_to_rank = analyzed_articles
        logger.info(f"Finished analysis. {len(articles_to_rank)} articles ready for ranking.")
    # --- End Analysis Integration ---

    # Rank articles using the Recommendation Engine
    engine = RecommendationEngine()
    ranked_articles = engine.generate_recommendations(
        articles=articles_to_rank,
        preferences=user_prefs,
        num_recommendations=20 # Fetch more initially, let engine decide final count
    ) # Using default num_recommendations from engine for now

    # Format the final ranked articles for the response
    formatter = ResponseFormatter()
    formatted_recommendations = formatter.format_recommendation_list(ranked_articles)

    logger.info(f"Returning {len(formatted_recommendations)} formatted recommendations for user {user_id}")
    return RecommendationResponse(user_id=user_id, recommendations=formatted_recommendations)
