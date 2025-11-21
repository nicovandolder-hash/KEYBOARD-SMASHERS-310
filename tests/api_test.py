from keyboard_smashers.api import app
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..')))


client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "IMDB Reviews API"
    assert data["status"] == "online"
    assert "total_reviews" in data
    assert "total_movies" in data
    assert "total_users" in data


def test_get_reviews_by_movie_endpoint():
    # Test with a non-existent movie ID - should return empty list
    response = client.get("/reviews/movie/999999")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["reviews"]) == 0
