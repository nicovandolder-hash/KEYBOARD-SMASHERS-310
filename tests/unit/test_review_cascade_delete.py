import pytest
import tempfile
from pathlib import Path
from keyboard_smashers.dao.review_dao import ReviewDAO


@pytest.fixture
def temp_imdb_csv():
    """Create a temporary IMDB reviews CSV file for testing."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_path = temp_file.name
    temp_file.write(
        "movie,User,User's Rating out of 10,Review,Date of Review\n"
    )
    temp_file.close()
    yield temp_path
    try:
        Path(temp_path).unlink()
    except Exception:
        pass


@pytest.fixture
def temp_new_reviews_csv():
    """Create a temporary new reviews CSV file for testing."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_path = temp_file.name
    temp_file.write(
        "operation,review_id,movie_id,user_id,imdb_username,"
        "rating,review_text,review_date\n"
    )
    temp_file.close()
    yield temp_path
    try:
        Path(temp_path).unlink()
    except Exception:
        pass


@pytest.fixture
def review_dao(temp_imdb_csv, temp_new_reviews_csv):
    """Create a ReviewDAO instance with temp files."""
    return ReviewDAO(
        imdb_csv_path=temp_imdb_csv,
        new_reviews_csv_path=temp_new_reviews_csv
    )


class TestDeleteReviewsByMovie:
    """Tests for delete_reviews_by_movie functionality"""

    def test_delete_reviews_for_movie_with_no_reviews(self, review_dao):
        """Test deleting reviews for a movie that has no reviews"""
        deleted_count = review_dao.delete_reviews_by_movie('nonexistent')
        assert deleted_count == 0

    def test_delete_user_reviews_for_movie(self, review_dao):
        """Test that user-created reviews are deleted"""
        # Create some reviews for movie 100
        review_dao.create_review({
            'movie_id': '100',
            'user_id': 'user_001',
            'rating': 4,
            'review_text': 'Great movie!'
        })
        review_dao.create_review({
            'movie_id': '100',
            'user_id': 'user_002',
            'rating': 5,
            'review_text': 'Amazing!'
        })

        # Delete reviews for movie 100
        deleted_count = review_dao.delete_reviews_by_movie('100')

        assert deleted_count == 2
        # Verify reviews are gone
        reviews = review_dao.get_reviews_for_movie('100')
        assert len(reviews) == 0

    def test_delete_only_target_movie_reviews(self, review_dao):
        """Test that only reviews for target movie are deleted"""
        # Create reviews for different movies
        review_dao.create_review({
            'movie_id': '100',
            'user_id': 'user_001',
            'rating': 4,
            'review_text': 'Movie 100 review'
        })
        review_dao.create_review({
            'movie_id': '200',
            'user_id': 'user_001',
            'rating': 5,
            'review_text': 'Movie 200 review'
        })

        # Delete reviews for movie 100 only
        deleted_count = review_dao.delete_reviews_by_movie('100')

        assert deleted_count == 1
        # Movie 200 review should still exist
        reviews_200 = review_dao.get_reviews_for_movie('200')
        assert len(reviews_200) == 1

    def test_does_not_delete_imdb_reviews(self, review_dao):
        """Test that IMDB legacy reviews (no user_id) are not deleted"""
        # Manually add an IMDB-style review (no user_id)
        imdb_review = {
            'review_id': 'imdb_001',
            'movie_id': '100',
            'user_id': None,
            'imdb_username': 'imdb_user',
            'rating': 4,
            'review_text': 'IMDB review',
            'review_date': '2023-01-01'
        }
        review_dao.reviews['imdb_001'] = imdb_review
        review_dao.reviews_by_movie.setdefault('100', []).append('imdb_001')

        # Also add a user review
        review_dao.create_review({
            'movie_id': '100',
            'user_id': 'user_001',
            'rating': 5,
            'review_text': 'User review'
        })

        # Delete reviews for movie 100
        deleted_count = review_dao.delete_reviews_by_movie('100')

        # Only the user review should be deleted
        assert deleted_count == 1
        # IMDB review should still be in memory
        assert 'imdb_001' in review_dao.reviews

    def test_returns_correct_count(self, review_dao):
        """Test that correct count of deleted reviews is returned"""
        # Create 3 reviews
        for i in range(3):
            review_dao.create_review({
                'movie_id': '100',
                'user_id': f'user_{i}',
                'rating': 4,
                'review_text': f'Review {i}'
            })

        deleted_count = review_dao.delete_reviews_by_movie('100')
        assert deleted_count == 3

    def test_movie_id_string_conversion(self, review_dao):
        """Test that movie_id is properly converted to string"""
        review_dao.create_review({
            'movie_id': '100',
            'user_id': 'user_001',
            'rating': 4,
            'review_text': 'Test review'
        })

        # Pass integer-like movie_id
        deleted_count = review_dao.delete_reviews_by_movie(100)
        assert deleted_count == 1
