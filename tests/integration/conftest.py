"""
Shared pytest fixtures for integration tests.
Prevents tests from writing to production data files.
"""
from keyboard_smashers.controllers.user_controller import (
    user_controller_instance
)
from unittest.mock import patch, MagicMock
import pytest
import sys
import os
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '../..')))


@pytest.fixture(autouse=True)
def mock_file_writes():
    """
    Mock all file write operations to prevent tests from
    touching production CSV files.
    """
    user_dao = user_controller_instance.user_dao

    with patch.object(user_dao, 'save_users', MagicMock()), \
            patch('pandas.DataFrame.to_csv', MagicMock()):
        yield
