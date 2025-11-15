from .models.user_model import User
import logging
from .logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def main():
    user = User(
        username="test_user",
        email="test@example.com",
        userid="12345",
        password="securePass123@"
    )

    print(f"Created user: {user.username}")
    print(f"Email: {user.email}")


if __name__ == '__main__':
    main()
