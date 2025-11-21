import pytest
import tempfile
import os
from datetime import datetime
from keyboard_smashers.dao.user_dao import UserDAO


@pytest.fixture
def temp_csv():
    """Create a temporary CSV file for testing"""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.csv',
        delete=False
    )
    temp_file.write(
        'userid,username,email,password,reputation,'
        'creation_date,is_admin,total_reviews\n'
    )
    temp_file.write(
        'user_001,john_doe,john@example.com,hashed_pass123,5,'
        '2025-01-15T10:30:00,false,3\n'
    )
    temp_file.write(
        'user_002,jane_smith,jane@example.com,hashed_pass456,4,'
        '2025-02-20T14:45:00,true,5\n'
    )
    temp_file.close()
    yield temp_file.name
    os.unlink(temp_file.name)


@pytest.fixture
def user_dao(temp_csv):
    """Create a UserDAO instance with test data"""
    return UserDAO(csv_path=temp_csv)


class TestUserDAOInitialization:
    """Test UserDAO initialization and data loading"""

    def test_load_users_from_csv(self, user_dao):
        """Test that users are loaded correctly from CSV"""
        assert len(user_dao.users) == 2
        assert 'user_001' in user_dao.users
        assert 'user_002' in user_dao.users

    def test_email_index_created(self, user_dao):
        """Test that email index is populated"""
        assert 'john@example.com' in user_dao.email_index
        assert 'jane@example.com' in user_dao.email_index
        assert user_dao.email_index['john@example.com'] == 'user_001'

    def test_username_index_created(self, user_dao):
        """Test that username index is populated"""
        assert 'john_doe' in user_dao.username_index
        assert 'jane_smith' in user_dao.username_index
        assert user_dao.username_index['john_doe'] == 'user_001'

    def test_user_counter_initialized(self, user_dao):
        """Test that user counter is set correctly"""
        assert user_dao.user_counter == 3  # Should be max + 1


class TestUserDAOCreate:
    """Test user creation functionality"""

    def test_create_user_success(self, user_dao):
        """Test creating a new user successfully"""
        user_data = {
            'username': 'new_user',
            'email': 'new@example.com',
            'password': 'hashed_new_pass',
            'reputation': 3
        }
        created_user = user_dao.create_user(user_data)

        assert created_user['userid'] == 'user_003'
        assert created_user['username'] == 'new_user'
        assert created_user['email'] == 'new@example.com'
        assert 'user_003' in user_dao.users

    def test_create_user_duplicate_email(self, user_dao):
        """Test that duplicate email raises ValueError"""
        user_data = {
            'username': 'another_user',
            'email': 'john@example.com',  # Duplicate email
            'password': 'pass123'
        }
        with pytest.raises(ValueError, match="already registered"):
            user_dao.create_user(user_data)

    def test_create_user_duplicate_email_case_insensitive(self, user_dao):
        """Test that duplicate email detection is case-insensitive"""
        user_data = {
            'username': 'another_user',
            'email': 'JOHN@EXAMPLE.COM',  # Different case
            'password': 'pass123'
        }
        with pytest.raises(ValueError, match="already registered"):
            user_dao.create_user(user_data)

    def test_create_user_duplicate_username(self, user_dao):
        """Test that duplicate username raises ValueError"""
        user_data = {
            'username': 'john_doe',  # Duplicate username
            'email': 'different@example.com',
            'password': 'pass123'
        }
        with pytest.raises(ValueError, match="already taken"):
            user_dao.create_user(user_data)

    def test_create_user_duplicate_username_case_insensitive(self, user_dao):
        """Test that duplicate username detection is case-insensitive"""
        user_data = {
            'username': 'JOHN_DOE',  # Different case
            'email': 'different@example.com',
            'password': 'pass123'
        }
        with pytest.raises(ValueError, match="already taken"):
            user_dao.create_user(user_data)

    def test_create_user_updates_indexes(self, user_dao):
        """Test that creating a user updates both indexes"""
        user_data = {
            'username': 'index_test',
            'email': 'index@test.com',
            'password': 'pass123'
        }
        created_user = user_dao.create_user(user_data)

        assert 'index@test.com' in user_dao.email_index
        assert 'index_test' in user_dao.username_index
        assert user_dao.email_index['index@test.com'] == created_user['userid']
        assert (user_dao.username_index['index_test'] ==
                created_user['userid'])


class TestUserDAORead:
    """Test user retrieval functionality"""

    def test_get_user_by_id(self, user_dao):
        """Test retrieving user by ID"""
        user = user_dao.get_user('user_001')
        assert user['username'] == 'john_doe'
        assert user['email'] == 'john@example.com'

    def test_get_user_not_found(self, user_dao):
        """Test that getting non-existent user raises KeyError"""
        with pytest.raises(KeyError, match="not found"):
            user_dao.get_user('user_999')

    def test_get_user_by_email(self, user_dao):
        """Test retrieving user by email"""
        user = user_dao.get_user_by_email('jane@example.com')
        assert user is not None
        assert user['username'] == 'jane_smith'
        assert user['userid'] == 'user_002'

    def test_get_user_by_email_not_found(self, user_dao):
        """Test that getting user by non-existent email returns None"""
        user = user_dao.get_user_by_email('nonexistent@example.com')
        assert user is None


class TestUserDAOUpdate:
    """Test user update functionality"""

    def test_update_user_username(self, user_dao):
        """Test updating username"""
        updated_user = user_dao.update_user(
            'user_001',
            {'username': 'updated_john'}
        )
        assert updated_user['username'] == 'updated_john'
        assert user_dao.users['user_001']['username'] == 'updated_john'

    def test_update_user_email(self, user_dao):
        """Test updating email"""
        updated_user = user_dao.update_user(
            'user_001',
            {'email': 'newemail@example.com'}
        )
        assert updated_user['email'] == 'newemail@example.com'
        assert 'newemail@example.com' in user_dao.email_index
        assert 'john@example.com' not in user_dao.email_index

    def test_update_username_to_duplicate(self, user_dao):
        """Test that updating to duplicate username raises ValueError"""
        with pytest.raises(ValueError, match="already taken"):
            user_dao.update_user(
                'user_001',
                {'username': 'jane_smith'}  # Already exists
            )

    def test_update_username_case_insensitive_duplicate(self, user_dao):
        """Test that username update checks are case-insensitive"""
        with pytest.raises(ValueError, match="already taken"):
            user_dao.update_user(
                'user_001',
                {'username': 'JANE_SMITH'}  # Different case
            )

    def test_update_email_to_duplicate(self, user_dao):
        """Test that updating to duplicate email raises ValueError"""
        with pytest.raises(ValueError, match="already registered"):
            user_dao.update_user(
                'user_001',
                {'email': 'jane@example.com'}  # Already exists
            )

    def test_update_user_not_found(self, user_dao):
        """Test that updating non-existent user raises KeyError"""
        with pytest.raises(KeyError, match="not found"):
            user_dao.update_user('user_999', {'username': 'new_name'})

    def test_update_username_updates_index(self, user_dao):
        """Test that updating username updates the username index"""
        user_dao.update_user('user_001', {'username': 'brand_new_name'})

        assert 'brand_new_name' in user_dao.username_index
        assert 'john_doe' not in user_dao.username_index
        assert user_dao.username_index['brand_new_name'] == 'user_001'
