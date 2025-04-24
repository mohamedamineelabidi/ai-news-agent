import requests
import logging
import json # To create hashable cache keys from dicts
from typing import Dict, Any, List, Optional
from configuration.config import settings
from cachetools import cached, TTLCache # Import caching utilities

logger = logging.getLogger(__name__)

NEWSAPI_BASE_URL = "https://newsapi.org/v2/everything"

# --- Cache Setup ---
# Cache results for 10 minutes (600 seconds), max 100 entries
news_api_cache = TTLCache(maxsize=100, ttl=600)

# Helper to create a hashable key from query params dict
def make_cache_key(query_params: Dict[str, Any]) -> str:
    # Sort items to ensure consistent key regardless of dict order
    return json.dumps(query_params, sort_keys=True)
# --- End Cache Setup ---

class NewsApiClient:
    """
    Client for interacting with the NewsAPI.org service.
    """

    def __init__(self, api_key: str = settings.NEWSAPI_KEY):
        if not api_key:
            logger.error("NewsAPI key is not configured.")
            raise ValueError("NewsAPI key is required.")
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        logger.info("NewsApiClient initialized.")

    # Apply caching decorator
    @cached(cache=news_api_cache, key=lambda self, query_params: make_cache_key(query_params))
    def fetch_articles(self, query_params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches news articles from NewsAPI based on the provided query parameters.
        Results are cached for 10 minutes.

        Args:
            query_params: A dictionary of parameters compatible with the NewsAPI /v2/everything endpoint.
                          Example: {'q': 'AI', 'language': 'en', 'pageSize': 10}

        Returns:
            A list of article dictionaries if successful, None otherwise.
        """
        # Create a copy to avoid mutating the input dict used for caching
        params_to_use = {
            "q": query_params.get("q", ""),
            "sources": query_params.get("sources", ""),
            "excludeDomains": query_params.get("excludeDomains", ""),
            "language": query_params.get("language", "en"),
            "pageSize": min(int(query_params.get("pageSize", 20)), 100),
            "sortBy": query_params.get("sortBy", "publishedAt"),
            "from": query_params.get("from", "")
        }
        # Remove empty values
        params_to_use = {k: v for k, v in params_to_use.items() if v}

        # This log will only appear on cache misses
        logger.info(f"CACHE MISS - Fetching articles from NewsAPI with params: {params_to_use}") # Log the params being used
        try:
            # Use the copied and potentially modified params for the request
            response = requests.get(NEWSAPI_BASE_URL, headers=self.headers, params=params_to_use, timeout=10)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            data = response.json()

            if data.get("status") == "ok":
                articles = data.get("articles", [])
                logger.info(f"Successfully fetched {len(articles)} articles.")
                # TODO: Add pagination handling if totalResults > pageSize
                return articles
            else:
                # Handle API-specific errors (e.g., invalid key, rate limit)
                error_code = data.get("code")
                error_message = data.get("message")
                logger.error(f"NewsAPI returned error - Code: {error_code}, Message: {error_message}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request to NewsAPI failed: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during NewsAPI fetch: {e}", exc_info=True)
            return None

# Example Usage (for testing purposes)
if __name__ == '__main__':
    # Ensure you have a valid NEWSAPI_KEY in your .env file
    if not settings.NEWSAPI_KEY or settings.NEWSAPI_KEY == "YOUR_NEWSAPI_KEY":
         print("Please set a valid NEWSAPI_KEY in your .env file to run this example.")
    else:
        client = NewsApiClient()
        # Example query based on transformed preferences
        example_query = {'q': 'artificial intelligence OR machine learning', 'language': 'en', 'pageSize': 5}
        fetched_articles = client.fetch_articles(example_query)

        if fetched_articles:
            print(f"\nFetched {len(fetched_articles)} articles:")
            for i, article in enumerate(fetched_articles):
                print(f"  {i+1}. {article.get('title')} (Source: {article.get('source', {}).get('name')})")
        else:
            print("\nFailed to fetch articles.")

        # Example error case (e.g., invalid parameter)
        # invalid_query = {'q': 'test', 'invalidParam': 'xyz'}
        # client.fetch_articles(invalid_query)
