import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from keyboard_smashers.api import app
from keyboard_smashers.controllers.user_controller import (
    user_controller_instance
)
from keyboard_smashers.controllers.review_controller import (
    review_controller_instance
)
from keyboard_smashers.dao.user_dao import UserDAO

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_test_data():
    """
    Clean up test data before and after each test.
    In-memory only, no file writes.
    """
    # Use the singleton instances that the API actually uses
    user_dao = user_controller_instance.user_dao
    review_dao = review_controller_instance.review_dao

    # Clear all in-memory data structures
    user_dao.users.clear()
    user_dao.email_index.clear()
    user_dao.username_index.clear()
    user_dao.user_counter = 1
    review_dao.reviews.clear()
    review_dao.reviews_by_movie.clear()
    review_dao.reviews_by_user.clear()

    # Clear sessions
    from keyboard_smashers.auth import sessions
    sessions.clear()

    # Mock save_users to prevent writing to real CSV files
    with patch.object(user_dao, 'save_users', MagicMock()):
        yield

    # Cleanup after test (in-memory only)
    user_dao.users.clear()
    user_dao.email_index.clear()
    user_dao.username_index.clear()
    user_dao.user_counter = 1
    review_dao.reviews.clear()
    review_dao.reviews_by_movie.clear()
    review_dao.reviews_by_user.clear()
    sessions.clear()


def test_get_notifications_requires_auth():
    """Test that getting notifications requires authentication"""
    response = client.get("/users/me/notifications")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


def test_get_notifications_empty():
    """Test getting notifications when there are none"""
    # Register and login
    client.post("/users/register", json={
        "username": "alice",
        "email": "alice@test.com",
        "password": "Password123!"
    })
    login_response = client.post("/users/login", json={
        "email": "alice@test.com",
        "password": "Password123!"
    })
    assert login_response.status_code == 200

    # Get notifications
    response = client.get("/users/me/notifications",
                          cookies=login_response.cookies)
    assert response.status_code == 200
    data = response.json()
    assert data["notifications"] == []
    assert data["total"] == 0
    assert data["unread"] == 0


def test_get_notifications_after_follow():
    """Test that follow notifications appear in the endpoint"""
    # Create two users
    client.post("/users/register", json={
        "username": "alice",
        "email": "alice@test.com",
        "password": "Password123!"
    })
    client.post("/users/register", json={
        "username": "bob",
        "email": "bob@test.com",
        "password": "Password456!"
    })

    # Login as alice
    alice_login = client.post("/users/login", json={
        "email": "alice@test.com",
        "password": "Password123!"
    })
    assert alice_login.status_code == 200

    # Login as bob
    bob_login = client.post("/users/login", json={
        "email": "bob@test.com",
        "password": "Password456!"
    })
    assert bob_login.status_code == 200

    # Alice follows bob
    follow_response = client.post(
        "/users/user_002/follow", cookies=alice_login.cookies)
    assert follow_response.status_code == 200

    # Bob checks notifications
    response = client.get("/users/me/notifications", cookies=bob_login.cookies)
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["unread"] == 1
    assert len(data["notifications"]) == 1

    notification = data["notifications"][0]
    assert notification["event_type"] == "user_follow"
    assert "alice" in notification["data"]["message"]
    assert "timestamp" in notification


def test_get_notifications_multiple_follows():
    """Test that multiple follow notifications are returned in correct order"""
    # Create three users
    client.post("/users/register", json={
        "username": "alice",
        "email": "alice@test.com",
        "password": "Password123!"
    })
    client.post("/users/register", json={
        "username": "bob",
        "email": "bob@test.com",
        "password": "Password123!"
    })
    client.post("/users/register", json={
        "username": "charlie",
        "email": "charlie@test.com",
        "password": "Password123!"
    })

    # Login as alice
    alice_login = client.post("/users/login", json={
        "email": "alice@test.com",
        "password": "Password123!"
    })

    # Login as bob
    bob_login = client.post("/users/login", json={
        "email": "bob@test.com",
        "password": "Password123!"
    })

    # Login as charlie
    charlie_login = client.post("/users/login", json={
        "email": "charlie@test.com",
        "password": "Password123!"
    })

    # Alice follows charlie
    client.post("/users/user_003/follow", cookies=alice_login.cookies)

    # Bob follows charlie
    client.post("/users/user_003/follow", cookies=bob_login.cookies)

    # Charlie checks notifications
    response = client.get("/users/me/notifications",
                          cookies=charlie_login.cookies)
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert len(data["notifications"]) == 2

    # Notifications should be most recent first (bob, then alice)
    assert "bob" in data["notifications"][0]["data"]["message"]
    assert "alice" in data["notifications"][1]["data"]["message"]


def test_get_notifications_pagination():
    """Test that notification pagination works"""
    # Create target user and 3 followers
    client.post("/users/register", json={
        "username": "target",
        "email": "target@test.com",
        "password": "Password123!"
    })

    target_login = client.post("/users/login", json={
        "email": "target@test.com",
        "password": "Password123!"
    })

    # Create 3 followers
    for i in range(3):
        client.post("/users/register", json={
            "username": f"follower{i}",
            "email": f"follower{i}@test.com",
            "password": "Password123!"
        })
        follower_login = client.post("/users/login", json={
            "email": f"follower{i}@test.com",
            "password": "Password123!"
        })
        # Follow target
        client.post("/users/user_001/follow", cookies=follower_login.cookies)

    # Target checks notifications with pagination
    # Get first 2
    response1 = client.get(
        "/users/me/notifications?limit=2&offset=0",
        cookies=target_login.cookies)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["total"] == 3
    assert len(data1["notifications"]) == 2
    assert data1["limit"] == 2
    assert data1["offset"] == 0

    # Get next 2 (should only have 1)
    response2 = client.get(
        "/users/me/notifications?limit=2&offset=2",
        cookies=target_login.cookies)
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["total"] == 3
    assert len(data2["notifications"]) == 1
    assert data2["offset"] == 2


def test_notifications_persist_after_reload(tmp_path):
    """Test that notifications are saved to CSV and persist across reloads"""
    # Create a temporary CSV file for this test
    temp_csv = tmp_path / "test_users.csv"
    temp_dao = UserDAO(csv_path=str(temp_csv))

    # Manually add users to temp DAO (bypassing create_user which expects dict)
    from datetime import datetime
    temp_dao.users = {
        'user_001': {
            'userid': 'user_001',
            'username': 'alice',
            'email': 'alice@test.com',
            'password': 'hashedpass',
            'reputation': 3,
            'creation_date': datetime.now(),
            'is_admin': False,
            'is_suspended': False,
            'total_reviews': 0,
            'total_penalty_count': 0,
            'favorites': [],
            'following': [],
            'followers': [],
            'blocked_users': [],
            'notifications': []
        },
        'user_002': {
            'userid': 'user_002',
            'username': 'bob',
            'email': 'bob@test.com',
            'password': 'hashedpass',
            'reputation': 3,
            'creation_date': datetime.now(),
            'is_admin': False,
            'is_suspended': False,
            'total_reviews': 0,
            'total_penalty_count': 0,
            'favorites': [],
            'following': [],
            'followers': [],
            'blocked_users': [],
            'notifications': []
        }
    }
    temp_dao.email_index = {
        'alice@test.com': 'user_001', 'bob@test.com': 'user_002'}
    temp_dao.username_index = {'alice': 'user_001', 'bob': 'user_002'}
    temp_dao.user_counter = 3

    # Alice follows bob (this should create a notification for bob)
    temp_dao.follow_user('user_001', 'user_002')

    # Save to CSV (this actually writes)
    temp_dao.save_users()

    # Simulate server restart: create new DAO instance that loads from the
    # same temp file
    reloaded_dao = UserDAO(csv_path=str(temp_csv))

    # Bob should still have the notification
    bob_user = reloaded_dao.get_user('user_002')
    assert "notifications" in bob_user
    assert len(bob_user["notifications"]) == 1
    assert bob_user["notifications"][0]["event_type"] == "user_follow"
    assert "alice" in bob_user["notifications"][0]["data"]["message"]


def test_notifications_invalid_session():
    """Test that invalid session returns 401"""
    response = client.get("/users/me/notifications",
                          cookies={"session": "invalid_token"})
    assert response.status_code == 401
    assert "Invalid session" in response.json()["detail"]
