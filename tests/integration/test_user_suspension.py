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
    # Clear user data
    user_dao = user_controller_instance.user_dao
    user_dao.users.clear()
    user_dao.email_index.clear()
    user_dao.username_index.clear()
    user_dao.user_counter = 1

    # Clear sessions
    auth.sessions.clear()

    yield

    # Cleanup after test
    user_dao.users.clear()
    user_dao.email_index.clear()
    user_dao.username_index.clear()
    user_dao.user_counter = 1
    auth.sessions.clear()


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def admin_client(client):
    """Create an authenticated admin client"""
    # Create admin user
    admin_data = {
        "username": "admin_user",
        "email": "admin@test.com",
        "password": "AdminPass123!"
    }
    create_response = client.post("/users/register", json=admin_data)
    assert create_response.status_code == 201, (
        f"Failed to create admin: {create_response.json()}"
    )
    user_id = create_response.json()["userid"]

    # Make user admin via direct DAO manipulation
    user_dao = user_controller_instance.user_dao
    user_dao.users[user_id]['is_admin'] = True
    user_dao.save_users()

    # Login as admin
    login_response = client.post("/users/login", json={
        "email": "admin@test.com",
        "password": "AdminPass123!"
    })

    # Extract session token from cookies
    session_token = login_response.cookies.get("session_token")
    client.cookies.set("session_token", session_token)

    return client


@pytest.fixture
def regular_client(client):
    """Create an authenticated regular user client"""
    # Create regular user
    user_data = {
        "username": "regular_user",
        "email": "user@test.com",
        "password": "UserPass123!"
    }
    client.post("/users/register", json=user_data)

    # Login as regular user
    login_response = client.post("/users/login", json={
        "email": "user@test.com",
        "password": "UserPass123!"
    })

    session_token = login_response.cookies.get("session_token")
    client.cookies.set("session_token", session_token)

    return client


class TestSuspensionEndpoints:
    """Test suspension API endpoints"""

    def test_suspend_user_without_auth(self, client):
        """Non-authenticated users cannot suspend accounts"""
        response = client.post("/users/user_001/suspend")
        assert response.status_code == 401

    def test_suspend_user_as_regular_user(self, regular_client):
        """Regular users cannot suspend accounts"""
        response = regular_client.post("/users/user_002/suspend")
        assert response.status_code == 403

    def test_suspend_user_as_admin(self, admin_client):
        """Admin can suspend a user account"""
        # Create target user
        target_user_data = {
            "username": "target_user",
            "email": "target@test.com",
            "password": "TargetPass123!"
        }
        create_response = admin_client.post(
            "/users/register", json=target_user_data)
        user_id = create_response.json()["userid"]

        # Suspend user
        response = admin_client.post(f"/users/{user_id}/suspend")
        assert response.status_code == 200
        assert "suspended" in response.json()["message"].lower()

    def test_suspend_nonexistent_user(self, admin_client):
        """Suspending non-existent user returns 404"""
        response = admin_client.post("/users/nonexistent_user/suspend")
        assert response.status_code == 404

    def test_reactivate_user_without_auth(self, client):
        """Non-authenticated users cannot reactivate accounts"""
        response = client.post("/users/user_001/reactivate")
        assert response.status_code == 401

    def test_reactivate_user_as_regular_user(self, regular_client):
        """Regular users cannot reactivate accounts"""
        response = regular_client.post("/users/user_002/reactivate")
        assert response.status_code == 403

    def test_reactivate_user_as_admin(self, admin_client):
        """Admin can reactivate a suspended user"""
        # Create and suspend user
        target_user_data = {
            "username": "target_user",
            "email": "target@test.com",
            "password": "TargetPass123!"
        }
        create_response = admin_client.post(
            "/users/register", json=target_user_data)
        user_id = create_response.json()["userid"]
        admin_client.post(f"/users/{user_id}/suspend")

        # Reactivate user
        response = admin_client.post(f"/users/{user_id}/reactivate")
        assert response.status_code == 200
        assert "reactivated" in response.json()["message"].lower()

    def test_reactivate_nonexistent_user(self, admin_client):
        """Reactivating non-existent user returns 404"""
        response = admin_client.post("/users/nonexistent_user/reactivate")
        assert response.status_code == 404


class TestSuspendedUserLogin:
    """Test login restrictions for suspended users"""

    def test_suspended_user_cannot_login(self, client, admin_client):
        """Suspended users should not be able to login"""
        # Create user
        user_data = {
            "username": "test_user",
            "email": "suspended@test.com",
            "password": "TestPass123!"
        }
        create_response = client.post("/users/register", json=user_data)
        user_id = create_response.json()["userid"]

        # Suspend user
        admin_client.post(f"/users/{user_id}/suspend")

        # Attempt login
        login_response = client.post("/users/login", json={
            "email": "suspended@test.com",
            "password": "TestPass123!"
        })

        assert login_response.status_code == 403
        assert "suspended" in login_response.json()["detail"].lower()

    def test_reactivated_user_can_login(self, client, admin_client):
        """Reactivated users should be able to login"""
        # Create user
        user_data = {
            "username": "test_user",
            "email": "reactivated@test.com",
            "password": "TestPass123!"
        }
        create_response = client.post("/users/register", json=user_data)
        user_id = create_response.json()["userid"]

        # Suspend then reactivate
        admin_client.post(f"/users/{user_id}/suspend")
        admin_client.post(f"/users/{user_id}/reactivate")

        # Attempt login
        login_response = client.post("/users/login", json={
            "email": "reactivated@test.com",
            "password": "TestPass123!"
        })

        assert login_response.status_code == 200
        assert "session_token" in login_response.cookies


class TestSuspendedUserReviewCreation:
    """Test review creation restrictions for suspended users"""

    def test_suspended_user_cannot_create_review(self, admin_client):
        """Suspended users should not be able to create reviews"""
        # Create separate client for reviewer
        reviewer_client = TestClient(app)

        # Create user
        user_data = {
            "username": "reviewer",
            "email": "reviewer@test.com",
            "password": "ReviewPass123!"
        }
        create_response = reviewer_client.post(
            "/users/register", json=user_data)
        user_id = create_response.json()["userid"]

        # Login as user
        login_response = reviewer_client.post("/users/login", json={
            "email": "reviewer@test.com",
            "password": "ReviewPass123!"
        })
        session_token = login_response.cookies.get("session_token")
        reviewer_client.cookies.set("session_token", session_token)

        # Suspend user (using admin)
        suspend_response = admin_client.post(f"/users/{user_id}/suspend")
        assert suspend_response.status_code == 200

        # Attempt to create review (should fail with 401 because session
        # was invalidated)
        review_data = {
            "movie_id": "tt0111161",  # Shawshank Redemption
            "rating": 5,
            "review_text": "Great movie!",
            "review_title": "Excellent"
        }
        review_response = reviewer_client.post("/reviews/", json=review_data)

        # After suspension, user's session is invalidated so they get 401
        assert review_response.status_code == 401
        detail = review_response.json()["detail"].lower()
        assert "invalid" in detail or "expired" in detail or "session" in detail
