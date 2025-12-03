"""
Integration tests for follow/unfollow functionality
"""
import pytest
from http import HTTPStatus
from fastapi.testclient import TestClient
from keyboard_smashers.api import app
from keyboard_smashers.controllers.user_controller import (
    user_controller_instance
)
from keyboard_smashers import auth

# HTTP Status Code Constants
HTTP_OK = HTTPStatus.OK
HTTP_CREATED = HTTPStatus.CREATED
HTTP_BAD_REQUEST = HTTPStatus.BAD_REQUEST
HTTP_UNAUTHORIZED = HTTPStatus.UNAUTHORIZED
HTTP_NOT_FOUND = HTTPStatus.NOT_FOUND

# Pagination Constants
DEFAULT_PAGE_LIMIT = 2
DEFAULT_PAGE_OFFSET = 0
SECOND_PAGE_OFFSET = 2
TEST_FOLLOWER_COUNT = 3


@pytest.fixture(scope="function", autouse=True)
def clean_test_data():
    """Clean test data before and after each test"""
    user_dao = user_controller_instance.user_dao
    user_dao.users.clear()
    user_dao.email_index.clear()
    user_dao.username_index.clear()
    user_dao.user_counter = 1
    auth.sessions.clear()

    yield

    user_dao.users.clear()
    user_dao.email_index.clear()
    user_dao.username_index.clear()
    user_dao.user_counter = 1
    auth.sessions.clear()


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def create_and_login_user(client, username, email, password):
    """Helper to create and login a user, returns (user_id, session_token)"""
    # Register
    register_response = client.post("/users/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    assert register_response.status_code == HTTP_CREATED, (
        f"Failed to register {username}"
    )
    user_id = register_response.json()["userid"]

    # Login
    login_response = client.post("/users/login", json={
        "email": email,
        "password": password
    })
    assert login_response.status_code == HTTP_OK, f"Failed to login {username}"
    token = login_response.cookies.get("session_token")
    assert token is not None, f"No session token for {username}"

    # Clear client cookies to prevent cookie jar interference
    # This ensures explicit cookies in requests are used, not cached ones
    client.cookies.clear()

    return user_id, token


def test_follow_user_success(client):
    """Test successfully following a user"""
    # Create two users
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, _ = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # Alice follows Bob
    follow_response = client.post(
        f"/users/{bob_id}/follow",
        cookies={"session_token": alice_token}
    )
    assert follow_response.status_code == HTTP_OK
    data = follow_response.json()
    assert data["message"] == "Successfully followed bob"
    assert data["following"] == bob_id
    assert "follower_count" in data

    # Verify relationship
    user_dao = user_controller_instance.user_dao
    alice = user_dao.get_user(alice_id)
    bob = user_dao.get_user(bob_id)
    assert bob_id in alice["following"]
    assert alice_id in bob["followers"]


def test_follow_self_fails(client):
    """Test that users cannot follow themselves"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")

    # Try to follow self
    follow_response = client.post(
        f"/users/{alice_id}/follow",
        cookies={"session_token": alice_token}
    )
    assert follow_response.status_code == HTTP_BAD_REQUEST
    assert "cannot follow" in follow_response.json()["detail"].lower()


def test_follow_nonexistent_user_fails(client):
    """Test that following a nonexistent user fails"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")

    # Try to follow nonexistent user
    follow_response = client.post(
        "/users/nonexistent_user/follow",
        cookies={"session_token": alice_token}
    )
    assert follow_response.status_code == HTTP_NOT_FOUND


def test_follow_requires_authentication(client):
    """Test that follow requires authentication"""
    alice_id, _ = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, _ = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # Clear cookies to simulate unauthenticated request
    client.cookies.clear()

    # Try to follow without authentication
    follow_response = client.post(f"/users/{bob_id}/follow")
    assert follow_response.status_code == HTTP_UNAUTHORIZED


def test_follow_idempotent(client):
    """Test that following the same user twice is idempotent"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, _ = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # Follow once
    response1 = client.post(
        f"/users/{bob_id}/follow",
        cookies={"session_token": alice_token}
    )
    assert response1.status_code == HTTP_OK

    # Follow again
    response2 = client.post(
        f"/users/{bob_id}/follow",
        cookies={"session_token": alice_token}
    )
    assert response2.status_code == HTTP_OK

    # Verify only one follow relationship exists
    user_dao = user_controller_instance.user_dao
    alice = user_dao.get_user(alice_id)
    bob = user_dao.get_user(bob_id)
    assert alice["following"].count(bob_id) == 1
    assert bob["followers"].count(alice_id) == 1


def test_unfollow_user_success(client):
    """Test successfully unfollowing a user"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, _ = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # First follow
    client.post(
        f"/users/{bob_id}/follow",
        cookies={"session_token": alice_token}
    )

    # Then unfollow
    unfollow_response = client.delete(
        f"/users/{bob_id}/follow",
        cookies={"session_token": alice_token}
    )
    assert unfollow_response.status_code == HTTP_OK
    data = unfollow_response.json()
    assert data["message"] == "Successfully unfollowed bob"

    # Verify relationship removed
    user_dao = user_controller_instance.user_dao
    alice = user_dao.get_user(alice_id)
    bob = user_dao.get_user(bob_id)
    assert bob_id not in alice["following"]
    assert alice_id not in bob["followers"]


def test_unfollow_requires_authentication(client):
    """Test that unfollow requires authentication"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, _ = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # Follow first (using alice's token)
    client.cookies.clear()
    client.cookies.set("session_token", alice_token)
    client.post(
        f"/users/{bob_id}/follow",
        cookies={"session_token": alice_token}
    )

    # Clear cookies to simulate unauthenticated request
    client.cookies.clear()

    # Try to unfollow without authentication
    unfollow_response = client.delete(f"/users/{bob_id}/follow")
    assert unfollow_response.status_code == HTTP_UNAUTHORIZED


def test_get_followers(client):
    """Test getting a user's followers"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, bob_token = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")
    charlie_id, charlie_token = create_and_login_user(
        client, "charlie", "charlie@example.com", "CharliePass123!")

    # Bob and Charlie follow Alice
    client.post(
        f"/users/{alice_id}/follow",
        cookies={
            "session_token": bob_token})
    client.post(f"/users/{alice_id}/follow",
                cookies={"session_token": charlie_token})

    # Get Alice's followers
    response = client.get(f"/users/{alice_id}/followers")
    assert response.status_code == HTTP_OK
    data = response.json()
    assert data["user_id"] == alice_id
    assert data["total"] == 2
    assert len(data["followers"]) == 2
    follower_ids = [f["userid"] for f in data["followers"]]
    assert bob_id in follower_ids
    assert charlie_id in follower_ids


def test_get_following(client):
    """Test getting users that a user is following"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, _ = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")
    charlie_id, _ = create_and_login_user(
        client, "charlie", "charlie@example.com", "CharliePass123!")

    # Alice follows Bob and Charlie
    client.post(f"/users/{bob_id}/follow",
                cookies={"session_token": alice_token})
    client.post(f"/users/{charlie_id}/follow",
                cookies={"session_token": alice_token})

    # Get who Alice is following
    response = client.get(f"/users/{alice_id}/following")
    assert response.status_code == HTTP_OK
    data = response.json()
    assert data["user_id"] == alice_id
    assert data["total"] == 2
    assert len(data["following"]) == 2
    following_ids = [f["userid"] for f in data["following"]]
    assert bob_id in following_ids
    assert charlie_id in following_ids


def test_followers_pagination(client):
    """Test pagination of followers list"""
    alice_id, _ = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")

    # Create 3 followers
    for i in range(TEST_FOLLOWER_COUNT):
        _, token = create_and_login_user(
            client,
            f"follower{i}",
            f"follower{i}@example.com",
            f"Follower{i}Pass123!"
        )
        client.post(
            f"/users/{alice_id}/follow",
            cookies={
                "session_token": token})

    # Get first page (limit 2)
    response1 = client.get(
        f"/users/{alice_id}/followers"
        f"?limit={DEFAULT_PAGE_LIMIT}&offset={DEFAULT_PAGE_OFFSET}"
    )
    assert response1.status_code == HTTP_OK
    data1 = response1.json()
    assert data1["total"] == TEST_FOLLOWER_COUNT
    assert len(data1["followers"]) == DEFAULT_PAGE_LIMIT
    assert data1["limit"] == DEFAULT_PAGE_LIMIT
    assert data1["offset"] == DEFAULT_PAGE_OFFSET

    # Get second page
    response2 = client.get(
        f"/users/{alice_id}/followers"
        f"?limit={DEFAULT_PAGE_LIMIT}&offset={SECOND_PAGE_OFFSET}"
    )
    assert response2.status_code == HTTP_OK
    data2 = response2.json()
    assert data2["total"] == TEST_FOLLOWER_COUNT
    assert len(data2["followers"]) == 1
    assert data2["limit"] == DEFAULT_PAGE_LIMIT
    assert data2["offset"] == SECOND_PAGE_OFFSET
