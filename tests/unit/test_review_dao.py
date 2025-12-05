import pytest
import tempfile
import pandas as pd
from pathlib import Path
from keyboard_smashers.dao.review_dao import ReviewDAO
from datetime import datetime


@pytest.fixture
def temp_imdb_csv():
    """Create a temporary IMDB reviews CSV file for testing."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_path = temp_file.name

    # Write sample IMDB data
    temp_file.write(
        "movie,User,User's Rating out of 10,Review,Date of Review\n"
    )
    temp_file.write(
        "Test Movie 1,user1,8,Great movie!,2023-01-01\n"
    )
    temp_file.write(
        "Test Movie 1,user2,6,Good but not great,2023-01-02\n"
    )
    temp_file.write(
        "Test Movie 2,user3,10,Masterpiece!,2023-01-03\n"
    )
    temp_file.close()

    yield temp_path

    # Cleanup
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
    # Write CSV header for append-only log (matches ReviewDAO format)
    temp_file.write(
        "operation,review_id,movie_id,user_id,imdb_username,"
        "rating,review_text,review_date\n"
    )
    temp_file.close()

    yield temp_path

    # Cleanup
    try:
        Path(temp_path).unlink()
    except Exception:
        pass


@pytest.fixture
def temp_movies_csv():
    """Create a temporary movies CSV file for testing."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_path = temp_file.name

    # Write sample movies data
    temp_file.write("movie_id,title,genre,year,director,description\n")
    temp_file.write("1,Test Movie 1,Action,2020,Director 1,Desc 1\n")
    temp_file.write("2,Test Movie 2,Drama,2021,Director 2,Desc 2\n")
    temp_file.close()

    # Create data directory temporarily
    data_dir = Path(temp_path).parent / "data"
    data_dir.mkdir(exist_ok=True)
    movies_csv = data_dir / "movies.csv"
    Path(temp_path).rename(movies_csv)

    yield str(movies_csv)

    # Cleanup
    try:
        movies_csv.unlink()
        data_dir.rmdir()
    except Exception:
        pass


class TestReviewDAOInitialization:
    """Test ReviewDAO initialization and loading."""

    def test_load_imdb_reviews(self, temp_imdb_csv, temp_new_reviews_csv):
        """Test loading IMDB reviews from CSV."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        assert len(dao.reviews) == 3
        assert 'review_000000' in dao.reviews
        assert 'review_000001' in dao.reviews
        assert 'review_000002' in dao.reviews

    def test_imdb_reviews_have_no_user_id(
        self, temp_imdb_csv, temp_new_reviews_csv
    ):
        """Test that IMDB reviews have None for user_id."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        for review in dao.reviews.values():
            assert review['user_id'] is None
            assert review['imdb_username'] is not None

    def test_rating_conversion(self, temp_imdb_csv, temp_new_reviews_csv):
        """Test that ratings are converted from 0-10 to 1-5 scale."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        review = dao.reviews['review_000000']
        # Rating 8 out of 10 should convert to 4 out of 5
        assert review['rating'] == 4

    def test_review_text_truncation(self):
        """Test that review text is truncated to 250 characters."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        temp_path = temp_file.name

        long_text = "a" * 300
        temp_file.write(
            "movie,User,User's Rating out of 10,Review,Date of Review\n"
        )
        temp_file.write(f"Test Movie,user1,8,{long_text},2023-01-01\n")
        temp_file.close()

        temp_new = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv', newline=''
        )
        # Write CSV header for append-only log
        temp_new.write(
            "operation,review_id,movie_id,user_id,imdb_username,"
            "rating,review_text,review_date\n"
        )
        temp_new.close()

        dao = ReviewDAO(
            imdb_csv_path=temp_path,
            new_reviews_csv_path=temp_new.name
        )

        review = dao.reviews['review_000000']
        assert len(review['review_text']) == 250

        # Cleanup
        Path(temp_path).unlink()
        Path(temp_new.name).unlink()


class TestReviewDAOIndexes:
    """Test ReviewDAO indexing functionality."""

    def test_reviews_by_movie_index(
        self, temp_imdb_csv, temp_new_reviews_csv
    ):
        """Test that reviews are indexed by movie_id."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        # Should have 2 movies (Test Movie 1 and Test Movie 2)
        assert len(dao.reviews_by_movie) == 2

    def test_get_reviews_for_movie(
        self, temp_imdb_csv, temp_new_reviews_csv
    ):
        """Test getting all reviews for a specific movie."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        # Get reviews for movie (depends on movie title in CSV)
        movie_reviews = dao.get_reviews_for_movie("Test Movie 1")
        assert len(movie_reviews) == 2


class TestReviewDAOCreate:
    """Test ReviewDAO create operations."""

    def test_create_review(self, temp_imdb_csv, temp_new_reviews_csv):
        """Test creating a new review."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        initial_count = len(dao.reviews)

        review_data = {
            'movie_id': '1',
            'user_id': 'user_001',
            'rating': 5,
            'review_text': 'Amazing movie!',
            'review_date': str(datetime.now())
        }

        created_review = dao.create_review(review_data)

        assert len(dao.reviews) == initial_count + 1
        assert created_review['review_id'] == 'review_000003'
        assert created_review['user_id'] == 'user_001'
        assert created_review['rating'] == 5

    def test_create_review_duplicate_prevention(
        self, temp_imdb_csv, temp_new_reviews_csv
    ):
        """Test that duplicate reviews are prevented."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        review_data = {
            'movie_id': '1',
            'user_id': 'user_001',
            'rating': 5,
            'review_text': 'Amazing movie!',
            'review_date': str(datetime.now())
        }

        # First creation should succeed
        dao.create_review(review_data)

        # Second creation should fail
        with pytest.raises(ValueError, match="already reviewed"):
            dao.create_review(review_data)

    def test_create_review_persists_to_csv(
        self, temp_imdb_csv, temp_new_reviews_csv
    ):
        """Test that created reviews are written to CSV."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        review_data = {
            'movie_id': '1',
            'user_id': 'user_001',
            'rating': 5,
            'review_text': 'Amazing movie!',
            'review_date': str(datetime.now())
        }

        dao.create_review(review_data)

        # Verify CSV file was written
        df = pd.read_csv(temp_new_reviews_csv)
        assert len(df) == 1
        # Column order: operation,review_id,movie_id,user_id,...
        assert df.iloc[0]['review_id'] is not None
        assert str(df.iloc[0]['movie_id']) == '1'
        assert df.iloc[0]['user_id'] == 'user_001'


class TestReviewDAORead:
    """Test ReviewDAO read operations."""

    def test_get_review_by_id(self, temp_imdb_csv, temp_new_reviews_csv):
        """Test getting a review by ID."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        review = dao.get_review('review_000000')
        assert review is not None
        assert review['review_id'] == 'review_000000'

    def test_get_nonexistent_review(
        self, temp_imdb_csv, temp_new_reviews_csv
    ):
        """Test getting a review that doesn't exist."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        with pytest.raises(KeyError):
            dao.get_review('nonexistent_id')

    def test_get_reviews_by_user(self, temp_imdb_csv, temp_new_reviews_csv):
        """Test getting reviews by user."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        # Create reviews with user_id
        dao.create_review({
            'movie_id': '1',
            'user_id': 'user_001',
            'rating': 5,
            'review_text': 'Great!',
            'review_date': str(datetime.now())
        })

        dao.create_review({
            'movie_id': '2',
            'user_id': 'user_001',
            'rating': 4,
            'review_text': 'Good!',
            'review_date': str(datetime.now())
        })

        user_reviews = dao.get_reviews_by_user('user_001')
        assert len(user_reviews) == 2


class TestReviewDAOUpdate:
    """Test ReviewDAO update operations."""

    def test_update_review(self, temp_imdb_csv, temp_new_reviews_csv):
        """Test updating an existing review."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        # Create a review first
        review_data = {
            'movie_id': '1',
            'user_id': 'user_001',
            'rating': 3,
            'review_text': 'Okay movie',
            'review_date': str(datetime.now())
        }
        created = dao.create_review(review_data)
        review_id = created['review_id']

        # Update it
        update_data = {
            'rating': 5,
            'review_text': 'Actually amazing!'
        }
        updated = dao.update_review(review_id, update_data)

        assert updated['rating'] == 5
        assert updated['review_text'] == 'Actually amazing!'

    def test_update_nonexistent_review(
        self, temp_imdb_csv, temp_new_reviews_csv
    ):
        """Test updating a review that doesn't exist."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        with pytest.raises(KeyError):
            dao.update_review('nonexistent_id', {'rating': 5})


class TestReviewDAODelete:
    """Test ReviewDAO delete operations."""

    def test_delete_review(self, temp_imdb_csv, temp_new_reviews_csv):
        """Test deleting a review."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        # Create a review first
        review_data = {
            'movie_id': '1',
            'user_id': 'user_001',
            'rating': 5,
            'review_text': 'Great!',
            'review_date': str(datetime.now())
        }
        created = dao.create_review(review_data)
        review_id = created['review_id']

        initial_count = len(dao.reviews)

        # Delete it
        dao.delete_review(review_id)

        assert len(dao.reviews) == initial_count - 1
        assert review_id not in dao.reviews

    def test_delete_removes_from_indexes(
        self, temp_imdb_csv, temp_new_reviews_csv
    ):
        """Test that deletion removes review from all indexes."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        # Create a review
        review_data = {
            'movie_id': '1',
            'user_id': 'user_001',
            'rating': 5,
            'review_text': 'Great!',
            'review_date': str(datetime.now())
        }
        created = dao.create_review(review_data)
        review_id = created['review_id']

        # Verify it's in indexes
        assert review_id in dao.reviews_by_movie['1']
        assert review_id in dao.reviews_by_user['user_001']

        # Delete it
        dao.delete_review(review_id)

        # Verify it's removed from indexes
        assert review_id not in dao.reviews_by_movie.get('1', [])
        assert review_id not in dao.reviews_by_user.get('user_001', [])

    def test_delete_and_recreate_same_user_movie(
        self, temp_imdb_csv, temp_new_reviews_csv
    ):
        """Test that user can create review after deleting previous one."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        # Create a review
        review_data = {
            'movie_id': '1',
            'user_id': 'user_001',
            'rating': 3,
            'review_text': 'Meh',
            'review_date': str(datetime.now())
        }
        created = dao.create_review(review_data)

        # Delete it
        dao.delete_review(created['review_id'])

        # Create another review for same movie by same user - should work
        review_data2 = {
            'movie_id': '1',
            'user_id': 'user_001',
            'rating': 5,
            'review_text': 'Actually great!',
            'review_date': str(datetime.now())
        }
        created2 = dao.create_review(review_data2)
        assert created2 is not None
        assert created2['rating'] == 5


class TestReviewDAOCompact:
    """Test ReviewDAO compact operation."""

    def test_compact_removes_deleted_reviews(
        self, temp_imdb_csv, temp_new_reviews_csv
    ):
        """Test that compact operation consolidates the CSV."""
        dao = ReviewDAO(
            imdb_csv_path=temp_imdb_csv,
            new_reviews_csv_path=temp_new_reviews_csv
        )

        # Create and delete some reviews
        review1 = dao.create_review({
            'movie_id': '1',
            'user_id': 'user_001',
            'rating': 5,
            'review_text': 'Great!',
            'review_date': str(datetime.now())
        })

        dao.create_review({
            'movie_id': '1',
            'user_id': 'user_002',
            'rating': 4,
            'review_text': 'Good!',
            'review_date': str(datetime.now())
        })

        dao.delete_review(review1['review_id'])

        # Before compact - should have operations
        df_before = pd.read_csv(temp_new_reviews_csv)
        assert len(df_before) > 0

        # Compact
        dao.compact_reviews()

        # After compact - only active review remains
        df_after = pd.read_csv(temp_new_reviews_csv)
        assert len(df_after) == 1
        assert df_after.iloc[0]['operation'] == 'create'
