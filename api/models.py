from pydantic import BaseModel, Field
from typing import List, Optional

class UserPreferences(BaseModel):
    """
    Model representing user preferences for news recommendations.
    """
    user_id: str = Field(..., description="Unique identifier for the user")
    preferred_categories: List[str] = Field(default=[], description="Preferred news categories (e.g., 'technology', 'science')")
    excluded_sources: List[str] = Field(default=[], description="Sources to exclude from results")
    preferred_authors: List[str] = Field(default=[], description="Preferred article authors")
    sources: List[str] = Field(default=[], description="Allowed news sources")
    keywords: List[str] = Field(default=[], description="Keywords to search for")
    language: str = Field(default="en", description="Preferred language for articles")
    min_reading_level: int = Field(default=1, ge=1, le=5, description="Minimum reading difficulty level")
    max_article_length: int = Field(default=1000, ge=100, description="Maximum article length in words")
    # Add weighting later if needed

class ArticleRecommendation(BaseModel):
    """
    Model representing a single recommended news article.
    """
    title: str = Field(..., description="Title of the news article")
    url: str = Field(..., description="URL link to the full article")
    source: str = Field(..., description="Source of the news article")
    summary: Optional[str] = Field(default=None, description="Generated summary of the article")
    keywords: Optional[List[str]] = Field(default=None, description="Extracted keywords from the article")
    sentiment: Optional[str] = Field(default=None, description="Analyzed sentiment of the article")
    category: Optional[str] = Field(default=None, description="Categorized topic of the article")
    relevance_score: Optional[float] = Field(default=None, description="Score indicating relevance to user preferences")

class RecommendationResponse(BaseModel):
    """
    Model for the response containing a list of recommended articles.
    """
    user_id: str = Field(..., description="User identifier for whom the recommendations are")
    recommendations: List[ArticleRecommendation] = Field(..., description="List of recommended articles")
