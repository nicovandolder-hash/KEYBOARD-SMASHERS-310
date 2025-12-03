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

    return user_id, token


def test_block_user_success(client):
    """Test successfully blocking a user"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, _ = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # Alice blocks Bob
    response = client.post(
        f"/users/{bob_id}/block",
        cookies={"session_token": alice_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Successfully blocked bob"
    assert data["blocked"] == bob_id

    # Verify bidirectional blocking
    user_dao = user_controller_instance.user_dao
    alice = user_dao.get_user(alice_id)
    bob = user_dao.get_user(bob_id)
    assert bob_id in alice["blocked_users"]
    assert alice_id in bob["blocked_users"]


def test_block_self_fails(client):
    """Test that users cannot block themselves"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")

    response = client.post(
        f"/users/{alice_id}/block",
        cookies={"session_token": alice_token}
    )
    assert response.status_code == 400
    assert "Cannot block yourself" in response.json()["detail"]


def test_block_nonexistent_user_fails(client):
    """Test that blocking a nonexistent user fails"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")

    response = client.post(
        "/users/nonexistent_user/block",
        cookies={"session_token": alice_token}
    )
    assert response.status_code == 404


def test_block_requires_authentication(client):
    """Test that blocking requires authentication"""
    alice_id, _ = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, _ = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # Clear cookies to simulate unauthenticated request
    client.cookies.clear()

    response = client.post(f"/users/{bob_id}/block")
    assert response.status_code == 401


def test_block_removes_follow_relationships(client):
    """Test that blocking removes existing follow relationships"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, bob_token = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # Alice follows Bob and Bob follows Alice
    client.post(f"/users/{bob_id}/follow",
                cookies={"session_token": alice_token})
    client.post(
        f"/users/{alice_id}/follow",
        cookies={
            "session_token": bob_token})

    # Verify follow relationships exist
    user_dao = user_controller_instance.user_dao
    alice = user_dao.get_user(alice_id)
    bob = user_dao.get_user(bob_id)
    assert bob_id in alice["following"]
    assert alice_id in bob["following"]

    # Alice blocks Bob
    client.post(
        f"/users/{bob_id}/block",
        cookies={
            "session_token": alice_token})

    # Verify follow relationships are removed
    alice = user_dao.get_user(alice_id)
    bob = user_dao.get_user(bob_id)
    assert bob_id not in alice.get("following", [])
    assert alice_id not in bob.get("following", [])
    assert alice_id not in alice.get("followers", [])
    assert bob_id not in bob.get("followers", [])


def test_block_prevents_following(client):
    """Test that blocked users cannot follow each other"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, bob_token = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # Alice blocks Bob
    client.post(
        f"/users/{bob_id}/block",
        cookies={
            "session_token": alice_token})

    # Alice tries to follow Bob
    response1 = client.post(
        f"/users/{bob_id}/follow",
        cookies={
            "session_token": alice_token})
    assert response1.status_code == 400
    assert "blocked" in response1.json()["detail"].lower()

    # Bob tries to follow Alice
    response2 = client.post(
        f"/users/{alice_id}/follow",
        cookies={
            "session_token": bob_token})
    assert response2.status_code == 400
    assert "blocked" in response2.json()["detail"].lower()


def test_block_idempotent(client):
    """Test that blocking the same user twice is idempotent"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, _ = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # Block once
    response1 = client.post(
        f"/users/{bob_id}/block",
        cookies={
            "session_token": alice_token})
    assert response1.status_code == 200

    # Block again
    response2 = client.post(
        f"/users/{bob_id}/block",
        cookies={
            "session_token": alice_token})
    assert response2.status_code == 200

    # Verify only one block exists
    user_dao = user_controller_instance.user_dao
    alice = user_dao.get_user(alice_id)
    assert alice["blocked_users"].count(bob_id) == 1


def test_unblock_user_success(client):
    """Test successfully unblocking a user"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, _ = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # First block
    client.post(
        f"/users/{bob_id}/block",
        cookies={
            "session_token": alice_token})

    # Then unblock
    response = client.delete(
        f"/users/{bob_id}/block",
        cookies={
            "session_token": alice_token})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Successfully unblocked bob"

    # Verify block removed bidirectionally
    user_dao = user_controller_instance.user_dao
    alice = user_dao.get_user(alice_id)
    bob = user_dao.get_user(bob_id)
    assert bob_id not in alice.get("blocked_users", [])
    assert alice_id not in bob.get("blocked_users", [])


def test_unblock_requires_authentication(client):
    """Test that unblocking requires authentication"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, _ = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # Block first (using alice's token)
    client.cookies.clear()
    client.cookies.set("session_token", alice_token)
    client.post(
        f"/users/{bob_id}/block",
        cookies={
            "session_token": alice_token})

    # Clear cookies to simulate unauthenticated request
    client.cookies.clear()

    # Try to unblock without authentication
    response = client.delete(f"/users/{bob_id}/block")
    assert response.status_code == 401


def test_unblock_allows_following_again(client):
    """Test that users can follow each other again after unblocking"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, bob_token = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # Alice blocks Bob
    client.post(
        f"/users/{bob_id}/block",
        cookies={
            "session_token": alice_token})

    # Alice unblocks Bob
    client.delete(f"/users/{bob_id}/block",
                  cookies={"session_token": alice_token})

    # Now Alice should be able to follow Bob
    response1 = client.post(
        f"/users/{bob_id}/follow",
        cookies={
            "session_token": alice_token})
    assert response1.status_code == 200

    # And Bob should be able to follow Alice
    response2 = client.post(
        f"/users/{alice_id}/follow",
        cookies={
            "session_token": bob_token})
    assert response2.status_code == 200


def test_get_blocked_users_empty(client):
    """Test getting blocked users when none are blocked"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")

    response = client.get(
        "/users/me/blocked",
        cookies={
            "session_token": alice_token})
    assert response.status_code == 200
    data = response.json()
    assert data["blocked_users"] == []
    assert data["total"] == 0


def test_get_blocked_users_list(client):
    """Test getting list of blocked users"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, _ = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")
    charlie_id, _ = create_and_login_user(
        client, "charlie", "charlie@example.com", "CharliePass123!")

    # Alice blocks Bob and Charlie
    client.post(
        f"/users/{bob_id}/block",
        cookies={
            "session_token": alice_token})
    client.post(f"/users/{charlie_id}/block",
                cookies={"session_token": alice_token})

    # Get blocked users
    response = client.get(
        "/users/me/blocked",
        cookies={
            "session_token": alice_token})
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 2
    assert len(data["blocked_users"]) == 2

    # Check that both users are in the list
    blocked_ids = [user["userid"] for user in data["blocked_users"]]
    assert bob_id in blocked_ids
    assert charlie_id in blocked_ids

    # Check structure
    for user in data["blocked_users"]:
        assert "userid" in user
        assert "username" in user


def test_get_blocked_users_after_unblock(client):
    """Test that unblocking removes user from blocked list"""
    alice_id, alice_token = create_and_login_user(
        client, "alice", "alice@example.com", "AlicePass123!")
    bob_id, _ = create_and_login_user(
        client, "bob", "bob@example.com", "BobPass123!")

    # Block
    client.post(
        f"/users/{bob_id}/block",
        cookies={
            "session_token": alice_token})

    # Verify blocked
    response1 = client.get(
        "/users/me/blocked",
        cookies={
            "session_token": alice_token})
    assert response1.json()["total"] == 1

    # Unblock
    client.delete(f"/users/{bob_id}/block",
                  cookies={"session_token": alice_token})

    # Verify unblocked
    response2 = client.get(
        "/users/me/blocked",
        cookies={
            "session_token": alice_token})
    assert response2.json()["total"] == 0


def test_get_blocked_users_requires_auth(client):
    """Test that getting blocked users requires authentication"""
    response = client.get("/users/me/blocked")
    assert response.status_code == 401
