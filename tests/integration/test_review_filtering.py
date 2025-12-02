"""
Integration tests for filtering suspended users' reviews.
"""
import pytest
from fastapi.testclient import TestClient
from keyboard_smashers.api import app
from keyboard_smashers.auth import sessions


@pytest.fixture(scope="function", autouse=True)
def clean_test_data():
    """Clean up test data before and after each test"""
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )
    from keyboard_smashers.controllers.review_controller import (
        review_controller_instance
    )
    from keyboard_smashers.controllers.movie_controller import (
        movie_controller_instance
    )

    # Clear before test
    sessions.clear()
    user_controller_instance.user_dao.users.clear()
    user_controller_instance.user_dao.email_index.clear()
    user_controller_instance.user_dao.username_index.clear()
    user_controller_instance.user_dao.user_counter = 1

    review_controller_instance.review_dao.reviews.clear()
    review_controller_instance.review_dao.reviews_by_movie.clear()
    review_controller_instance.review_dao.reviews_by_user.clear()

    movie_controller_instance.movie_dao.movies.clear()

    # Add test movie
    movie_controller_instance.movie_dao.movies["movie_001"] = {
        "movie_id": "movie_001",
        "title": "Test Movie",
        "year": 2024,
        "genres": ["Action"],
        "plot": "A test movie"
    }

    yield

    # Clear after test
    sessions.clear()
    user_controller_instance.user_dao.users.clear()
    user_controller_instance.user_dao.email_index.clear()
    user_controller_instance.user_dao.username_index.clear()

    review_controller_instance.review_dao.reviews.clear()
    review_controller_instance.review_dao.reviews_by_movie.clear()
    review_controller_instance.review_dao.reviews_by_user.clear()

    movie_controller_instance.movie_dao.movies.clear()


@pytest.fixture
def admin_client():
    """Create an authenticated admin client"""
    client = TestClient(app)

    # Register admin
    response = client.post("/users/register", json={
        "username": "admin_user",
        "email": "admin@test.com",
        "password": "Admin123!",
        "is_admin": True
    })
    assert response.status_code == 201

    # Login
    response = client.post("/users/login", json={
        "email": "admin@test.com",
        "password": "Admin123!"
    })
    assert response.status_code == 200

    return client


@pytest.fixture
def regular_user():
    """Create a regular user and return user data"""
    client = TestClient(app)

    response = client.post("/users/register", json={
        "username": "regular_user",
        "email": "regular@test.com",
        "password": "User123!"
    })
    assert response.status_code == 201
    user_id = response.json()["userid"]

    # Login
    response = client.post("/users/login", json={
        "email": "regular@test.com",
        "password": "User123!"
    })
    assert response.status_code == 200

    return {"client": client, "user_id": user_id}


@pytest.fixture
def suspended_user():
    """Create a suspended user and return user data"""
    client = TestClient(app)

    response = client.post("/users/register", json={
        "username": "suspended_user",
        "email": "suspended@test.com",
        "password": "User123!"
    })
    assert response.status_code == 201
    user_id = response.json()["userid"]

    # Suspend the user
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )
    user_controller_instance.user_dao.suspend_user(user_id)

    return {"user_id": user_id}


class TestReviewFiltering:
    """Test that suspended users' reviews are filtered from public endpoints"""

    def test_suspended_user_reviews_not_in_movie_reviews(
        self, admin_client, regular_user, suspended_user
    ):
        """Suspended user reviews should not appear in movie review list"""
        # Create a review from regular user
        response = regular_user["client"].post("/reviews/", json={
            "movie_id": "movie_001",
            "rating": 5,
            "review_text": "Great movie from regular user!"
        })
        assert response.status_code == 201

        # Create a review from suspended user (as admin)
        from keyboard_smashers.controllers.review_controller import (
            review_controller_instance
        )
        from keyboard_smashers.controllers.review_controller import (
            ReviewCreateSchema
        )
        review_data = ReviewCreateSchema(
            movie_id="movie_001",
            rating=1,
            review_text="Bad movie from suspended user!"
        )
        review_controller_instance.create_review(
            review_data,
            suspended_user["user_id"]
        )

        # Get reviews for movie (public endpoint)
        public_client = TestClient(app)
        response = public_client.get("/reviews/movie/movie_001")
        assert response.status_code == 200

        data = response.json()
        reviews = data["reviews"]

        # Should only have 1 review (from regular user)
        assert len(reviews) == 1
        assert reviews[0]["review_text"] == "Great movie from regular user!"
        assert data["total"] == 1

    def test_imdb_reviews_always_included(self, suspended_user):
        """IMDB reviews (user_id=None) should always be included"""
        from keyboard_smashers.controllers.review_controller import (
            review_controller_instance
        )

        # Add IMDB review manually
        review_controller_instance.review_dao.reviews["imdb_001"] = {
            "review_id": "imdb_001",
            "movie_id": "movie_001",
            "user_id": None,
            "imdb_username": "imdb_reviewer",
            "rating": 4.5,
            "review_text": "IMDB review",
            "review_date": "2024-01-01"
        }
        review_controller_instance.review_dao.reviews_by_movie["movie_001"] = [
            "imdb_001"
        ]

        # Get reviews
        public_client = TestClient(app)
        response = public_client.get("/reviews/movie/movie_001")
        assert response.status_code == 200

        data = response.json()
        reviews = data["reviews"]

        # IMDB review should be included
        assert len(reviews) == 1
        assert reviews[0]["review_id"] == "imdb_001"
        assert reviews[0]["imdb_username"] == "imdb_reviewer"

    def test_user_reviews_endpoint_filters_suspended(
        self, regular_user, suspended_user
    ):
        """User reviews endpoint should filter suspended users"""
        from keyboard_smashers.controllers.review_controller import (
            review_controller_instance
        )
        from keyboard_smashers.controllers.review_controller import (
            ReviewCreateSchema
        )

        # Create review from suspended user
        review_data = ReviewCreateSchema(
            movie_id="movie_001",
            rating=1,
            review_text="Review from suspended user"
        )
        review_controller_instance.create_review(
            review_data,
            suspended_user["user_id"]
        )

        # Try to get reviews by suspended user
        public_client = TestClient(app)
        response = public_client.get(
            f"/reviews/user/{suspended_user['user_id']}"
        )
        assert response.status_code == 200

        data = response.json()
        # Should be empty (filtered out)
        assert len(data["reviews"]) == 0
        assert data["total"] == 0

    def test_filtering_with_mixed_reviews(
        self, admin_client, regular_user, suspended_user
    ):
        """Test filtering works with mix of regular and suspended users"""
        from keyboard_smashers.controllers.review_controller import (
            review_controller_instance
        )
        from keyboard_smashers.controllers.review_controller import (
            ReviewCreateSchema
        )
        from keyboard_smashers.controllers.movie_controller import (
            movie_controller_instance
        )

        # Add more test movies
        movie_controller_instance.movie_dao.movies["movie_002"] = {
            "movie_id": "movie_002",
            "title": "Test Movie 2",
            "year": 2024,
            "genres": ["Drama"],
            "plot": "Another test movie"
        }
        movie_controller_instance.movie_dao.movies["movie_003"] = {
            "movie_id": "movie_003",
            "title": "Test Movie 3",
            "year": 2024,
            "genres": ["Comedy"],
            "plot": "A third test movie"
        }
        movie_controller_instance.movie_dao.movies["movie_004"] = {
            "movie_id": "movie_004",
            "title": "Test Movie 4",
            "year": 2024,
            "genres": ["Horror"],
            "plot": "A fourth test movie"
        }

        # Create 2 reviews from regular user on different movies
        response = regular_user["client"].post("/reviews/", json={
            "movie_id": "movie_001",
            "rating": 5,
            "review_text": "Review 1 from regular user"
        })
        assert response.status_code == 201

        response = regular_user["client"].post("/reviews/", json={
            "movie_id": "movie_002",
            "rating": 4,
            "review_text": "Review 2 from regular user"
        })
        assert response.status_code == 201

        # Create 3 reviews from suspended user on different movies
        movies = ["movie_001", "movie_003", "movie_004"]
        for i, movie_id in enumerate(movies):
            review_data = ReviewCreateSchema(
                movie_id=movie_id,
                rating=1,
                review_text=f"Review {i + 1} from suspended user"
            )
            review_controller_instance.create_review(
                review_data,
                suspended_user["user_id"]
            )

        # Get reviews for movie_001
        public_client = TestClient(app)
        response = public_client.get("/reviews/movie/movie_001")
        assert response.status_code == 200

        data = response.json()
        reviews = data["reviews"]

        # Should only have 1 review (from regular user,
        # suspended ones filtered)
        assert len(reviews) == 1
        assert data["total"] == 1
        assert "regular user" in reviews[0]["review_text"]

    def test_reactivated_user_reviews_visible(
        self, admin_client, suspended_user
    ):
        """After reactivation, user reviews should be visible again"""
        from keyboard_smashers.controllers.review_controller import (
            review_controller_instance
        )
        from keyboard_smashers.controllers.review_controller import (
            ReviewCreateSchema
        )

        # Create review from suspended user
        review_data = ReviewCreateSchema(
            movie_id="movie_001",
            rating=3,
            review_text="Review from user"
        )
        review_controller_instance.create_review(
            review_data,
            suspended_user["user_id"]
        )

        # Verify it's filtered when suspended
        public_client = TestClient(app)
        response = public_client.get("/reviews/movie/movie_001")
        assert response.status_code == 200
        assert len(response.json()["reviews"]) == 0

        # Reactivate user
        response = admin_client.post(
            f"/users/{suspended_user['user_id']}/reactivate"
        )
        assert response.status_code == 200

        # Now reviews should be visible
        response = public_client.get("/reviews/movie/movie_001")
        assert response.status_code == 200
        data = response.json()
        assert len(data["reviews"]) == 1
        assert data["reviews"][0]["review_text"] == "Review from user"
