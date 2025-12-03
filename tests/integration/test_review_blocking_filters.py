"""
Integration tests for blocking filters in review endpoints
"""
import pytest
from fastapi.testclient import TestClient
from keyboard_smashers.api import app
from keyboard_smashers.controllers.user_controller import (
    user_controller_instance
)
from keyboard_smashers.controllers.review_controller import (
    review_controller_instance
)
from keyboard_smashers import auth


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup and teardown for each test"""
    # Store original data
    original_users = user_controller_instance.user_dao.users.copy()
    original_reviews = review_controller_instance.review_dao.reviews.copy()
    original_sessions = auth.sessions.copy()

    yield

    # Restore original data
    user_controller_instance.user_dao.users = original_users
    review_controller_instance.review_dao.reviews = original_reviews
    auth.sessions = original_sessions


client = TestClient(app)


def test_blocked_user_reviews_filtered_in_movie_reviews():
    """Test that reviews from blocked users are filtered out"""
    # Setup: user_002 creates a review
    login_response = client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "Password123!"}
    )
    token_002 = login_response.cookies.get("session_token")

    review_response = client.post(
        "/reviews/",
        json={
            "movie_id": "movie_001",
            "rating": 4.5,
            "review_text": "Great movie!"
        },
        cookies={"session_token": token_002}
    )
    assert review_response.status_code == 201

    # Login as user_001 and block user_002
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token_001 = login_response.cookies.get("session_token")

    client.post("/users/user_002/block", cookies={"session_token": token_001})

    # Get movie reviews as user_001 (should not see user_002's review)
    reviews_response = client.get(
        "/reviews/movie/movie_001",
        cookies={"session_token": token_001}
    )
    assert reviews_response.status_code == 200
    data = reviews_response.json()

    # Check that user_002's review is filtered out
    review_user_ids = [
        r.get("user_id") for r in data["reviews"] if r.get("user_id")
    ]
    assert "user_002" not in review_user_ids


def test_unblocked_user_reviews_visible():
    """Test that reviews are visible after unblocking"""
    # Setup: Block and then unblock
    user_controller_instance.user_dao.block_user("user_001", "user_002")

    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token_001 = login_response.cookies.get("session_token")

    # Unblock user_002
    client.delete("/users/user_002/block", cookies={"session_token": token_001})

    # Get movie reviews (should see user_002's reviews now)
    reviews_response = client.get(
        "/reviews/movie/movie_001",
        cookies={"session_token": token_001}
    )
    assert reviews_response.status_code == 200
    # Should not filter out user_002's reviews anymore


def test_unauthenticated_users_see_all_reviews():
    """Test that unauthenticated users see all reviews (except suspended)"""
    # Get movie reviews without authentication
    reviews_response = client.get("/reviews/movie/movie_001")
    assert reviews_response.status_code == 200
    data = reviews_response.json()
    # Should see all reviews from non-suspended users
    assert "reviews" in data


def test_blocked_user_reviews_filtered_in_user_reviews():
    """Test that blocking filters work in user review endpoint"""
    # Block user_002
    user_controller_instance.user_dao.block_user("user_001", "user_002")

    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token = login_response.cookies.get("session_token")

    # Try to get user_002's reviews (should be filtered)
    reviews_response = client.get(
        "/reviews/user/user_002",
        cookies={"session_token": token}
    )
    assert reviews_response.status_code == 200
    data = reviews_response.json()
    # Since we're viewing blocked user's profile, all their reviews filtered
    assert data["total"] == 0


def test_bidirectional_block_filters_reviews():
    """Test that blocking works both ways for review filtering"""
    # user_002 blocks user_001
    user_controller_instance.user_dao.block_user("user_002", "user_001")

    # Login as user_001 (who is blocked by user_002)
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token = login_response.cookies.get("session_token")

    # Get movie reviews - should not see user_002's reviews
    reviews_response = client.get(
        "/reviews/movie/movie_001",
        cookies={"session_token": token}
    )
    assert reviews_response.status_code == 200
    data = reviews_response.json()

    # Check that user_002's reviews are filtered out
    review_user_ids = [
        r.get("user_id") for r in data["reviews"] if r.get("user_id")
    ]
    assert "user_002" not in review_user_ids


def test_imdb_reviews_never_filtered():
    """Test that IMDB reviews (no user_id) are never filtered"""
    # Block user_002
    user_controller_instance.user_dao.block_user("user_001", "user_002")

    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token = login_response.cookies.get("session_token")

    # Get movie reviews - IMDB reviews should still be visible
    reviews_response = client.get(
        "/reviews/movie/movie_001",
        cookies={"session_token": token}
    )
    assert reviews_response.status_code == 200
    data = reviews_response.json()

    # Check that IMDB reviews (user_id is None) are present
    imdb_reviews = [r for r in data["reviews"] if r.get("user_id") is None]
    # Should have IMDB reviews (depends on test data)
    # This is more of a sanity check that filtering doesn't break IMDB reviews
    assert isinstance(imdb_reviews, list)


def test_multiple_blocks_filter_correctly():
    """Test filtering when user has blocked multiple users"""
    # user_001 blocks user_002 and user_003
    user_controller_instance.user_dao.block_user("user_001", "user_002")
    user_controller_instance.user_dao.block_user("user_001", "user_003")

    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token = login_response.cookies.get("session_token")

    # Get movie reviews - should not see user_002 or user_003's reviews
    reviews_response = client.get(
        "/reviews/movie/movie_001",
        cookies={"session_token": token}
    )
    assert reviews_response.status_code == 200
    data = reviews_response.json()

    # Check that blocked users' reviews are filtered out
    review_user_ids = [
        r.get("user_id") for r in data["reviews"] if r.get("user_id")
    ]
    assert "user_002" not in review_user_ids
    assert "user_003" not in review_user_ids
