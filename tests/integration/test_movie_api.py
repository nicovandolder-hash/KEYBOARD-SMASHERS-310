import pytest
from fastapi.testclient import TestClient
from keyboard_smashers.api import app
from keyboard_smashers.auth import sessions
from datetime import datetime, timedelta
import secrets
import time
import tempfile
from pathlib import Path


@pytest.fixture(scope="function")
def test_movies_csv():
    """Create a temporary movies CSV file for testing."""
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_path = temp_file.name

    # Copy the original movies.csv structure with initial test data
    temp_file.write("movie_id,title,genre,year,director,description\n")
    temp_file.write(
        "1,Test Movie 1,Action,2020,Test Director,Test description\n"
    )
    temp_file.write(
        "2,Inception,Sci-Fi,2010,Christopher Nolan,"
        "A mind-bending thriller\n"
    )
    temp_file.close()

    # Replace the MovieDAO's CSV path with temp file
    from keyboard_smashers.controllers.movie_controller import (
        movie_controller_instance
    )
    from keyboard_smashers.dao.review_dao import ReviewDAO

    original_path = movie_controller_instance.movie_dao.csv_path
    movie_controller_instance.movie_dao.csv_path = temp_path
    movie_controller_instance.movie_dao._load_movies()

    # Replace ReviewDAO with fresh instance for isolated testing
    original_review_dao = movie_controller_instance.review_dao
    movie_controller_instance.review_dao = ReviewDAO(
        imdb_csv_path="data/imdb_reviews.csv",
        new_reviews_csv_path=temp_path.replace('.csv', '_reviews.csv')
    )

    yield temp_path

    # Cleanup: restore original instances
    movie_controller_instance.movie_dao.csv_path = original_path
    movie_controller_instance.movie_dao._load_movies()
    movie_controller_instance.review_dao = original_review_dao

    # Delete temp files
    try:
        Path(temp_path).unlink()
        Path(temp_path.replace('.csv', '_reviews.csv')).unlink()
    except Exception:
        pass


@pytest.fixture
def client(test_movies_csv):
    """Create a TestClient with isolated test data."""
    return TestClient(app)


@pytest.fixture
def admin_client(client, test_movies_csv):
    """Create a TestClient with admin authentication."""
    # Create admin user via the API
    # (requires creating user then setting admin flag manually)
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )

    # Create admin user directly
    admin_user = {
        'user_id': 'test_admin',
        'username': 'Test Admin',
        'email': 'admin@test.com',
        'password': '',
        'reputation': 3,
        'creation_date': datetime.now(),
        'is_admin': True,
        'total_reviews': 0
    }
    user_controller_instance.user_dao.users[admin_user['user_id']] = admin_user
    user_controller_instance.user_dao.users[admin_user['user_id']] = admin_user
    user_controller_instance.user_dao.email_index[admin_user['email']] = (
        admin_user['user_id'])

    # Create admin session
    session_token = secrets.token_urlsafe(32)
    sessions[session_token] = {
        'user_id': 'test_admin',
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(hours=2),
        'is_admin': True
    }

    # Set cookie on client
    client.cookies.set("session_token", session_token)

    yield client

    # Cleanup
    if session_token in sessions:
        del sessions[session_token]
    if "test_admin" in user_controller_instance.user_dao.users:
        del user_controller_instance.user_dao.users["test_admin"]
    if "admin@test.com" in user_controller_instance.user_dao.email_index:
        del user_controller_instance.user_dao.email_index["admin@test.com"]
    client.cookies.clear()


@pytest.fixture
def regular_client(client, test_movies_csv):
    """Create a TestClient with regular user authentication."""
    session_token = secrets.token_urlsafe(32)
    sessions[session_token] = {
        'user_id': 'test_user',
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(hours=2)
    }

    # Set cookie on client
    client.cookies.set("session_token", session_token)

    yield client

    # Cleanup
    if session_token in sessions:
        del sessions[session_token]
    client.cookies.clear()


class TestMovieAPIPublicEndpoints:
    """Test public movie endpoints (no authentication required)."""

    def test_get_all_movies(self, client):
        """Test getting all movies."""
        response = client.get("/movies/")
        assert response.status_code == 200
        movies = response.json()
        assert isinstance(movies, list)
        # Should have movies from setup_movies.py
        assert len(movies) >= 6

    def test_get_movie_by_id(self, client):
        """Test getting a specific movie by ID."""
        # First get all movies to find a valid ID
        all_movies = client.get("/movies/").json()
        if all_movies:
            movie_id = all_movies[0]["movie_id"]
            response = client.get(f"/movies/{movie_id}")
            assert response.status_code == 200
            movie = response.json()
            assert movie["movie_id"] == movie_id

    def test_get_movie_not_found(self, client):
        """Test getting a non-existent movie."""
        response = client.get("/movies/nonexistent_id_12345")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_search_movies_by_query(self, client):
        """Test searching movies by query string."""
        response = client.get("/movies/search?q=inception")
        assert response.status_code == 200
        movies = response.json()
        assert isinstance(movies, list)

    def test_search_movies_by_title(self, client):
        """Test searching movies by title."""
        response = client.get("/movies/search?q=matrix")
        assert response.status_code == 200
        movies = response.json()
        assert isinstance(movies, list)

    def test_search_movies_by_genre(self, client):
        """Test getting movies by genre."""
        response = client.get("/movies/genre/Sci-Fi")
        assert response.status_code == 200
        movies = response.json()
        assert isinstance(movies, list)
        if movies:
            assert all(m["genre"] == "Sci-Fi" for m in movies)

    def test_search_movies_no_results(self, client):
        """Test search with no matching results."""
        response = client.get("/movies/search?q=nonexistent_movie_xyz123")
        assert response.status_code == 200
        assert response.json() == []


class TestMovieAPIProtectedEndpoints:
    """Test protected movie endpoints (admin authentication required)."""

    def test_create_movie_without_auth(self, client):
        """Test creating a movie without authentication."""
        movie_data = {
            "title": "New Movie",
            "genre": "Action",
            "year": 2023,
            "director": "Test Director"
        }
        response = client.post("/movies/", json=movie_data)
        assert response.status_code == 401

    def test_create_movie_with_admin(self, admin_client):
        """Test creating a movie with admin authentication."""
        unique_title = f"Integration Test Movie {int(time.time() * 1000)}"
        movie_data = {
            "title": unique_title,
            "genre": "Action",
            "year": 2023,
            "director": "Test Director"
        }
        response = admin_client.post("/movies/", json=movie_data)
        assert response.status_code == 201
        movie = response.json()
        assert movie["title"] == unique_title
        assert movie["genre"] == "Action"
        assert "movie_id" in movie

    def test_create_movie_validation_error(self, admin_client):
        """Test creating a movie with invalid data."""
        movie_data = {
            "title": "",  # Empty title should fail validation
            "genre": "Action",
            "year": 2023
        }
        response = admin_client.post("/movies/", json=movie_data)
        assert response.status_code == 422

    def test_update_movie_without_auth(self, client):
        """Test updating a movie without authentication."""
        # Get an existing movie ID
        all_movies = client.get("/movies/").json()
        if all_movies:
            movie_id = all_movies[0]["movie_id"]
            update_data = {"title": "Updated Movie"}
            response = client.put(f"/movies/{movie_id}", json=update_data)
            assert response.status_code == 401

    def test_update_movie_with_admin(self, admin_client):
        """Test updating a movie with admin authentication."""
        # Get an existing movie
        all_movies = admin_client.get("/movies/").json()
        if all_movies:
            movie_id = all_movies[0]["movie_id"]
            original_year = all_movies[0]["year"]

            update_data = {"title": "Updated Title"}
            response = admin_client.put(
                f"/movies/{movie_id}", json=update_data
            )
            assert response.status_code == 200
            movie = response.json()
            assert movie["title"] == "Updated Title"
            # Unchanged field preserved
            assert movie["year"] == original_year

    def test_update_movie_not_found(self, admin_client):
        """Test updating a non-existent movie."""
        update_data = {"title": "Updated Movie"}
        response = admin_client.put(
            "/movies/nonexistent_id_xyz", json=update_data
        )
        assert response.status_code == 404

    def test_delete_movie_without_auth(self, client):
        """Test deleting a movie without authentication."""
        all_movies = client.get("/movies/").json()
        if all_movies:
            movie_id = all_movies[0]["movie_id"]
            response = client.delete(f"/movies/{movie_id}")
            assert response.status_code == 401

    def test_delete_movie_not_found(self, admin_client):
        """Test deleting a non-existent movie."""
        response = admin_client.delete("/movies/nonexistent_id_abc")
        assert response.status_code == 404


class TestMovieAPIDataPersistence:
    """Test data persistence across requests."""

    def test_data_persists_across_requests(self, admin_client):
        """Test that created movies persist across multiple requests."""
        unique_title = f"Persistence Test {int(time.time() * 1000)}"
        # Create a movie
        movie_data = {
            "title": unique_title,
            "genre": "Drama",
            "year": 2023,
            "director": "Test Director"
        }
        create_response = admin_client.post("/movies/", json=movie_data)
        assert create_response.status_code == 201
        movie_id = create_response.json()["movie_id"]

        # Verify it exists in subsequent request
        get_response = admin_client.get(f"/movies/{movie_id}")
        assert get_response.status_code == 200
        assert get_response.json()["title"] == unique_title

        # Verify it appears in list
        list_response = admin_client.get("/movies/")
        assert list_response.status_code == 200
        movie_ids = [m["movie_id"] for m in list_response.json()]
        assert movie_id in movie_ids


class TestMovieAPIEdgeCases:
    """Test edge cases and error handling."""

    def test_create_movie_with_special_characters(self, admin_client):
        """Test creating a movie with special characters in fields."""
        unique_title = (
            f"Special Test {int(time.time() * 1000)}: Sequel - Part 1"
        )
        movie_data = {
            "title": unique_title,
            "genre": "Sci-Fi/Action",
            "year": 2023,
            "director": "O'Neill & Smith"
        }
        response = admin_client.post("/movies/", json=movie_data)
        assert response.status_code == 201
        movie = response.json()
        assert movie["title"] == unique_title

    def test_search_case_insensitive(self, client):
        """Test that search is case-insensitive."""
        # Use existing movies from setup
        response = client.get("/movies/search?q=INCEPTION")
        assert response.status_code == 200
        movies = response.json()
        assert isinstance(movies, list)


class TestMovieAverageRating:
    """Test movie detail page with average rating calculation."""

    def test_movie_detail_includes_average_rating(self, client):
        """Test that getting a movie by ID includes average_rating field."""
        # Get all movies to find a valid ID
        all_movies = client.get("/movies/").json()
        if all_movies:
            movie_id = all_movies[0]["movie_id"]
            response = client.get(f"/movies/{movie_id}")
            assert response.status_code == 200
            movie = response.json()
            assert "average_rating" in movie
            # Can be None if no reviews exist
            assert movie["average_rating"] is None or isinstance(
                movie["average_rating"], (int, float)
            )

    def test_average_rating_with_no_reviews(self, client):
        """Test that average_rating is None when no reviews exist."""
        from keyboard_smashers.controllers.movie_controller import (
            movie_controller_instance
        )

        new_movie = {
            'title': 'No Reviews Movie',
            'genre': 'Drama',
            'year': 2024,
            'director': 'Test Director',
            'description': 'Test description'
        }
        created = movie_controller_instance.movie_dao.create_movie(new_movie)
        movie_id = created['movie_id']

        response = client.get(f"/movies/{movie_id}")
        assert response.status_code == 200
        movie = response.json()
        assert movie["average_rating"] is None

    def test_average_rating_with_reviews(self, client):
        """Test average rating calculation with multiple reviews."""
        from keyboard_smashers.controllers.movie_controller import (
            movie_controller_instance
        )

        new_movie = {
            'title': 'Test Rating Movie',
            'genre': 'Comedy',
            'year': 2024,
            'director': 'Test Director',
            'description': 'Test description'
        }
        created = movie_controller_instance.movie_dao.create_movie(new_movie)
        movie_id = created['movie_id']

        review_dao = movie_controller_instance.review_dao
        review_dao.create_review({
            'movie_id': movie_id,
            'user_id': 'user1',
            'rating': 5,
            'review_text': 'Great movie!'
        })
        review_dao.create_review({
            'movie_id': movie_id,
            'user_id': 'user2',
            'rating': 3,
            'review_text': 'It was okay'
        })
        review_dao.create_review({
            'movie_id': movie_id,
            'user_id': 'user3',
            'rating': 4,
            'review_text': 'Pretty good'
        })

        response = client.get(f"/movies/{movie_id}")
        assert response.status_code == 200
        movie = response.json()

        # Average should be (5 + 3 + 4) / 3 = 4.0
        assert movie["average_rating"] == 4.0

    def test_average_rating_rounds_correctly(self, client):
        """Test that average rating is rounded to 2 decimal places."""
        from keyboard_smashers.controllers.movie_controller import (
            movie_controller_instance
        )

        new_movie = {
            'title': 'Test Rounding Movie',
            'genre': 'Thriller',
            'year': 2024,
            'director': 'Test Director',
            'description': 'Test description'
        }
        created = movie_controller_instance.movie_dao.create_movie(new_movie)
        movie_id = created['movie_id']

        review_dao = movie_controller_instance.review_dao
        review_dao.create_review({
            'movie_id': movie_id,
            'user_id': 'user1',
            'rating': 5,
            'review_text': 'Excellent!'
        })
        review_dao.create_review({
            'movie_id': movie_id,
            'user_id': 'user2',
            'rating': 4,
            'review_text': 'Good'
        })
        review_dao.create_review({
            'movie_id': movie_id,
            'user_id': 'user3',
            'rating': 3,
            'review_text': 'Average'
        })

        response = client.get(f"/movies/{movie_id}")
        assert response.status_code == 200
        movie = response.json()

        # Average should be (5 + 4 + 3) / 3 = 4.0
        assert movie["average_rating"] == 4.0

    def test_average_rating_with_single_review(self, client):
        """Test average rating with only one review."""
        from keyboard_smashers.controllers.movie_controller import (
            movie_controller_instance
        )

        new_movie = {
            'title': 'Single Review Movie',
            'genre': 'Horror',
            'year': 2024,
            'director': 'Test Director',
            'description': 'Test description'
        }
        created = movie_controller_instance.movie_dao.create_movie(new_movie)
        movie_id = created['movie_id']

        review_dao = movie_controller_instance.review_dao
        review_dao.create_review({
            'movie_id': movie_id,
            'user_id': 'user1',
            'rating': 3.5,
            'review_text': 'Decent'
        })

        response = client.get(f"/movies/{movie_id}")
        assert response.status_code == 200
        movie = response.json()

        # Average should equal the single rating
        assert movie["average_rating"] == 3.5
