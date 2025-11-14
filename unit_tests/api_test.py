import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from keyboard_smashers.api import app


client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "IMDB Reviews API"
    assert data["status"] == "online"
    assert "total_reviews" in data
    assert "total_movies" in data

def test_get_reviews_endpoint():
    response = client.get("/reviews?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert len(data["reviews"]) == 0
    for review in data["reviews"]:
        assert "review_id" in review
        assert "user_id" in review
        assert "movie_id" in review
        assert "movie_title" in review
        assert "rating" in review
        assert "comment" in review
        assert "helpful_votes" in review
