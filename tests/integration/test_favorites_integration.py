import pytest
from fastapi.testclient import TestClient
from keyboard_smashers.api import app
from keyboard_smashers.controllers.user_controller import (
    user_controller_instance
)
from keyboard_smashers.controllers.movie_controller import (
    movie_controller_instance
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_data():
    """Set up test data before each test"""
    user_dao = user_controller_instance.user_dao
    movie_dao = movie_controller_instance.movie_dao

    original_users = user_dao.users.copy()
    original_movies = movie_dao.movies.copy()

    user_dao.users.clear()
    user_dao.email_index.clear()
    user_dao.username_index.clear()

    movie_dao.movies.clear()

    from datetime import datetime
    from keyboard_smashers.models.user_model import User

    temp_user = User('testuser', 'test@example.com', 'user_001')
    temp_user.set_password('Test123!@#')

    test_user = {
        'userid': 'user_001',
        'username': 'testuser',
        'email': 'test@example.com',
        'password': temp_user.password,
        'reputation': 3,
        'creation_date': datetime(2025, 1, 1),
        'is_admin': False,
        'is_suspended': False,
        'total_reviews': 0,
        'total_penalty_count': 0,
        'favorites': []
    }

    user_dao.users['user_001'] = test_user
    user_dao.email_index['test@example.com'] = 'user_001'
    user_dao.username_index['testuser'] = 'user_001'

    test_movie = {
        'movie_id': 'movie_001',
        'title': 'Test Movie',
        'genre': 'Action',
        'year': 2020,
        'director': 'Test Director',
        'description': 'A test movie'
    }
    movie_dao.movies['movie_001'] = test_movie

    yield

    user_dao.users = original_users
    user_dao.email_index.clear()
    user_dao.username_index.clear()
    for user_id, user in original_users.items():
        user_dao.email_index[user['email'].lower()] = user_id
        user_dao.username_index[user['username'].lower()] = user_id

    movie_dao.movies = original_movies


class TestFavoritesIntegration:
    """Integration tests for favorites toggling API"""

    def test_add_favorite_success(self):
        """Test successfully adding a movie to favorites"""
        login_response = client.post(
            "/users/login",
            json={"email": "test@example.com", "password": "Test123!@#"}
        )
        assert login_response.status_code == 200
        cookies = login_response.cookies

        response = client.post(
            "/users/user_001/favorites/movie_001",
            cookies=cookies
        )

        assert response.status_code == 200
        data = response.json()
        assert data['added'] is True
        assert 'movie_001' in data['favorites']
        assert "added to" in data['message']

    def test_remove_favorite_success(self):
        """Test successfully removing a movie from favorites"""
        login_response = client.post(
            "/users/login",
            json={"email": "test@example.com", "password": "Test123!@#"}
        )
        cookies = login_response.cookies

        client.post(
            "/users/user_001/favorites/movie_001",
            cookies=cookies
        )

        response = client.post(
            "/users/user_001/favorites/movie_001",
            cookies=cookies
        )

        assert response.status_code == 200
        data = response.json()
        assert data['added'] is False
        assert 'movie_001' not in data['favorites']
        assert "removed from" in data['message']

    def test_toggle_favorite_unauthenticated(self):
        """Test toggling favorite without authentication"""
        # Use a fresh client without cookies
        from fastapi.testclient import TestClient
        from keyboard_smashers.api import app
        fresh_client = TestClient(app)

        response = fresh_client.post("/users/user_001/favorites/movie_001")

        assert response.status_code == 401
        assert "Not authenticated" in response.json()['detail']

    def test_toggle_favorite_wrong_user(self):
        """Test user trying to modify another user's favorites"""
        user_dao = user_controller_instance.user_dao
        from datetime import datetime

        other_user = {
            'userid': 'user_002',
            'username': 'otheruser',
            'email': 'other@example.com',
            'password': (
                '402e3e7d1144746852fd0a89b0c9926d$'
                '84cdefeba603cb67fb3601aa85b1e2f5d5a2f93c0d1277398fd97'
                '50def1f456a'
            ),
            'reputation': 3,
            'creation_date': datetime(2025, 1, 1),
            'is_admin': False,
            'is_suspended': False,
            'total_reviews': 0,
            'total_penalty_count': 0,
            'favorites': []
        }
        user_dao.users['user_002'] = other_user
        user_dao.email_index['other@example.com'] = 'user_002'
        user_dao.username_index['otheruser'] = 'user_002'

        login_response = client.post(
            "/users/login",
            json={"email": "test@example.com", "password": "Test123!@#"}
        )
        cookies = login_response.cookies

        response = client.post(
            "/users/user_002/favorites/movie_001",
            cookies=cookies
        )

        assert response.status_code == 403
        assert "Can only modify your own favorites" in (
            response.json()['detail']
        )

    def test_toggle_favorite_invalid_movie(self):
        """Test toggling favorite with non-existent movie"""
        login_response = client.post(
            "/users/login",
            json={"email": "test@example.com", "password": "Test123!@#"}
        )
        cookies = login_response.cookies

        response = client.post(
            "/users/user_001/favorites/movie_999",
            cookies=cookies
        )

        assert response.status_code == 404
        assert "Movie with ID 'movie_999' not found" in (
            response.json()['detail']
        )

    def test_get_user_includes_favorites(self):
        """Test that user endpoint returns favorites list"""
        login_response = client.post(
            "/users/login",
            json={"email": "test@example.com", "password": "Test123!@#"}
        )
        cookies = login_response.cookies

        client.post(
            "/users/user_001/favorites/movie_001",
            cookies=cookies
        )

        response = client.get("/users/user_001")
        assert response.status_code == 200
        data = response.json()

        assert 'favorites' in data
        assert 'movie_001' in data['favorites']

    def test_multiple_movies_in_favorites(self):
        """Test adding multiple movies to favorites"""
        movie_dao = movie_controller_instance.movie_dao
        movie_dao.movies['movie_002'] = {
            'movie_id': 'movie_002',
            'title': 'Another Movie',
            'genre': 'Drama',
            'year': 2021,
            'director': 'Director 2',
            'description': 'Another test movie'
        }

        login_response = client.post(
            "/users/login",
            json={"email": "test@example.com", "password": "Test123!@#"}
        )
        cookies = login_response.cookies

        response1 = client.post(
            "/users/user_001/favorites/movie_001",
            cookies=cookies
        )
        response2 = client.post(
            "/users/user_001/favorites/movie_002",
            cookies=cookies
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()['added'] is True
        assert response2.json()['added'] is True

        data = response2.json()
        assert len(data['favorites']) == 2
        assert 'movie_001' in data['favorites']
        assert 'movie_002' in data['favorites']

    def test_deleted_movie_removed_from_favorites(self):
        """Test that deleted movies are filtered from favorites"""
        movie_dao = movie_controller_instance.movie_dao

        # Add second movie
        movie_dao.movies['movie_002'] = {
            'movie_id': 'movie_002',
            'title': 'Another Movie',
            'genre': 'Drama',
            'year': 2021,
            'director': 'Director 2',
            'description': 'Another test movie'
        }

        login_response = client.post(
            "/users/login",
            json={"email": "test@example.com", "password": "Test123!@#"}
        )
        cookies = login_response.cookies

        # Add both movies to favorites
        client.post(
            "/users/user_001/favorites/movie_001",
            cookies=cookies
        )
        client.post(
            "/users/user_001/favorites/movie_002",
            cookies=cookies
        )

        # Delete movie_001
        del movie_dao.movies['movie_001']

        # Get user - should only show movie_002
        response = client.get("/users/user_001")
        assert response.status_code == 200
        data = response.json()

        assert 'favorites' in data
        assert len(data['favorites']) == 1
        assert 'movie_002' in data['favorites']
        assert 'movie_001' not in data['favorites']
