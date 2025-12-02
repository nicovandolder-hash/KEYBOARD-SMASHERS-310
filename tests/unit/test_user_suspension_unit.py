import pytest
from keyboard_smashers.dao.user_dao import UserDAO
from keyboard_smashers.models.user_model import User
import tempfile
import os


@pytest.fixture
def temp_user_csv():
    """Create a temporary CSV file for testing"""
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "test_users.csv")
    yield csv_path
    # Cleanup
    if os.path.exists(csv_path):
        os.remove(csv_path)
    os.rmdir(temp_dir)


@pytest.fixture
def user_dao(temp_user_csv):
    """Create a UserDAO instance with temporary CSV"""
    return UserDAO(csv_path=temp_user_csv)


class TestUserSuspension:
    """Test user suspension functionality"""

    def test_user_created_not_suspended_by_default(self, user_dao):
        """New users should not be suspended by default"""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        created_user = user_dao.create_user(user_data)

        assert created_user['is_suspended'] is False

    def test_suspend_user_success(self, user_dao):
        """Admin should be able to suspend a user"""
        # Create user
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        created_user = user_dao.create_user(user_data)
        user_id = created_user['userid']

        # Suspend user
        user_dao.suspend_user(user_id)

        # Verify suspension
        suspended_user = user_dao.get_user(user_id)
        assert suspended_user['is_suspended'] is True

    def test_reactivate_user_success(self, user_dao):
        """Admin should be able to reactivate a suspended user"""
        # Create and suspend user
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        created_user = user_dao.create_user(user_data)
        user_id = created_user['userid']
        user_dao.suspend_user(user_id)

        # Reactivate user
        user_dao.reactivate_user(user_id)

        # Verify reactivation
        reactivated_user = user_dao.get_user(user_id)
        assert reactivated_user['is_suspended'] is False

    def test_suspend_nonexistent_user(self, user_dao):
        """Suspending non-existent user should raise error"""
        with pytest.raises(KeyError):
            user_dao.suspend_user('nonexistent_user')

    def test_reactivate_nonexistent_user(self, user_dao):
        """Reactivating non-existent user should raise error"""
        with pytest.raises(KeyError):
            user_dao.reactivate_user('nonexistent_user')

    def test_suspension_persists_after_save(self, user_dao):
        """Suspension status should persist to CSV"""
        # Create and suspend user
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        created_user = user_dao.create_user(user_data)
        user_id = created_user['userid']
        user_dao.suspend_user(user_id)

        # Create new DAO instance (reloads from CSV)
        new_dao = UserDAO(csv_path=user_dao.csv_path)

        # Verify suspension persisted
        user = new_dao.get_user(user_id)
        assert user['is_suspended'] is True

    def test_user_model_has_is_suspended_field(self):
        """User model should have is_suspended field"""
        user = User(
            username='testuser',
            email='test@example.com',
            userid='user_001'
        )
        assert hasattr(user, 'is_suspended')
        assert user.is_suspended is False

    def test_user_model_accepts_is_suspended_parameter(self):
        """User model should accept is_suspended in constructor"""
        user = User(
            username='testuser',
            email='test@example.com',
            userid='user_001',
            is_suspended=True
        )
        assert user.is_suspended is True
