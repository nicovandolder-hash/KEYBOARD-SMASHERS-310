from keyboard_smashers.models.user_model import User


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
