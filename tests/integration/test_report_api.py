import pytest
from fastapi.testclient import TestClient
from keyboard_smashers.api import app
from keyboard_smashers.auth import sessions
import tempfile
from pathlib import Path


@pytest.fixture(scope="function")
def test_data_files():
    """Create temporary CSV files for testing."""
    # Create temp users CSV
    users_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    users_file.write(
        "userid,username,email,password,reputation,creation_date,"
        "is_admin,total_reviews,total_penalty_count\n"
    )
    users_file.close()

    # Create temp movies CSV
    movies_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    movies_file.write("movie_id,title,genre,year,director,description\n")
    movies_file.write(
        "movie_001,Test Movie,Action,2024,Test Director,A test movie\n"
    )
    movies_file.close()

    # Create temp reviews CSV
    reviews_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    reviews_file.write(
        "operation,review_id,movie_id,user_id,imdb_username,rating,"
        "review_text,review_date\n"
    )
    reviews_file.close()

    # Create temp reports CSV
    reports_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    reports_file.write("report_id,review_id,reporting_user_id,timestamp\n")
    reports_file.close()

    # Patch the DAOs to use temp files
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )
    from keyboard_smashers.controllers.movie_controller import (
        movie_controller_instance
    )
    from keyboard_smashers.controllers.review_controller import (
        review_controller_instance
    )

    original_users_path = user_controller_instance.user_dao.csv_path
    original_movies_path = movie_controller_instance.movie_dao.csv_path
    original_reviews_path = (
        review_controller_instance.review_dao.new_reviews_csv_path
    )
    original_reports_path = review_controller_instance.report_dao.csv_path

    user_controller_instance.user_dao.csv_path = users_file.name
    user_controller_instance.user_dao.load_users()

    movie_controller_instance.movie_dao.csv_path = movies_file.name
    movie_controller_instance.movie_dao._load_movies()

    review_controller_instance.review_dao.new_reviews_csv_path = (
        reviews_file.name
    )
    review_controller_instance.report_dao.csv_path = reports_file.name
    review_controller_instance.report_dao.load_reports()

    yield {
        'users': users_file.name,
        'movies': movies_file.name,
        'reviews': reviews_file.name,
        'reports': reports_file.name
    }

    # Restore original paths and reload
    user_controller_instance.user_dao.csv_path = original_users_path
    user_controller_instance.user_dao.load_users()

    movie_controller_instance.movie_dao.csv_path = original_movies_path
    movie_controller_instance.movie_dao._load_movies()

    review_controller_instance.review_dao.new_reviews_csv_path = (
        original_reviews_path
    )
    review_controller_instance.report_dao.csv_path = original_reports_path
    review_controller_instance.report_dao.load_reports()

    # Cleanup temp files
    for path in [
        users_file.name, movies_file.name,
        reviews_file.name, reports_file.name
    ]:
        try:
            Path(path).unlink()
        except Exception:
            pass


@pytest.fixture
def client(test_data_files):
    """Create a TestClient with isolated test data."""
    # Clear sessions before each test
    sessions.clear()
    return TestClient(app)


class TestReportingIntegration:
    """End-to-end integration tests for review reporting."""

    def test_full_reporting_workflow(self, client, test_data_files):
        """Test complete workflow: create users, login, create review,
        report it.
        """

        # Step 1: Create first user (reviewer)
        response = client.post("/users/register", json={
            "username": "reviewer_user",
            "email": "reviewer@test.com",
            "password": "Password123!"
        })
        assert response.status_code == 201
        reviewer_id = response.json()["userid"]

        # Step 2: Create second user (reporter)
        response = client.post("/users/register", json={
            "username": "reporter_user",
            "email": "reporter@test.com",
            "password": "Password456!"
        })
        assert response.status_code == 201
        reporter_id = response.json()["userid"]

        # Step 3: Login as reviewer
        response = client.post("/users/login", json={
            "email": "reviewer@test.com",
            "password": "Password123!"
        })
        assert response.status_code == 200
        reviewer_session = response.cookies.get("session_token")
        assert reviewer_session is not None

        # Step 4: Create a review as reviewer
        response = client.post(
            "/reviews/",
            json={
                "movie_id": "movie_001",
                "rating": 4.5,
                "review_text": "Great movie!"
            },
            cookies={"session_token": reviewer_session}
        )
        assert response.status_code == 201
        review_data = response.json()
        review_id = review_data["review_id"]
        assert review_data["movie_id"] == "movie_001"
        assert review_data["rating"] == 4.5
        assert review_data["user_id"] == reviewer_id

        # Step 5: Login as reporter
        response = client.post("/users/login", json={
            "email": "reporter@test.com",
            "password": "Password456!"
        })
        assert response.status_code == 200
        reporter_session = response.cookies.get("session_token")
        assert reporter_session is not None

        # Step 6: Report the review as reporter
        response = client.post(
            f"/reviews/{review_id}/report",
            cookies={"session_token": reporter_session}
        )
        assert response.status_code == 201
        report_data = response.json()
        assert report_data["message"] == "Review reported successfully"
        assert "report_id" in report_data

        # Step 7: Verify the report was saved to CSV
        import csv
        with open(test_data_files['reports'], 'r') as f:
            reader = csv.DictReader(f)
            reports = list(reader)
            assert len(reports) == 1
            assert reports[0]['review_id'] == review_id
            assert reports[0]['reporting_user_id'] == reporter_id
            assert reports[0]['report_id'] == report_data['report_id']

    def test_cannot_report_twice(self, client, test_data_files):
        """Test that a user cannot report the same review twice."""

        # Create users
        client.post("/users/register", json={
            "username": "user1",
            "email": "user1@test.com",
            "password": "Password1!"
        })
        client.post("/users/register", json={
            "username": "user2",
            "email": "user2@test.com",
            "password": "Password2!"
        })

        # User1 creates review
        response = client.post("/users/login", json={
            "email": "user1@test.com",
            "password": "Password1!"
        })
        user1_session = response.cookies.get("session_token")

        response = client.post(
            "/reviews/",
            json={
                "movie_id": "movie_001",
                "rating": 3.0,
                "review_text": "Okay"
            },
            cookies={"session_token": user1_session}
        )
        review_id = response.json()["review_id"]

        # User2 reports review
        response = client.post("/users/login", json={
            "email": "user2@test.com",
            "password": "Password2!"
        })
        user2_session = response.cookies.get("session_token")

        response = client.post(
            f"/reviews/{review_id}/report",
            cookies={"session_token": user2_session}
        )
        assert response.status_code == 201

        # User2 tries to report again
        response = client.post(
            f"/reviews/{review_id}/report",
            cookies={"session_token": user2_session}
        )
        assert response.status_code == 400
        assert "already reported" in response.json()["detail"]

    def test_cannot_report_without_authentication(self, client):
        """Test that unauthenticated users cannot report reviews."""
        response = client.post("/reviews/fake_review_id/report")
        assert response.status_code == 401

    def test_cannot_report_nonexistent_review(self, client, test_data_files):
        """Test that reporting a non-existent review returns 404."""

        # Create and login user
        client.post("/users/register", json={
            "username": "user",
            "email": "user@test.com",
            "password": "Password1!"
        })
        response = client.post("/users/login", json={
            "email": "user@test.com",
            "password": "Password1!"
        })
        session = response.cookies.get("session_token")

        # Try to report non-existent review
        response = client.post(
            "/reviews/nonexistent_review/report",
            cookies={"session_token": session}
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_multiple_users_can_report_same_review(
        self, client, test_data_files
    ):
        """Test that multiple different users can report the same
        review.
        """

        # Create three users with unique names for this test
        for i in range(1, 4):
            client.post("/users/register", json={
                "username": f"multi_user{i}",
                "email": f"multi_user{i}@test.com",
                "password": f"Password{i}!"
            })

        # User1 creates review
        response = client.post("/users/login", json={
            "email": "multi_user1@test.com",
            "password": "Password1!"
        })
        user1_session = response.cookies.get("session_token")

        response = client.post(
            "/reviews/",
            json={
                "movie_id": "movie_001",
                "rating": 2.0,
                "review_text": "Bad"
            },
            cookies={"session_token": user1_session}
        )
        review_id = response.json()["review_id"]

        # User2 and User3 both report the same review
        for i in [2, 3]:
            response = client.post("/users/login", json={
                "email": f"multi_user{i}@test.com",
                "password": f"Password{i}!"
            })
            session = response.cookies.get("session_token")

            response = client.post(
                f"/reviews/{review_id}/report",
                cookies={"session_token": session}
            )
            assert response.status_code == 201

        # Verify 2 reports in CSV for this specific review
        import csv
        with open(test_data_files['reports'], 'r') as f:
            reader = csv.DictReader(f)
            reports = list(reader)
            # Filter reports for this specific review
            review_reports = [
                r for r in reports if r['review_id'] == review_id]
            assert len(review_reports) == 2
            assert all(r['review_id'] == review_id for r in review_reports)
