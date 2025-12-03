"""
Integration tests for block/unblock functionality
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


def test_block_user_success():
    """Test successfully blocking a user"""
    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    assert login_response.status_code == 200
    token = login_response.cookies.get("session_token")

    # Block user_002
    block_response = client.post(
        "/users/user_002/block",
        cookies={"session_token": token}
    )
    assert block_response.status_code == 200
    data = block_response.json()
    assert data["message"] == "Successfully blocked bob_reviewer"
    assert data["blocked"] == "user_002"

    # Verify bidirectional block
    user_001 = user_controller_instance.user_dao.get_user("user_001")
    user_002 = user_controller_instance.user_dao.get_user("user_002")
    assert "user_002" in user_001["blocked_users"]
    assert "user_001" in user_002["blocked_users"]


def test_block_self_fails():
    """Test that users cannot block themselves"""
    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token = login_response.cookies.get("session_token")

    # Try to block self
    block_response = client.post(
        "/users/user_001/block",
        cookies={"session_token": token}
    )
    assert block_response.status_code == 400
    assert "Cannot block yourself" in block_response.json()["detail"]


def test_block_removes_follow_relationships():
    """Test that blocking removes existing follow relationships"""
    # Setup: user_001 follows user_002 and vice versa
    user_controller_instance.user_dao.follow_user("user_001", "user_002")
    user_controller_instance.user_dao.follow_user("user_002", "user_001")

    # Verify follows exist
    user_001 = user_controller_instance.user_dao.get_user("user_001")
    user_002 = user_controller_instance.user_dao.get_user("user_002")
    assert "user_002" in user_001["following"]
    assert "user_001" in user_002["following"]

    # Login and block
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token = login_response.cookies.get("session_token")

    client.post("/users/user_002/block", cookies={"session_token": token})

    # Verify follows removed
    user_001 = user_controller_instance.user_dao.get_user("user_001")
    user_002 = user_controller_instance.user_dao.get_user("user_002")
    assert "user_002" not in user_001.get("following", [])
    assert "user_001" not in user_002.get("following", [])
    assert "user_002" not in user_001.get("followers", [])
    assert "user_001" not in user_002.get("followers", [])


def test_block_without_authentication_fails():
    """Test that blocking requires authentication"""
    block_response = client.post("/users/user_002/block")
    assert block_response.status_code == 401


def test_unblock_user_success():
    """Test successfully unblocking a user"""
    # Setup: user_001 blocks user_002
    user_controller_instance.user_dao.block_user("user_001", "user_002")

    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token = login_response.cookies.get("session_token")

    # Unblock user_002
    unblock_response = client.delete(
        "/users/user_002/block",
        cookies={"session_token": token}
    )
    assert unblock_response.status_code == 200
    data = unblock_response.json()
    assert data["message"] == "Successfully unblocked bob_reviewer"
    assert data["unblocked"] == "user_002"

    # Verify block removed
    user_001 = user_controller_instance.user_dao.get_user("user_001")
    user_002 = user_controller_instance.user_dao.get_user("user_002")
    assert "user_002" not in user_001.get("blocked_users", [])
    assert "user_001" not in user_002.get("blocked_users", [])


def test_blocked_users_cannot_follow():
    """Test that blocked users cannot follow each other"""
    # Block user_002
    user_controller_instance.user_dao.block_user("user_001", "user_002")

    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token = login_response.cookies.get("session_token")

    # Try to follow user_002 (blocked)
    follow_response = client.post(
        "/users/user_002/follow",
        cookies={"session_token": token}
    )
    # Should fail because they're blocked
    assert follow_response.status_code == 400


def test_block_idempotent():
    """Test that blocking the same user multiple times is idempotent"""
    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token = login_response.cookies.get("session_token")

    # Block user_002 twice
    client.post("/users/user_002/block", cookies={"session_token": token})
    client.post("/users/user_002/block", cookies={"session_token": token})

    # Verify only one block exists
    user_001 = user_controller_instance.user_dao.get_user("user_001")
    assert user_001["blocked_users"].count("user_002") == 1


def test_unblock_idempotent():
    """Test that unblocking when not blocked is idempotent"""
    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token = login_response.cookies.get("session_token")

    # Unblock user_002 (not blocked)
    response = client.delete(
        "/users/user_002/block",
        cookies={"session_token": token}
    )
    assert response.status_code == 200


def test_is_blocked_functionality():
    """Test the is_blocked helper method"""
    # Block user_002
    user_controller_instance.user_dao.block_user("user_001", "user_002")

    # Test is_blocked
    assert user_controller_instance.user_dao.is_blocked(
        "user_001", "user_002"
    ) is True
    assert user_controller_instance.user_dao.is_blocked(
        "user_002", "user_001"
    ) is True
    assert user_controller_instance.user_dao.is_blocked(
        "user_001", "user_003"
    ) is False


def test_block_nonexistent_user_fails():
    """Test that blocking a nonexistent user fails"""
    # Login as user_001
    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Password123!"}
    )
    token = login_response.cookies.get("session_token")

    # Try to block nonexistent user
    block_response = client.post(
        "/users/nonexistent_user/block",
        cookies={"session_token": token}
    )
    assert block_response.status_code == 404
