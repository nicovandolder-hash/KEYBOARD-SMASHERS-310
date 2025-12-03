import pytest
from keyboard_smashers.dao.user_dao import UserDAO
from keyboard_smashers.dao.movie_dao import MovieDAO


@pytest.fixture
def temp_users_csv(tmp_path):
    """Create a temporary users CSV for testing"""
    csv_path = tmp_path / "users.csv"
    csv_path.write_text(
        "userid,username,email,password,reputation,creation_date,"
        "is_admin,is_suspended,total_reviews,total_penalty_count,"
        "favorites\n"
        "user_001,testuser,test@example.com,hashedpass,3,"
        "2025-01-01T00:00:00,false,false,0,0,\n"
    )
    return str(csv_path)


@pytest.fixture
def temp_movies_csv(tmp_path):
    """Create a temporary movies CSV for testing"""
    csv_path = tmp_path / "movies.csv"
    csv_path.write_text(
        "movie_id,title,genre,year,director,description\n"
        "movie_001,Test Movie,Action,2020,Director,Description\n"
        "movie_002,Another Movie,Drama,2021,Director2,Desc2\n"
    )
    return str(csv_path)


@pytest.fixture
def user_dao(temp_users_csv):
    """Create a UserDAO instance with temp CSV"""
    return UserDAO(csv_path=temp_users_csv)


@pytest.fixture
def movie_dao(temp_movies_csv):
    """Create a MovieDAO instance with temp CSV"""
    return MovieDAO(csv_path=temp_movies_csv)


class TestFavoritesToggle:
    """Unit tests for toggle_favorite functionality"""

    def test_add_movie_to_favorites(self, user_dao):
        """Test adding a movie to empty favorites list"""
        added = user_dao.toggle_favorite("user_001", "movie_001")

        assert added is True
        user = user_dao.get_user("user_001")
        assert "movie_001" in user['favorites']
        assert len(user['favorites']) == 1

    def test_remove_movie_from_favorites(self, user_dao):
        """Test removing a movie from favorites list"""
        user_dao.toggle_favorite("user_001", "movie_001")
        removed = user_dao.toggle_favorite("user_001", "movie_001")

        assert removed is False
        user = user_dao.get_user("user_001")
        assert "movie_001" not in user['favorites']
        assert len(user['favorites']) == 0

    def test_add_multiple_movies(self, user_dao):
        """Test adding multiple movies to favorites"""
        user_dao.toggle_favorite("user_001", "movie_001")
        user_dao.toggle_favorite("user_001", "movie_002")
        user_dao.toggle_favorite("user_001", "movie_003")

        user = user_dao.get_user("user_001")
        assert len(user['favorites']) == 3
        assert "movie_001" in user['favorites']
        assert "movie_002" in user['favorites']
        assert "movie_003" in user['favorites']

    def test_toggle_nonexistent_user(self, user_dao):
        """Test toggling favorite for non-existent user"""
        with pytest.raises(KeyError) as exc_info:
            user_dao.toggle_favorite("user_999", "movie_001")

        assert "User with ID 'user_999' not found" in str(exc_info.value)

    def test_favorites_persistence(self, user_dao, tmp_path):
        """Test that favorites persist after save/reload"""
        user_dao.toggle_favorite("user_001", "movie_001")
        user_dao.toggle_favorite("user_001", "movie_002")

        csv_path = user_dao.csv_path
        new_dao = UserDAO(csv_path=csv_path)

        user = new_dao.get_user("user_001")
        assert len(user['favorites']) == 2
        assert "movie_001" in user['favorites']
        assert "movie_002" in user['favorites']

    def test_new_user_has_empty_favorites(self, user_dao):
        """Test that newly created users have empty favorites list"""
        new_user_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'hashedpass'
        }
        user = user_dao.create_user(new_user_data)

        assert 'favorites' in user
        assert user['favorites'] == []

    def test_favorites_loaded_from_csv(self, tmp_path):
        """Test loading favorites from CSV with existing data"""
        csv_path = tmp_path / "users_with_favs.csv"
        csv_path.write_text(
            "userid,username,email,password,reputation,creation_date,"
            "is_admin,is_suspended,total_reviews,total_penalty_count,"
            "favorites\n"
            "user_001,testuser,test@example.com,hashedpass,3,"
            "2025-01-01T00:00:00,false,false,0,0,"
            "\"movie_001,movie_002,movie_003\"\n"
        )

        dao = UserDAO(csv_path=str(csv_path))
        user = dao.get_user("user_001")

        assert len(user['favorites']) == 3
        assert "movie_001" in user['favorites']
        assert "movie_002" in user['favorites']
        assert "movie_003" in user['favorites']
