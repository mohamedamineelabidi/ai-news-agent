import logging
from typing import Dict, Any
from api.models import UserPreferences # Assuming models are accessible

logger = logging.getLogger(__name__)

class PreferenceProcessor:
    """
    Handles parsing, validation, and transformation of user preferences.
    """

    def __init__(self):
        # Initialization, if needed (e.g., loading validation schemas)
        pass

    def parse_and_validate(self, preferences_data: Dict[str, Any]) -> UserPreferences:
        """
        Parses raw preference data and validates it using the Pydantic model.
        """
        try:
            preferences = UserPreferences(**preferences_data)
            logger.info(f"Successfully parsed and validated preferences for user {preferences.user_id}")
            # Add more specific validation logic here if needed beyond Pydantic
            return preferences
        except Exception as e: # Catch Pydantic validation errors and others
            logger.error(f"Failed to parse or validate preferences: {e}", exc_info=True)
            # Re-raise or handle specific validation errors appropriately
            raise ValueError(f"Invalid preference data: {e}")

    def transform_for_fetching(self, preferences: UserPreferences) -> Dict[str, Any]:
        """
        Transforms validated preferences into query parameters suitable for news fetching APIs.
        """
        query_params = {
            "language": preferences.language or "en",
            "pageSize": 20,
            "sortBy": "publishedAt"
        }

        # Build search query from categories and keywords
        search_terms = []
        if preferences.preferred_categories:
            search_terms.extend(preferences.preferred_categories)
        if preferences.keywords:
            search_terms.extend(preferences.keywords)
        
        if search_terms:
            query_params["q"] = " OR ".join(search_terms)
        
        # Handle sources and exclusions
        if preferences.sources:
            query_params["sources"] = ",".join(preferences.sources)
        if preferences.excluded_sources:
            query_params["excludeDomains"] = ",".join(preferences.excluded_sources)
        
        logger.debug(f"Transformed preferences for user {preferences.user_id} into query params: {query_params}")
        # Remove duplicate source/language handling that's already covered above

        logger.info(f"Transformed preferences for user {preferences.user_id} into query params: {query_params}")
        return query_params

# Example Usage (for testing purposes)
if __name__ == '__main__':
    processor = PreferenceProcessor()
    sample_prefs_data = {
        "user_id": "user123",
        "topics": ["technology", "finance"],
        "keywords": ["AI", "blockchain"],
        "sources": ["techcrunch"],
        "language": "en"
    }
    try:
        validated_prefs = processor.parse_and_validate(sample_prefs_data)
        print("Validated Preferences:", validated_prefs)
        query = processor.transform_for_fetching(validated_prefs)
        print("Transformed Query:", query)

        invalid_prefs_data = {
            "user_id": "user456",
            "topics": ["sports"],
            "language": 123 # Invalid type
        }
        # This should raise a ValueError
        # validated_invalid = processor.parse_and_validate(invalid_prefs_data)

    except ValueError as e:
        print(f"Validation Error: {e}")
