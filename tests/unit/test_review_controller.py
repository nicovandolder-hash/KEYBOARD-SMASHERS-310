"""
Unit tests for ReviewController with mocked ReviewDAO.
"""
import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from datetime import datetime
from keyboard_smashers.controllers.review_controller import (
    ReviewController,
    ReviewCreateSchema,
    ReviewUpdateSchema,
    ReviewSchema,
    PaginatedReviewResponse
)


@pytest.fixture
def mock_review_dao():
    """Mock ReviewDAO for testing controller logic."""
    dao = Mock()
    dao.reviews = {}
    dao.reviews_by_movie = {}
    dao.reviews_by_user = {}
    return dao


@pytest.fixture
def controller(mock_review_dao):
    """Create ReviewController with mocked DAO."""
    with patch(
        'keyboard_smashers.controllers.review_controller.ReviewDAO'
    ) as mock_dao_class:
        mock_dao_class.return_value = mock_review_dao
        controller = ReviewController(
            imdb_csv_path="test.csv",
            new_reviews_csv_path="test_new.csv"
        )
        controller.review_dao = mock_review_dao
        return controller


@pytest.fixture
def sample_review():
    """Sample review dict for testing."""
    return {
        'review_id': 'rev_001',
        'movie_id': '1',
        'user_id': 'user_001',
        'imdb_username': None,
        'rating': 4.5,
        'review_text': 'Great movie!',
        'review_date': str(datetime.now())
    }


@pytest.fixture
def sample_imdb_review():
    """Sample IMDB review (no user_id) for testing."""
    return {
        'review_id': 'imdb_001',
        'movie_id': '1',
        'user_id': None,
        'imdb_username': 'imdb_user',
        'rating': 5.0,
        'review_text': 'Classic film!',
        'review_date': '2020-01-01'
    }


class TestReviewControllerGetOperations:
    """Test GET operations (public endpoints)."""

    def test_get_review_by_id_success(
        self, controller, mock_review_dao, sample_review
    ):
        """Test getting a review by ID."""
        mock_review_dao.get_review.return_value = sample_review

        result = controller.get_review_by_id('rev_001')

        mock_review_dao.get_review.assert_called_once_with('rev_001')
        assert isinstance(result, ReviewSchema)
        assert result.review_id == 'rev_001'
        assert result.rating == 4.5

    def test_get_review_by_id_not_found(
        self, controller, mock_review_dao
    ):
        """Test getting non-existent review."""
        mock_review_dao.get_review.side_effect = KeyError('Not found')

        with pytest.raises(HTTPException) as exc_info:
            controller.get_review_by_id('nonexistent')

        assert exc_info.value.status_code == 404
        assert 'not found' in str(exc_info.value.detail).lower()

    def test_get_reviews_for_movie_with_pagination(
        self, controller, mock_review_dao, sample_review
    ):
        """Test getting reviews for a movie with pagination."""
        reviews = [
            {**sample_review, 'review_id': f'rev_{i:03d}'}
            for i in range(15)
        ]
        mock_review_dao.get_reviews_for_movie.return_value = reviews

        result = controller.get_reviews_for_movie('1', skip=0, limit=10)

        mock_review_dao.get_reviews_for_movie.assert_called_once_with('1')
        assert isinstance(result, PaginatedReviewResponse)
        assert len(result.reviews) == 10
        assert result.total == 15
        assert result.skip == 0
        assert result.limit == 10
        assert result.has_more is True

    def test_get_reviews_for_movie_last_page(
        self, controller, mock_review_dao, sample_review
    ):
        """Test last page of reviews has_more=False."""
        reviews = [
            {**sample_review, 'review_id': f'rev_{i:03d}'}
            for i in range(15)
        ]
        mock_review_dao.get_reviews_for_movie.return_value = reviews

        result = controller.get_reviews_for_movie('1', skip=10, limit=10)

        assert len(result.reviews) == 5
        assert result.has_more is False

    def test_get_reviews_for_movie_empty(
        self, controller, mock_review_dao
    ):
        """Test getting reviews for movie with no reviews."""
        mock_review_dao.get_reviews_for_movie.return_value = []

        result = controller.get_reviews_for_movie('999')

        assert len(result.reviews) == 0
        assert result.total == 0
        assert result.has_more is False

    def test_get_reviews_by_user_with_pagination(
        self, controller, mock_review_dao, sample_review
    ):
        """Test getting reviews by user with pagination."""
        reviews = [
            {**sample_review, 'review_id': f'rev_{i:03d}'}
            for i in range(8)
        ]
        mock_review_dao.get_reviews_by_user.return_value = reviews

        result = controller.get_reviews_by_user(
            'user_001', skip=0, limit=5
        )

        mock_review_dao.get_reviews_by_user.assert_called_once_with(
            'user_001'
        )
        assert len(result.reviews) == 5
        assert result.total == 8
        assert result.has_more is True


class TestReviewControllerCreateOperations:
    """Test CREATE operations (authenticated endpoints)."""

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance'
    )
    def test_create_review_success(
        self, mock_movie_ctrl, controller, mock_review_dao, sample_review
    ):
        """Test creating a review successfully."""
        mock_movie_ctrl.get_movie_by_id.return_value = {
            'id': '1', 'title': 'Test Movie'
        }
        mock_review_dao.create_review.return_value = sample_review

        review_data = ReviewCreateSchema(
            movie_id='1',
            rating=4.5,
            review_text='Great movie!'
        )

        result = controller.create_review(review_data, 'user_001')

        mock_movie_ctrl.get_movie_by_id.assert_called_once_with('1')
        mock_review_dao.create_review.assert_called_once()
        assert isinstance(result, ReviewSchema)
        assert result.review_id == 'rev_001'

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance'
    )
    def test_create_review_movie_not_found(
        self, mock_movie_ctrl, controller, mock_review_dao
    ):
        """Test creating review for non-existent movie."""
        mock_movie_ctrl.get_movie_by_id.side_effect = HTTPException(
            status_code=404, detail="Movie not found"
        )

        review_data = ReviewCreateSchema(
            movie_id='999',
            rating=4.5,
            review_text='Great movie!'
        )

        with pytest.raises(HTTPException) as exc_info:
            controller.create_review(review_data, 'user_001')

        assert exc_info.value.status_code == 404
        mock_review_dao.create_review.assert_not_called()

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance'
    )
    def test_create_review_duplicate(
        self, mock_movie_ctrl, controller, mock_review_dao
    ):
        """Test creating duplicate review (user already reviewed)."""
        mock_movie_ctrl.get_movie_by_id.return_value = {
            'id': '1', 'title': 'Test Movie'
        }
        mock_review_dao.create_review.side_effect = ValueError(
            "User user_001 already reviewed movie 1"
        )

        review_data = ReviewCreateSchema(
            movie_id='1',
            rating=4.5,
            review_text='Great movie!'
        )

        with pytest.raises(HTTPException) as exc_info:
            controller.create_review(review_data, 'user_001')

        assert exc_info.value.status_code == 400
        assert 'already reviewed' in str(exc_info.value.detail)


class TestReviewControllerUpdateOperations:
    """Test UPDATE operations (authenticated endpoints)."""

    def test_update_review_success(
        self, controller, mock_review_dao, sample_review
    ):
        """Test updating a review successfully."""
        mock_review_dao.get_review.return_value = sample_review
        updated_review = {
            **sample_review, 'rating': 5.0, 'review_text': 'Amazing!'
        }
        mock_review_dao.update_review.return_value = updated_review

        update_data = ReviewUpdateSchema(
            rating=5.0,
            review_text='Amazing!'
        )

        result = controller.update_review(
            'rev_001', update_data, 'user_001'
        )

        assert isinstance(result, ReviewSchema)
        assert result.rating == 5.0
        assert result.review_text == 'Amazing!'

    def test_update_review_not_found(
        self, controller, mock_review_dao
    ):
        """Test updating non-existent review."""
        mock_review_dao.get_review.side_effect = KeyError('Not found')

        update_data = ReviewUpdateSchema(rating=5.0)

        with pytest.raises(HTTPException) as exc_info:
            controller.update_review(
                'nonexistent', update_data, 'user_001'
            )

        assert exc_info.value.status_code == 404

    def test_update_review_unauthorized(
        self, controller, mock_review_dao, sample_review
    ):
        """Test updating another user's review (forbidden)."""
        mock_review_dao.get_review.return_value = sample_review

        update_data = ReviewUpdateSchema(rating=5.0)

        with pytest.raises(HTTPException) as exc_info:
            controller.update_review(
                'rev_001', update_data, 'user_002'
            )

        assert exc_info.value.status_code == 403
        assert 'only update your own' in str(exc_info.value.detail)
        mock_review_dao.update_review.assert_not_called()

    def test_update_imdb_review_forbidden(
        self, controller, mock_review_dao, sample_imdb_review
    ):
        """Test updating IMDB review is forbidden."""
        mock_review_dao.get_review.return_value = sample_imdb_review

        update_data = ReviewUpdateSchema(rating=5.0)

        with pytest.raises(HTTPException) as exc_info:
            # Use None as current_user to bypass ownership check
            controller.update_review(
                'imdb_001', update_data, None
            )

        assert exc_info.value.status_code == 403
        assert 'IMDB' in str(exc_info.value.detail)
        mock_review_dao.update_review.assert_not_called()

    def test_update_review_no_fields(
        self, controller, mock_review_dao, sample_review
    ):
        """Test updating with no fields raises error."""
        mock_review_dao.get_review.return_value = sample_review

        update_data = ReviewUpdateSchema()

        with pytest.raises(HTTPException) as exc_info:
            controller.update_review(
                'rev_001', update_data, 'user_001'
            )

        assert exc_info.value.status_code == 400
        assert 'No fields to update' in str(exc_info.value.detail)


class TestReviewControllerDeleteOperations:
    """Test DELETE operations (authenticated endpoints)."""

    def test_delete_review_success(
        self, controller, mock_review_dao, sample_review
    ):
        """Test deleting a review successfully."""
        mock_review_dao.get_review.return_value = sample_review
        mock_review_dao.delete_review.return_value = None

        result = controller.delete_review('rev_001', 'user_001')

        mock_review_dao.delete_review.assert_called_once_with('rev_001')
        assert 'deleted successfully' in result['message']

    def test_delete_review_not_found(
        self, controller, mock_review_dao
    ):
        """Test deleting non-existent review."""
        mock_review_dao.get_review.side_effect = KeyError('Not found')

        with pytest.raises(HTTPException) as exc_info:
            controller.delete_review('nonexistent', 'user_001')

        assert exc_info.value.status_code == 404
        mock_review_dao.delete_review.assert_not_called()

    def test_delete_review_unauthorized(
        self, controller, mock_review_dao, sample_review
    ):
        """Test deleting another user's review (forbidden)."""
        mock_review_dao.get_review.return_value = sample_review

        with pytest.raises(HTTPException) as exc_info:
            controller.delete_review('rev_001', 'user_002')

        assert exc_info.value.status_code == 403
        assert 'only delete your own' in str(exc_info.value.detail)
        mock_review_dao.delete_review.assert_not_called()

    def test_delete_imdb_review_forbidden(
        self, controller, mock_review_dao, sample_imdb_review
    ):
        """Test deleting IMDB review is forbidden."""
        mock_review_dao.get_review.return_value = sample_imdb_review

        with pytest.raises(HTTPException) as exc_info:
            # Use None as current_user to bypass ownership check
            controller.delete_review('imdb_001', None)

        assert exc_info.value.status_code == 403
        assert 'IMDB' in str(exc_info.value.detail)
        mock_review_dao.delete_review.assert_not_called()

    def test_admin_delete_review_success(
        self, controller, mock_review_dao, sample_review
    ):
        """Test admin deleting any review."""
        mock_review_dao.get_review.return_value = sample_review
        mock_review_dao.delete_review.return_value = None

        result = controller.admin_delete_review('rev_001')

        mock_review_dao.delete_review.assert_called_once_with('rev_001')
        assert 'admin' in result['message']

    def test_admin_delete_review_not_found(
        self, controller, mock_review_dao
    ):
        """Test admin deleting non-existent review."""
        mock_review_dao.get_review.side_effect = KeyError('Not found')

        with pytest.raises(HTTPException) as exc_info:
            controller.admin_delete_review('nonexistent')

        assert exc_info.value.status_code == 404

    def test_admin_delete_imdb_review_forbidden(
        self, controller, mock_review_dao, sample_imdb_review
    ):
        """Test admin cannot delete IMDB reviews."""
        mock_review_dao.get_review.return_value = sample_imdb_review

        with pytest.raises(HTTPException) as exc_info:
            controller.admin_delete_review('imdb_001')

        assert exc_info.value.status_code == 403
        assert 'IMDB' in str(exc_info.value.detail)
        mock_review_dao.delete_review.assert_not_called()


class TestReviewControllerHelpers:
    """Test helper methods and edge cases."""

    def test_dict_to_schema_conversion(
        self, controller, sample_review
    ):
        """Test conversion from dict to ReviewSchema."""
        schema = controller._dict_to_schema(sample_review)

        assert isinstance(schema, ReviewSchema)
        assert schema.review_id == sample_review['review_id']
        assert schema.rating == sample_review['rating']
