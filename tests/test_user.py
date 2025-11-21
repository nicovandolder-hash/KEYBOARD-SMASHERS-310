from keyboard_smashers.models.review_model import Review
from keyboard_smashers.models.user_model import User
from datetime import datetime
import pytest
import sys
import os
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..')))


@pytest.fixture
def standard_user():
    return User(
        username="test_user",
        email="test_user@gmail.com",
        userid="u12345",
        reputation=3,
        creation_date=datetime(2025, 1, 1, 12, 0, 0),
        is_admin=False
    )


def standard_review():
    return Review(
        review_id="r1",
        user_id="u1",
        movie_id="m1",
        movie_title="Test Movie",
        rating=8,
        comment="Great movie!",
        review_date="2025-05-15",
        helpful_votes=5
    )


def test_create_user(standard_user):
    assert standard_user.username == "test_user"
    assert standard_user.email == "test_user@gmail.com"
    assert standard_user.userid == "u12345"
    assert standard_user.reputation == 3
    assert standard_user.creation_date == datetime(2025, 1, 1, 12, 0, 0)
    assert standard_user.reviews == []
    assert standard_user.total_reviews == 0
    assert standard_user.is_admin is False
    assert standard_user.notifications == []


def test_set_password_length_short(standard_user):
    with pytest.raises(ValueError, match=(
            "Password must be at least 8 characters long")):
        standard_user.set_password("Short1!")


def test_set_password_length_long(standard_user):
    standard_user.set_password("VeryLongPassword123!")
    assert standard_user.password == "VeryLongPassword123!"


def test_set_password_length_exact(standard_user):
    standard_user.set_password("Exact8.!")
    assert standard_user.password == "Exact8.!"


def test_set_password_no_digit(standard_user):
    with pytest.raises(ValueError, match=(
            "Password must contain at least one digit.")):
        standard_user.set_password("NoDigitPass!")


def test_set_password_with_digit(standard_user):
    standard_user.set_password("Passw0rd!")
    assert standard_user.password == "Passw0rd!"


def test_set_password_no_special_char(standard_user):
    with pytest.raises(ValueError, match=(
            "Password must contain at least one special character.")):
        standard_user.set_password("NoSpecialChar1")


def test_set_password_with_special_char(standard_user):
    standard_user.set_password("Special@123")
    assert standard_user.password == "Special@123"


def test_set_password_no_uppercase(standard_user):
    with pytest.raises(ValueError, match=(
            "Password must contain at least one uppercase letter.")):
        standard_user.set_password("nouppercase1!")


def test_set_password_with_uppercase(standard_user):
    standard_user.set_password("WithUppercase1!")
    assert standard_user.password == "WithUppercase1!"


def test_set_password_no_lowercase(standard_user):
    with pytest.raises(ValueError, match=(
            "Password must contain at least one lowercase letter.")):
        standard_user.set_password("NOLOWERCASE1!")


def test_set_password_with_lowercase(standard_user):
    standard_user.set_password("WithLowercase1!")
    assert standard_user.password == "WithLowercase1!"


def test_set_and_check_password(standard_user):
    standard_user.set_password("ValidPass1!")
    assert standard_user.check_password("ValidPass1!") is True
    assert standard_user.check_password("InvalidPass1!") is False


def test_add_review(standard_user):
    review = standard_review()
    standard_user.add_review(review)
    assert len(standard_user.reviews) == 1
    assert standard_user.total_reviews == 1
    assert standard_user.reviews[0] == review


def test_add_multiple_review(standard_user):

    review1 = standard_review()
    standard_user.add_review(review1)

    review2 = Review(
        review_id="r2",
        user_id="u1",
        movie_id="m2",
        movie_title="Another Test Movie",
        rating=7,
        comment="Good movie!",
        review_date="2025-06-20",
        helpful_votes=3
    )

    standard_user.add_review(review2)

    assert len(standard_user.reviews) == 2
    assert standard_user.total_reviews == 2
    assert standard_user.reviews[0] == review1
    assert standard_user.reviews[1] == review2
