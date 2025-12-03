"""
Integration tests for follow/unfollow functionality
"""
import pytest
from fastapi.testclient import TestClient
from keyboard_smashers.api import app
from keyboard_smashers.controllers.user_controller import (
    user_controller_instance
)
from keyboard_smashers import auth


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup and teardown for each test"""
    # Store original data
    original_users = user_controller_instance.user_dao.users.copy()
    original_sessions = auth.sessions.copy()

    yield

    # Restore original data
    user_controller_instance.user_dao.users = original_users
    auth.sessions = original_sessions


client = TestClient(app)


def test_follow_user_success():
    """Test successfully following a user"""
    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    assert login_response.status_code == 200
    token = login_response.cookies.get("session_token")
    assert token is not None

    # Follow user_002
    follow_response = client.post(
        "/users/user_002/follow",
        cookies={"session_token": token}
    )
    assert follow_response.status_code == 200
    data = follow_response.json()
    assert data["message"] == "Successfully followed bob_reviewer"
    assert data["following"] == "user_002"
    assert "follower_count" in data

    # Verify relationship
    user_001 = user_controller_instance.user_dao.get_user("user_001")
    user_002 = user_controller_instance.user_dao.get_user("user_002")
    assert "user_002" in user_001["following"]
    assert "user_001" in user_002["followers"]


def test_follow_self_fails():
    """Test that users cannot follow themselves"""
    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    assert login_response.status_code == 200
    token = login_response.cookies.get("session_token")

    # Try to follow self
    follow_response = client.post(
        "/users/user_001/follow",
        cookies={"session_token": token}
    )
    assert follow_response.status_code == 400
    assert "Cannot follow yourself" in follow_response.json()["detail"]


def test_follow_nonexistent_user_fails():
    """Test that following a nonexistent user fails"""
    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    assert login_response.status_code == 200
    token = login_response.cookies.get("session_token")

    # Try to follow nonexistent user
    follow_response = client.post(
        "/users/nonexistent_user/follow",
        cookies={"session_token": token}
    )
    assert follow_response.status_code == 404


def test_follow_without_authentication_fails():
    """Test that following requires authentication"""
    follow_response = client.post("/users/user_002/follow")
    assert follow_response.status_code == 401


def test_unfollow_user_success():
    """Test successfully unfollowing a user"""
    # Setup: user_001 follows user_002
    user_controller_instance.user_dao.follow_user("user_001", "user_002")

    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    assert login_response.status_code == 200
    token = login_response.cookies.get("session_token")

    # Unfollow user_002
    unfollow_response = client.delete(
        "/users/user_002/follow",
        cookies={"session_token": token}
    )
    assert unfollow_response.status_code == 200
    data = unfollow_response.json()
    assert data["message"] == "Successfully unfollowed bob_reviewer"
    assert data["unfollowed"] == "user_002"

    # Verify relationship removed
    user_001 = user_controller_instance.user_dao.get_user("user_001")
    user_002 = user_controller_instance.user_dao.get_user("user_002")
    assert "user_002" not in user_001.get("following", [])
    assert "user_001" not in user_002.get("followers", [])


def test_get_followers():
    """Test getting a user's followers"""
    # Setup: user_002 and user_003 follow user_001
    user_controller_instance.user_dao.follow_user("user_002", "user_001")
    user_controller_instance.user_dao.follow_user("user_003", "user_001")

    # Get followers (no auth required)
    response = client.get("/users/user_001/followers")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["user_id"] == "user_001"
    assert len(data["followers"]) == 2
    follower_ids = [f["userid"] for f in data["followers"]]
    assert "user_002" in follower_ids
    assert "user_003" in follower_ids


def test_get_followers_pagination():
    """Test pagination of followers list"""
    # Setup: Multiple users follow user_001
    for i in range(2, 6):  # user_002 to user_005
        user_id = f"user_{i:03d}"
        try:
            user_controller_instance.user_dao.follow_user(user_id, "user_001")
        except Exception:
            pass

    # Get first page
    response = client.get("/users/user_001/followers?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["followers"]) <= 2

    # Get second page
    response = client.get("/users/user_001/followers?limit=2&offset=2")
    assert response.status_code == 200
    data = response.json()
    assert data["offset"] == 2


def test_get_following():
    """Test getting users that a user follows"""
    # Setup: user_001 follows user_002 and user_003
    user_controller_instance.user_dao.follow_user("user_001", "user_002")
    user_controller_instance.user_dao.follow_user("user_001", "user_003")

    # Get following (no auth required)
    response = client.get("/users/user_001/following")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["user_id"] == "user_001"
    assert len(data["following"]) == 2
    following_ids = [f["userid"] for f in data["following"]]
    assert "user_002" in following_ids
    assert "user_003" in following_ids


def test_follow_idempotent():
    """Test that following the same user multiple times is idempotent"""
    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token = login_response.cookies.get("session_token")

    # Follow user_002 twice
    client.post("/users/user_002/follow", cookies={"session_token": token})
    client.post("/users/user_002/follow", cookies={"session_token": token})

    # Verify only one relationship exists
    user_001 = user_controller_instance.user_dao.get_user("user_001")
    assert user_001["following"].count("user_002") == 1


def test_unfollow_idempotent():
    """Test that unfollowing when not following is idempotent"""
    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token = login_response.cookies.get("session_token")

    # Unfollow user_002 (not following them)
    response = client.delete(
        "/users/user_002/follow",
        cookies={"session_token": token}
    )
    assert response.status_code == 200
