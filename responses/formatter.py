import logging
from typing import List, Dict, Any
from api.models import ArticleRecommendation # Import the response model

logger = logging.getLogger(__name__)

class ResponseFormatter:
    """
    Formats processed article data into the structure required for API responses.
    """

    def __init__(self):
        logger.info("ResponseFormatter initialized.")

    def format_single_article(self, article_data: Dict[str, Any]) -> ArticleRecommendation:
        """
        Formats a single article dictionary into an ArticleRecommendation object.

        Args:
            article_data: A dictionary containing article information, potentially including
                          raw data from fetcher, analysis results from LLM, and scores
                          from the recommendation engine. Expected keys might include:
                          'title', 'url', 'source' (dict), 'summary', 'keywords',
                          'sentiment', 'category', 'relevance_score', etc.

        Returns:
            An ArticleRecommendation Pydantic model instance.
        """
        try:
            # Extract data safely using .get() with defaults
            formatted = ArticleRecommendation(
                title=article_data.get('title', 'N/A'),
                url=article_data.get('url', ''),
                # Handle nested source dictionary
                source=article_data.get('source', {}).get('name', 'N/A'),
                # Include fields added by analysis and recommendation engine
                summary=article_data.get('summary'), # Will be None if not present
                keywords=article_data.get('keywords'),
                sentiment=article_data.get('sentiment'),
                category=article_data.get('category'),
                relevance_score=article_data.get('relevance_score')
            )
            logger.debug(f"Formatted article: {formatted.title[:30]}...")
            return formatted
        except Exception as e:
            # Log error if formatting fails for an article
            logger.error(f"Error formatting article data: {article_data}. Error: {e}", exc_info=True)
            # Return a default/error representation or re-raise?
            # For now, let's create a placeholder to avoid crashing the whole response
            return ArticleRecommendation(
                title="Error Formatting Article",
                url=article_data.get('url', ''), # Keep URL if possible
                source="N/A",
                summary="Could not format article details."
            )

    def format_recommendation_list(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Formats a list of article dictionaries into a list of ArticleRecommendation objects.
        """
        formatted_list = []
        for article_data in articles:
            formatted_article = self.format_single_article(article_data)
            formatted_list.append(formatted_article.dict())

        logger.info(f"Formatted {len(formatted_list)} articles for response.")
        return formatted_list

# Example Usage (for testing purposes)
if __name__ == '__main__':
    formatter = ResponseFormatter()

    sample_processed_article = {
        'title': 'Test Article Title',
        'url': 'http://example.com/test',
        'source': {'id': 'test-src', 'name': 'Test Source Name'},
        'summary': 'This is the LLM summary.',
        'keywords': ['test', 'llm', 'format'],
        'sentiment': 'neutral',
        'category': 'technology',
        'relevance_score': 3.5,
        'description': 'Original description', # Extra field, should be ignored by formatter
        'content': 'Original content'        # Extra field
    }

    sample_article_missing_data = {
         'title': 'Incomplete Article',
         'url': 'http://example.com/incomplete',
         # Missing source, summary, keywords etc.
         'relevance_score': 1.0
    }

    formatted1 = formatter.format_single_article(sample_processed_article)
    print("\n--- Formatted Article (Full) ---")
    print(formatted1.dict()) # Use .dict() for easy printing

    formatted2 = formatter.format_single_article(sample_article_missing_data)
    print("\n--- Formatted Article (Incomplete) ---")
    print(formatted2.dict())

    formatted_list = formatter.format_recommendation_list([sample_processed_article, sample_article_missing_data])
    print("\n--- Formatted List ---")
    for item in formatted_list:
        print(item.dict())
