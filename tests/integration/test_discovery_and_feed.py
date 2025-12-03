"""
Integration tests for user discovery and following feed functionality
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


@pytest.fixture(scope="function", autouse=True)
def clean_test_data():
    """Clean test data before and after each test"""
    user_dao = user_controller_instance.user_dao
    review_dao = review_controller_instance.review_dao

    user_dao.users.clear()
    user_dao.email_index.clear()
    user_dao.username_index.clear()
    user_dao.user_counter = 1
    auth.sessions.clear()

    # Store and clear original reviews and indexes
    original_reviews = review_dao.reviews.copy()
    original_reviews_by_movie = review_dao.reviews_by_movie.copy()
    original_reviews_by_user = review_dao.reviews_by_user.copy()

    review_dao.reviews.clear()
    review_dao.reviews_by_movie.clear()
    review_dao.reviews_by_user.clear()

    yield

    user_dao.users.clear()
    user_dao.email_index.clear()
    user_dao.username_index.clear()
    user_dao.user_counter = 1
    auth.sessions.clear()

    # Restore reviews and indexes
    review_dao.reviews = original_reviews
    review_dao.reviews_by_movie = original_reviews_by_movie
    review_dao.reviews_by_user = original_reviews_by_user


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def create_and_login_user(client, username, email, password):
    """Helper to create and login a user, returns (user_id, session_token)"""
    register_response = client.post("/users/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    assert register_response.status_code == 201
    user_id = register_response.json()["userid"]

    login_response = client.post("/users/login", json={
        "email": email,
        "password": password
    })
    assert login_response.status_code == 200
    token = login_response.cookies.get("session_token")

    # Clear client cookies to prevent cookie jar interference
    # This ensures explicit cookies in requests are used, not cached ones
    client.cookies.clear()

    return user_id, token


def test_search_users_public_access(client):
    """Test that user search is publicly accessible"""
    # Create some users
    create_and_login_user(
        client,
        "alice",
        "alice@example.com",
        "AlicePass123!")
    create_and_login_user(client, "bob", "bob@example.com", "BobPass123!")
    create_and_login_user(
        client,
        "charlie",
        "charlie@example.com",
        "CharliePass123!")

    # Search without authentication
    response = client.get("/users/search/users")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["users"]) == 3


def test_search_users_by_query(client):
    """Test searching users by username"""
    create_and_login_user(
        client,
        "alice123",
        "alice@example.com",
        "AlicePass123!")
    create_and_login_user(client, "bob456", "bob@example.com", "BobPass123!")
    create_and_login_user(
        client,
        "alice789",
        "alice2@example.com",
        "AlicePass123!")

    # Search for "alice"
    response = client.get("/users/search/users?q=alice")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["query"] == "alice"
    usernames = [u["username"] for u in data["users"]]
    assert "alice123" in usernames
    assert "alice789" in usernames
    assert "bob456" not in usernames


def test_search_users_pagination(client):
    """Test user search pagination"""
    # Create 5 users
    for i in range(5):
        create_and_login_user(
            client,
            f"user{i}",
            f"user{i}@example.com",
            f"User{i}Pass123!"
        )

    # Get first page
    response1 = client.get("/users/search/users?limit=2&offset=0")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["total"] == 5
    assert len(data1["users"]) == 2
    assert data1["limit"] == 2
    assert data1["offset"] == 0

    # Get second page
    response2 = client.get("/users/search/users?limit=2&offset=2")
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["users"]) == 2

    # Ensure different results
    page1_ids = [u["userid"] for u in data1["users"]]
    page2_ids = [u["userid"] for u in data2["users"]]
    assert len(set(page1_ids) & set(page2_ids)) == 0


def test_following_feed_requires_auth(client):
    """Test that following feed requires authentication"""
    response = client.get("/reviews/feed/following")
    assert response.status_code == 401


def test_following_feed_empty(client):
    """Test following feed when not following anyone"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!"
    )

    response = client.get(
        "/reviews/feed/following",
        cookies={"session_token": alice_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["reviews"]) == 0
    assert data["following_count"] == 0


def test_following_feed_with_follows(client):
    """Test following feed aggregates reviews from followed users"""
    # Create users
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!"
    )
    bob_id, bob_token = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!"
    )
    charlie_id, charlie_token = create_and_login_user(
        client, "charlie", "charlie@example.com", "CharliePass123!"
    )

    # Create some reviews for bob and charlie
    review_dao = review_controller_instance.review_dao

    bob_review = {
        'review_id': 'review_bob_1',
        'user_id': bob_id,
        'movie_id': 'tt0111161',
        'review_text': 'Great movie!',
        'rating': 5,
        'review_date': '2024-01-01T10:00:00'
    }
    charlie_review = {
        'review_id': 'review_charlie_1',
        'user_id': charlie_id,
        'movie_id': 'tt0068646',
        'review_text': 'Amazing film!',
        'rating': 5,
        'review_date': '2024-01-02T10:00:00'
    }

    review_dao.reviews[bob_review['review_id']] = bob_review
    review_dao.reviews[charlie_review['review_id']] = charlie_review

    # Update indexes
    review_dao.reviews_by_user.setdefault(
        bob_id, []).append(
        bob_review['review_id'])
    review_dao.reviews_by_user.setdefault(
        charlie_id, []).append(
        charlie_review['review_id'])
    review_dao.reviews_by_movie.setdefault(
        bob_review['movie_id'], []).append(
        bob_review['review_id'])
    review_dao.reviews_by_movie.setdefault(
        charlie_review['movie_id'], []).append(
        charlie_review['review_id'])

    # Alice follows Bob and Charlie
    client.post(f"/users/{bob_id}/follow",
                cookies={"session_token": alice_token})
    client.post(f"/users/{charlie_id}/follow",
                cookies={"session_token": alice_token})

    # Get following feed
    response = client.get(
        "/reviews/feed/following",
        cookies={"session_token": alice_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["reviews"]) == 2
    assert data["following_count"] == 2

    # Verify reviews are from followed users
    review_user_ids = [r["user_id"] for r in data["reviews"]]
    assert bob_id in review_user_ids
    assert charlie_id in review_user_ids


def test_following_feed_pagination(client):
    """Test following feed pagination"""
    # Create users
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!"
    )
    bob_id, bob_token = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!"
    )

    # Create multiple reviews for bob
    review_dao = review_controller_instance.review_dao
    for i in range(5):
        review = {
            'review_id': f'review_bob_{i}',
            'user_id': bob_id,
            'movie_id': 'tt0111161',
            'review_text': f'Review {i}',
            'rating': 5,
            'review_date': f'2024-01-0{i + 1}T10:00:00'
        }
        review_dao.reviews[review['review_id']] = review
        # Update indexes
        review_dao.reviews_by_user.setdefault(
            bob_id, []).append(
            review['review_id'])
        review_dao.reviews_by_movie.setdefault(
            review['movie_id'], []).append(
            review['review_id'])

    # Alice follows Bob
    client.post(f"/users/{bob_id}/follow",
                cookies={"session_token": alice_token})

    # Get first page
    response1 = client.get(
        "/reviews/feed/following?limit=2&skip=0",
        cookies={"session_token": alice_token}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["total"] == 5
    assert len(data1["reviews"]) == 2

    # Get second page
    response2 = client.get(
        "/reviews/feed/following?limit=2&skip=2",
        cookies={"session_token": alice_token}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["reviews"]) == 2
