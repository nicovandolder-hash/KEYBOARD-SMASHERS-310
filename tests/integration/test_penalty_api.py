import pytest
from fastapi.testclient import TestClient
from keyboard_smashers.api import app
from keyboard_smashers.auth import sessions
from datetime import datetime, timedelta
import secrets
import tempfile
import os
import pandas as pd


@pytest.fixture
def temp_penalty_csv():
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "test_penalties.csv")

    pd.DataFrame(columns=[
        'penalty_id', 'user_id', 'reason', 'severity',
        'start_date', 'end_date', 'issued_by', 'created_at'
    ]).to_csv(csv_path, index=False)

    yield csv_path

    if os.path.exists(csv_path):
        os.remove(csv_path)
    os.rmdir(temp_dir)


@pytest.fixture
def temp_user_csv():
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "test_users.csv")

    pd.DataFrame(columns=[
        'userid', 'username', 'email', 'password',
        'reputation', 'creation_date', 'is_admin',
        'total_reviews', 'total_penalty_count'
    ]).to_csv(csv_path, index=False)

    yield csv_path

    if os.path.exists(csv_path):
        os.remove(csv_path)
    os.rmdir(temp_dir)


@pytest.fixture(autouse=True)
def setup_test_controllers(temp_penalty_csv, temp_user_csv):
    from keyboard_smashers.controllers import (
        penalty_controller, user_controller)
    from keyboard_smashers.controllers.penalty_controller import (
        PenaltyController)
    from keyboard_smashers.controllers.user_controller import UserController

    original_penalty_controller = (
        penalty_controller.penalty_controller_instance)
    original_user_controller = user_controller.user_controller_instance

    PenaltyController.penalty_dao = None
    PenaltyController.user_dao = None
    UserController.user_dao = None

    test_penalty_controller = PenaltyController(
        penalty_csv_path=temp_penalty_csv,
        user_csv_path=temp_user_csv
    )
    test_user_controller = UserController(csv_path=temp_user_csv)

    penalty_controller.penalty_controller_instance = test_penalty_controller
    user_controller.user_controller_instance = test_user_controller

    original_sessions = sessions.copy()
    sessions.clear()

    yield

    penalty_controller.penalty_controller_instance = (
        original_penalty_controller)
    user_controller.user_controller_instance = original_user_controller
    sessions.clear()
    sessions.update(original_sessions)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_client():
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )
    from keyboard_smashers.models.user_model import User

    client = TestClient(app)

    admin_id = 'test_admin'
    if admin_id not in user_controller_instance.user_dao.users:
        temp_user = User(
            userid=admin_id,
            username='Test Admin',
            email='admin@test.com',
            reputation=3,
            is_admin=True
        )
    temp_user.set_password('AdminPass123!')

    admin_user_data = {
        'userid': admin_id,
        'username': 'Test Admin',
        'email': 'admin@test.com',
        'password': 'AdminPass123!',
        'reputation': 3,
        'creation_date': datetime.now(),
        'is_admin': True,
        'total_reviews': 0,
        'total_penalty_count': 0
    }

    user_controller_instance.user_dao.users[admin_id] = admin_user_data
    user_controller_instance.user_dao.email_index['admin@test.com'] = admin_id
    user_controller_instance.user_dao.save_users()

    session_token = secrets.token_urlsafe(32)
    sessions[session_token] = {
        'user_id': 'test_admin',
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(hours=2),
        'is_admin': True
    }

    client.cookies.set("session_token", session_token)

    yield client

    if session_token in sessions:
        del sessions[session_token]
    client.cookies.clear()


@pytest.fixture
def regular_client():
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )
    from keyboard_smashers.models.user_model import User

    client = TestClient(app)

    user_id = 'test_user'
    if user_id not in user_controller_instance.user_dao.users:
        temp_user = User(
            userid=user_id,
            username='Test User',
            email='user@test.com',
            reputation=3,
            is_admin=False
        )
        temp_user.set_password('UserPass123!')

    user_data = {
        'userid': user_id,
        'username': 'Test User',
        'email': 'user@test.com',
        'password': temp_user.password,
        'reputation': 3,
        'creation_date': datetime.now(),
        'is_admin': False,
        'total_reviews': 0,
        'total_penalty_count': 0
    }

    user_controller_instance.user_dao.users[user_id] = user_data
    user_controller_instance.user_dao.email_index['user@test.com'] = user_id
    user_controller_instance.user_dao.save_users()

    session_token = secrets.token_urlsafe(32)
    sessions[session_token] = {
        'user_id': 'test_user',
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(hours=2),
        'is_admin': False
    }

    client.cookies.set("session_token", session_token)

    yield client

    if session_token in sessions:
        del sessions[session_token]
    client.cookies.clear()
    client.cookies.clear()


class TestPenaltyAPIPublicEndpoints:

    def test_get_my_penalties_without_auth(self, client):
        response = client.get("/penalties/my-penalties")
        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    def test_get_my_penalties_with_auth_no_penalties(self, regular_client):
        response = regular_client.get("/penalties/my-penalties")
        assert response.status_code == 200
        data = response.json()
        assert "penalties" in data
        assert len(data["penalties"]) == 0

    def test_get_my_penalties_with_status_filter_active(
            self, regular_client, admin_client):
        penalty_data = {
            "user_id": "test_user",
            "reason": "Active violation that is long enough",
            "severity": 2
        }
        admin_client.post("/penalties/", json=penalty_data)

        response = regular_client.get("/penalties/my-penalties?status=active")
        assert response.status_code == 200
        data = response.json()
        penalties = data["penalties"]
        assert all(p["is_active"] for p in penalties)

    def test_get_my_penalties_with_status_filter_inactive(
            self, regular_client, admin_client):
        response = regular_client.get(
            "/penalties/my-penalties?status=inactive")
        assert response.status_code == 200
        data = response.json()
        penalties = data["penalties"]
        assert all(not p["is_active"] for p in penalties)


class TestPenaltyAPIAdminEndpoints:

    def test_create_penalty_without_auth(self, client):
        penalty_data = {
            "user_id": "test_user",
            "reason": "Test violation that is long enough",
            "severity": 3
        }
        response = client.post("/penalties/", json=penalty_data)
        assert response.status_code == 401

    def test_create_penalty_with_regular_user(self, regular_client):
        penalty_data = {
            "user_id": "test_user",
            "reason": "Test violation that is long enough",
            "severity": 3
        }
        response = regular_client.post("/penalties/", json=penalty_data)
        assert response.status_code == 403
        assert "admin privileges required" in response.json()["detail"].lower()

    def test_create_penalty_with_admin_success(self, admin_client):
        penalty_data = {
            "user_id": "test_admin",
            "reason": "Violated community guidelines repeatedly",
            "severity": 4
        }
        response = admin_client.post("/penalties/", json=penalty_data)
        assert response.status_code == 201
        penalty = response.json()
        assert penalty["user_id"] == "test_admin"
        assert penalty["severity"] == 4
        assert penalty["issued_by"] == "test_admin"
        assert "penalty_id" in penalty
        assert penalty["is_active"] is True

    def test_create_penalty_validation_error_invalid_severity(
            self, admin_client):
        penalty_data = {
            "user_id": "test_admin",
            "reason": "Test violation that is long enough",
            "severity": 6
        }
        response = admin_client.post("/penalties/", json=penalty_data)
        assert response.status_code == 422

    def test_create_penalty_nonexistent_user(self, admin_client):
        penalty_data = {
            "user_id": "nonexistent_user_xyz",
            "reason": "Test violation that is long enough",
            "severity": 3
        }
        response = admin_client.post("/penalties/", json=penalty_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_all_penalties_without_auth(self, client):
        response = client.get("/penalties/")
        assert response.status_code == 401

    def test_get_all_penalties_with_regular_user(self, regular_client):
        response = regular_client.get("/penalties/")
        assert response.status_code == 403

    def test_get_all_penalties_with_admin(self, admin_client):
        response = admin_client.get("/penalties/")
        assert response.status_code == 200
        data = response.json()
        assert "penalties" in data

    def test_get_all_penalties_with_user_filter(self, admin_client):
        penalty_data = {
            "user_id": "test_admin",
            "reason": "Test violation that is long enough",
            "severity": 3
        }
        admin_client.post("/penalties/", json=penalty_data)

        response = admin_client.get("/penalties/?user_id=test_admin")
        assert response.status_code == 200
        data = response.json()
        penalties = data["penalties"]
        assert all(p["user_id"] == "test_admin" for p in penalties)

    def test_get_all_penalties_with_status_filter(self, admin_client):
        response = admin_client.get("/penalties/?status=active")
        assert response.status_code == 200
        data = response.json()
        penalties = data["penalties"]
        assert all(p["is_active"] for p in penalties)

    def test_get_all_penalties_invalid_status(self, admin_client):
        response = admin_client.get("/penalties/?status=invalid")
        assert response.status_code == 400
        assert "invalid status" in response.json()["detail"].lower()

    def test_get_penalty_by_id_without_auth(self, client):
        response = client.get("/penalties/penalty_001")
        assert response.status_code == 401

    def test_get_penalty_by_id_with_regular_user(self, regular_client):
        response = regular_client.get("/penalties/penalty_001")
        assert response.status_code == 403

    def test_get_penalty_by_id_with_admin(self, admin_client):
        penalty_data = {
            "user_id": "test_admin",
            "reason": "Test violation that is long enough",
            "severity": 3
        }
        create_response = admin_client.post("/penalties/", json=penalty_data)
        penalty_id = create_response.json()["penalty_id"]

        response = admin_client.get(f"/penalties/{penalty_id}")
        assert response.status_code == 200
        penalty = response.json()
        assert penalty["penalty_id"] == penalty_id

    def test_get_penalty_by_id_not_found(self, admin_client):
        response = admin_client.get("/penalties/penalty_999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_penalty_without_auth(self, client):
        update_data = {"severity": 5}
        response = client.put("/penalties/penalty_001", json=update_data)
        assert response.status_code == 401

    def test_update_penalty_with_regular_user(self, regular_client):
        update_data = {"severity": 5}
        response = regular_client.put(
            "/penalties/penalty_001", json=update_data)
        assert response.status_code == 403

    def test_update_penalty_with_admin_success(self, admin_client):
        penalty_data = {
            "user_id": "test_admin",
            "reason": "Original violation reason",
            "severity": 2
        }
        create_response = admin_client.post("/penalties/", json=penalty_data)
        penalty_id = create_response.json()["penalty_id"]

        update_data = {
            "reason": "Updated violation reason for testing",
            "severity": 4
        }
        response = admin_client.put(
            f"/penalties/{penalty_id}", json=update_data)
        assert response.status_code == 200
        penalty = response.json()
        assert penalty["reason"] == "Updated violation reason for testing"
        assert penalty["severity"] == 4

    def test_update_penalty_not_found(self, admin_client):
        update_data = {"severity": 5}
        response = admin_client.put("/penalties/penalty_999", json=update_data)
        assert response.status_code == 404

    def test_delete_penalty_without_auth(self, client):
        response = client.delete("/penalties/penalty_001")
        assert response.status_code == 401

    def test_delete_penalty_with_regular_user(self, regular_client):
        response = regular_client.delete("/penalties/penalty_001")
        assert response.status_code == 403

    def test_delete_penalty_with_admin_success(self, admin_client):
        penalty_data = {
            "user_id": "test_admin",
            "reason": "Test violation that is long enough",
            "severity": 3
        }
        create_response = admin_client.post("/penalties/", json=penalty_data)
        penalty_id = create_response.json()["penalty_id"]

        response = admin_client.delete(f"/penalties/{penalty_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"].lower()

        get_response = admin_client.get(f"/penalties/{penalty_id}")
        assert get_response.status_code == 404

    def test_delete_penalty_not_found(self, admin_client):
        response = admin_client.delete("/penalties/penalty_999")
        assert response.status_code == 404


class TestPenaltyAPIDataPersistence:

    def test_penalty_persists_across_requests(self, admin_client):
        penalty_data = {
            "user_id": "test_admin",
            "reason": "Persistence test violation",
            "severity": 3
        }
        create_response = admin_client.post("/penalties/", json=penalty_data)
        assert create_response.status_code == 201
        penalty_id = create_response.json()["penalty_id"]

        get_response = admin_client.get(f"/penalties/{penalty_id}")
        assert get_response.status_code == 200
        assert get_response.json()["penalty_id"] == penalty_id

        list_response = admin_client.get("/penalties/")
        assert list_response.status_code == 200
        data = list_response.json()
        penalty_ids = [p["penalty_id"] for p in data["penalties"]]
        assert penalty_id in penalty_ids

    def test_update_persists_across_requests(self, admin_client):
        penalty_data = {
            "user_id": "test_admin",
            "reason": "Original reason for testing",
            "severity": 2
        }
        create_response = admin_client.post("/penalties/", json=penalty_data)
        penalty_id = create_response.json()["penalty_id"]

        update_data = {"severity": 5}
        admin_client.put(f"/penalties/{penalty_id}", json=update_data)

        get_response = admin_client.get(f"/penalties/{penalty_id}")
        assert get_response.json()["severity"] == 5


class TestPenaltyAPIMultipleCases:

    def test_create_multiple_penalties_same_user(self, admin_client):
        penalty_data_1 = {
            "user_id": "test_admin",
            "reason": "First violation that is long enough",
            "severity": 2
        }
        penalty_data_2 = {
            "user_id": "test_admin",
            "reason": "Second violation that is long enough",
            "severity": 3
        }

        response_1 = admin_client.post("/penalties/", json=penalty_data_1)
        response_2 = admin_client.post("/penalties/", json=penalty_data_2)

        assert response_1.status_code == 201
        assert response_2.status_code == 201

        penalties_response = admin_client.get("/penalties/?user_id=test_admin")
        penalties = penalties_response.json()
        assert len(penalties) >= 2


class TestPenaltyAPIComplexScenario:

    def test_full_penalty_lifecycle(self, admin_client, regular_client):
        """Test create, read, update, delete."""

        penalty_data = {
            "user_id": "test_user",
            "reason": "Lifecycle test violation",
            "severity": 2
        }
        create_response = admin_client.post("/penalties/", json=penalty_data)
        assert create_response.status_code == 201
        penalty_id = create_response.json()["penalty_id"]

        get_response = admin_client.get(f"/penalties/{penalty_id}")
        assert get_response.status_code == 200

        user_penalties = regular_client.get("/penalties/my-penalties")
        assert user_penalties.status_code == 200
        data = user_penalties.json()
        assert any(p["penalty_id"] ==
                   penalty_id for p in data["penalties"])

        update_data = {"severity": 5}
        update_response = admin_client.put(
            f"/penalties/{penalty_id}", json=update_data)
        assert update_response.status_code == 200
        assert update_response.json()["severity"] == 5

        delete_response = admin_client.delete(f"/penalties/{penalty_id}")
        assert delete_response.status_code == 200

        get_after_delete = admin_client.get(f"/penalties/{penalty_id}")
        assert get_after_delete.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
