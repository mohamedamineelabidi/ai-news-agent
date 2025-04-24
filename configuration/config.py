import os
from dotenv import load_dotenv

# Load environment variables from .env file
# Assumes .env file is in the project root directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

class Settings:
    """Loads settings from environment variables."""
    PROJECT_NAME: str = "AI News Recommendation Agent"
    API_KEY: str = os.getenv("API_KEY", "default_secret_key") # Default for safety
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    NEWSAPI_KEY: str = os.getenv("NEWSAPI_KEY")

    # Add other settings as needed

settings = Settings()

# You can access settings like this:
# from configuration.config import settings
# api_key = settings.API_KEY
