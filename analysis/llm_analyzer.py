import logging
from openai import OpenAI, OpenAIError
import hashlib # For creating cache keys from text
from typing import List, Dict, Optional
from configuration.config import settings
from cachetools import cached, TTLCache # Import caching utilities

logger = logging.getLogger(__name__)

# --- Cache Setup ---
# Cache results for 1 hour (3600 seconds), max 500 entries
# Key will be based on method name and hash of the input text
llm_analysis_cache = TTLCache(maxsize=500, ttl=3600)

def generate_cache_key(func_name: str, text: str) -> str:
    """Generates a cache key based on function name and text hash."""
    text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
    return f"{func_name}:{text_hash}"
# --- End Cache Setup ---

class LlmAnalyzer:
    """
    Handles interaction with an LLM (OpenAI) for news article analysis tasks
    like summarization, keyword extraction, sentiment analysis, and categorization.
    """

    def __init__(self, api_key: str = settings.OPENAI_API_KEY, model: str = "gpt-3.5-turbo"):
        if not api_key or api_key == "YOUR_OPENAI_API_KEY":
            logger.error("OpenAI API key is not configured.")
            # Decide whether to raise an error or allow initialization but fail later
            # raise ValueError("OpenAI API key is required for LlmAnalyzer.")
            self.client = None # Indicate that the client is not functional
            logger.warning("LlmAnalyzer initialized without a valid OpenAI API key. Analysis functions will fail.")
        else:
            try:
                self.client = OpenAI(api_key=api_key)
                self.model = model
                logger.info(f"LlmAnalyzer initialized with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
                self.client = None
                # raise RuntimeError(f"Failed to initialize OpenAI client: {e}")

    def _make_llm_call(self, prompt: str, max_tokens: int = 150) -> Optional[str]:
        """Helper function to make a call to the OpenAI API."""
        if not self.client:
            logger.error("OpenAI client not initialized. Cannot make LLM call.")
            return None

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant analyzing news articles."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.5, # Adjust temperature for creativity vs consistency
                n=1,
                stop=None,
            )
            # Accessing the response content correctly for chat completions
            if response.choices and len(response.choices) > 0:
                 content = response.choices[0].message.content.strip()
                 logger.debug(f"LLM call successful. Response: {content[:100]}...") # Log snippet
                 return content
            else:
                 logger.warning("LLM call returned no choices or empty response.")
                 return None
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            # Handle specific errors like rate limits, auth errors etc. if needed
            # e.g., if e.http_status == 429: handle rate limit
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during LLM call: {e}", exc_info=True)
        return None

    @cached(cache=llm_analysis_cache, key=lambda self, text, num_keywords=5: generate_cache_key('extract_keywords', text + str(num_keywords)))
    def extract_keywords(self, text: str, num_keywords: int = 5) -> Optional[List[str]]:
        """
        Extracts keywords from the given text using the LLM. Results are cached.
        """
        # This log will only appear on cache misses
        logger.info(f"CACHE MISS - Requesting keyword extraction for text snippet: {text[:100]}...")
        if not self.client: return None
        prompt = f"Extract the {num_keywords} most important keywords from the following news article text. Return them as a comma-separated list:\n\n{text}"
        result = self._make_llm_call(prompt, max_tokens=50)
        if result:
            keywords = [kw.strip() for kw in result.split(',') if kw.strip()]
            logger.info(f"Extracted keywords: {keywords}")
            return keywords
        # If result is None or an empty string after stripping in _make_llm_call, return empty list
        return []

    @cached(cache=llm_analysis_cache, key=lambda self, text, max_length=100: generate_cache_key('generate_summary', text + str(max_length)))
    def generate_summary(self, text: str, max_length: int = 100) -> Optional[str]:
        """
        Generates a summary for the given text using the LLM. Results are cached.
        """
        # This log will only appear on cache misses
        logger.info(f"CACHE MISS - Requesting summary generation for text snippet: {text[:100]}...")
        if not self.client: return None
        prompt = f"Summarize the following news article text in about {max_length} words:\n\n{text}"
        summary = self._make_llm_call(prompt, max_tokens=max_length + 50) # Allow some buffer
        if summary:
             logger.info(f"Generated summary: {summary[:100]}...")
        return summary

    @cached(cache=llm_analysis_cache, key=lambda self, text: generate_cache_key('analyze_sentiment', text))
    def analyze_sentiment(self, text: str) -> Optional[str]:
        """
        Analyzes the sentiment (e.g., positive, negative, neutral) of the given text. Results are cached.
        """
        # This log will only appear on cache misses
        logger.info(f"CACHE MISS - Requesting sentiment analysis for text snippet: {text[:100]}...")
        if not self.client: return None
        prompt = f"Analyze the sentiment of the following news article text. Respond with only one word: positive, negative, or neutral.\n\n{text}"
        sentiment = self._make_llm_call(prompt, max_tokens=10)
        if sentiment and sentiment.lower() in ['positive', 'negative', 'neutral']:
             logger.info(f"Analyzed sentiment: {sentiment}")
             return sentiment.lower()
        logger.warning(f"Could not determine valid sentiment from LLM response: {sentiment}")
        return None # Or return a default like 'neutral'

    @cached(cache=llm_analysis_cache, key=lambda self, text, categories=["technology", "business", "sports", "entertainment", "health", "science", "world"]: generate_cache_key('categorize_article', text + "".join(sorted(categories))))
    def categorize_article(self, text: str, categories: List[str] = ["technology", "business", "sports", "entertainment", "health", "science", "world"]) -> Optional[str]:
        """
        Categorizes the article text into one of the provided categories. Results are cached.
        """
        # This log will only appear on cache misses
        logger.info(f"CACHE MISS - Requesting categorization for text snippet: {text[:100]}...")
        if not self.client: return None
        category_list = ", ".join(sorted(categories)) # Sort categories for consistent cache key
        prompt = f"Categorize the following news article text into one of these categories: {category_list}. Respond with only the category name.\n\n{text}"
        category = self._make_llm_call(prompt, max_tokens=15)
        if category and category.lower() in [c.lower() for c in categories]:
             logger.info(f"Categorized article as: {category}")
             return category.lower()
        logger.warning(f"Could not determine valid category from LLM response: {category}")
        return None # Or return a default like 'general'


# Example Usage (for testing purposes)
if __name__ == '__main__':
    # Ensure you have a valid OPENAI_API_KEY in your .env file
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "YOUR_OPENAI_API_KEY":
         print("Please set a valid OPENAI_API_KEY in your .env file to run this example.")
    else:
        analyzer = LlmAnalyzer()
        sample_text = """
        TechCorp announced today its groundbreaking new AI processor, the 'Quantum Leap', promising unprecedented speeds for machine learning tasks.
        Stock prices surged following the announcement. The processor uses novel photonic technology.
        Experts are cautiously optimistic about its real-world performance and energy efficiency compared to existing silicon chips.
        """

        if analyzer.client: # Check if client initialized successfully
            print("\n--- Testing LLM Analyzer ---")

            keywords = analyzer.extract_keywords(sample_text)
            print(f"Keywords: {keywords}")

            summary = analyzer.generate_summary(sample_text)
            print(f"Summary: {summary}")

            sentiment = analyzer.analyze_sentiment(sample_text)
            print(f"Sentiment: {sentiment}")

            category = analyzer.categorize_article(sample_text)
            print(f"Category: {category}")
        else:
            print("\nLLM Analyzer could not be initialized. Skipping examples.")
