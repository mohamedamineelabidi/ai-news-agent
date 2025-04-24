# AI News Recommendation System

[Previous content...]

## API Integration Guide

### Base URL
`http://localhost:8000/api/v1`

### Endpoints

#### Get Recommendations
```http
POST /recommendations
```
**Request Body**
```json
{
  "user_id": "user_123",
  "preferred_categories": ["technology", "science"],
  "keywords": ["AI", "machine learning"],
  "sources": ["techcrunch"],
  "language": "en",
  "max_articles": 10
}
```

**Response**
```json
{
  "user_id": "user_123",
  "recommendations": [
    {
      "title": "AI Breakthrough in Healthcare",
      "url": "https://example.com/article1",
      "summary": "New AI system achieves 98% accuracy...",
      "relevance_score": 4.8,
      "keywords": ["AI", "healthcare", "machine learning"]
    }
  ],
  "analysis_metadata": {
    "processing_time": 1.23,
    "model_version": "gpt-4-0613"
  }
}
```

#### Health Check
```http
GET /health
```
**Response**
```json
{
  "status": "OK",
  "version": "1.0.0",
  "timestamp": "2025-04-24T01:35:00Z"
}
```

### Authentication
Add API key to headers:
```http
X-API-Key: your_api_key_here
```

### Client Example (Python)
```python
import requests

API_URL = "http://localhost:8000/api/v1/recommendations"
API_KEY = "your_api_key_here"

preferences = {
    "user_id": "client_123",
    "preferred_categories": ["technology"],
    "keywords": ["LLM"],
    "max_articles": 5
}

response = requests.post(
    API_URL,
    json=preferences,
    headers={"X-API-Key": API_KEY}
)

if response.status_code == 200:
    recommendations = response.json()
    print(f"Received {len(recommendations)} articles")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

### Error Handling
Common error responses:
```json
{
  "detail": [
    {
      "type": "missing_api_key",
      "msg": "X-API-Key header is required",
      "status": 401
    }
  ]
}
```

[Remaining previous content...]
