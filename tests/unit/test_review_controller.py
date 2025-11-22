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
def mock_report_dao():
    """Mock ReportDAO for testing controller logic."""
    dao = Mock()
    return dao


@pytest.fixture
def controller(mock_review_dao, mock_report_dao):
    """Create ReviewController with mocked DAOs."""
    with patch(
        'keyboard_smashers.controllers.review_controller.ReviewDAO'
    ) as mock_dao_class:
        mock_dao_class.return_value = mock_review_dao
        controller = ReviewController(
            imdb_csv_path="test.csv",
            new_reviews_csv_path="test_new.csv"
        )
        controller.review_dao = mock_review_dao
        controller.report_dao = mock_report_dao
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

    def test_admin_delete_review_cascades_reports(
        self, controller, mock_review_dao, mock_report_dao, sample_review
    ):
        """Test that deleting a review also deletes associated reports."""
        mock_review_dao.get_review.return_value = sample_review
        mock_review_dao.delete_review.return_value = None
        mock_report_dao.delete_reports_by_review.return_value = 3

        result = controller.admin_delete_review('rev_001')

        # Verify review was deleted
        mock_review_dao.delete_review.assert_called_once_with('rev_001')
        # Verify reports were cascade deleted
        mock_report_dao.delete_reports_by_review.assert_called_once_with(
            'rev_001'
        )
        # Verify response includes deleted reports count
        assert result['deleted_reports'] == 3
        assert 'admin' in result['message']


class TestReviewControllerAdminReportDeletion:
    """Test admin report deletion operations."""

    def test_admin_delete_report_success(
        self, controller, mock_report_dao
    ):
        """Test successful report deletion by admin."""
        mock_report = {
            'report_id': 'report_000001',
            'review_id': 'rev_001',
            'reporting_user_id': 'user_001',
            'reason': 'spam',
            'admin_viewed': False,
            'timestamp': '2024-01-01T10:00:00'
        }
        mock_report_dao.get_report.return_value = mock_report
        mock_report_dao.delete_report.return_value = True

        result = controller.admin_delete_report('report_000001')

        mock_report_dao.get_report.assert_called_once_with('report_000001')
        mock_report_dao.delete_report.assert_called_once_with('report_000001')
        assert result['message'] == "Report 'report_000001' deleted by admin"
        assert result['review_id'] == 'rev_001'

    def test_admin_delete_report_not_found(
        self, controller, mock_report_dao
    ):
        """Test deleting a non-existent report."""
        mock_report_dao.get_report.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            controller.admin_delete_report('report_999999')

        assert exc_info.value.status_code == 404
        assert 'not found' in str(exc_info.value.detail).lower()
        mock_report_dao.delete_report.assert_not_called()

    def test_admin_delete_report_failure(
        self, controller, mock_report_dao
    ):
        """Test when report deletion fails."""
        mock_report = {
            'report_id': 'report_000001',
            'review_id': 'rev_001',
            'reporting_user_id': 'user_001',
            'reason': 'spam',
            'admin_viewed': False,
            'timestamp': '2024-01-01T10:00:00'
        }
        mock_report_dao.get_report.return_value = mock_report
        mock_report_dao.delete_report.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            controller.admin_delete_report('report_000001')

        assert exc_info.value.status_code == 500
        assert 'failed' in str(exc_info.value.detail).lower()


class TestReviewControllerReportedReviewsRetrieval:
    """Test admin retrieval of reported reviews."""

    def test_get_reported_reviews_success(
        self, controller, mock_report_dao, mock_review_dao
    ):
        """Test successful retrieval of reported reviews with pagination."""
        # Mock reports
        mock_reports = [
            {
                'report_id': 'report_000001',
                'review_id': 'rev_001',
                'reporting_user_id': 'user_001',
                'reason': 'spam',
                'admin_viewed': False,
                'timestamp': datetime(2024, 1, 3, 10, 0, 0)
            },
            {
                'report_id': 'report_000002',
                'review_id': 'rev_002',
                'reporting_user_id': 'user_002',
                'reason': 'offensive',
                'admin_viewed': True,
                'timestamp': datetime(2024, 1, 2, 10, 0, 0)
            },
            {
                'report_id': 'report_000003',
                'review_id': 'rev_003',
                'reporting_user_id': 'user_003',
                'reason': 'inappropriate',
                'admin_viewed': False,
                'timestamp': datetime(2024, 1, 1, 10, 0, 0)
            }
        ]
        mock_report_dao.get_all_reports.return_value = mock_reports

        # Mock reviews
        mock_reviews = {
            'rev_001': {
                'review_id': 'rev_001',
                'movie_id': 'movie_001',
                'user_id': 'user_123',
                'rating': 4.5,
                'review_text': 'Great movie!',
                'imdb_username': None
            },
            'rev_002': {
                'review_id': 'rev_002',
                'movie_id': 'movie_002',
                'user_id': 'user_456',
                'rating': 2.0,
                'review_text': 'Not good',
                'imdb_username': None
            },
            'rev_003': {
                'review_id': 'rev_003',
                'movie_id': 'movie_003',
                'user_id': None,
                'rating': 5.0,
                'review_text': 'Amazing!',
                'imdb_username': 'imdb_user'
            }
        }
        mock_review_dao.get_review.side_effect = lambda rid: mock_reviews[rid]

        result = controller.get_reported_reviews_for_admin(skip=0, limit=50)

        assert result['total'] == 3
        assert len(result['reports']) == 3
        assert result['skip'] == 0
        assert result['limit'] == 50
        assert result['has_more'] is False

        # Verify sorted by timestamp (newest first)
        assert result['reports'][0]['report_id'] == 'report_000001'
        assert result['reports'][1]['report_id'] == 'report_000002'
        assert result['reports'][2]['report_id'] == 'report_000003'

        # Verify report data
        first_report = result['reports'][0]
        assert first_report['review_id'] == 'rev_001'
        assert first_report['reason'] == 'spam'
        assert first_report['admin_viewed'] is False

        # Verify review data is included
        assert first_report['review_text'] == 'Great movie!'
        assert first_report['rating'] == 4.5
        assert first_report['movie_id'] == 'movie_001'
        assert first_report['reviewer_user_id'] == 'user_123'

    def test_get_reported_reviews_pagination(
        self, controller, mock_report_dao, mock_review_dao
    ):
        """Test pagination with skip and limit."""
        # Create 10 mock reports
        mock_reports = []
        for i in range(10):
            mock_reports.append({
                'report_id': f'report_{str(i).zfill(6)}',
                'review_id': f'rev_{str(i).zfill(3)}',
                'reporting_user_id': f'user_{str(i).zfill(3)}',
                'reason': 'test',
                'admin_viewed': False,
                'timestamp': datetime(2024, 1, i + 1, 10, 0, 0)
            })
        mock_report_dao.get_all_reports.return_value = mock_reports

        # Mock review lookup
        def get_review_mock(review_id):
            return {
                'review_id': review_id,
                'movie_id': 'movie_001',
                'user_id': 'user_001',
                'rating': 3.0,
                'review_text': 'Review text',
                'imdb_username': None
            }
        mock_review_dao.get_review.side_effect = get_review_mock

        # Test first page
        result = controller.get_reported_reviews_for_admin(skip=0, limit=5)
        assert result['total'] == 10
        assert len(result['reports']) == 5
        assert result['has_more'] is True
        assert result['reports'][0]['report_id'] == 'report_000009'

        # Test second page
        result = controller.get_reported_reviews_for_admin(skip=5, limit=5)
        assert result['total'] == 10
        assert len(result['reports']) == 5
        assert result['has_more'] is False
        assert result['reports'][0]['report_id'] == 'report_000004'

    def test_get_reported_reviews_empty(
        self, controller, mock_report_dao
    ):
        """Test when there are no reported reviews."""
        mock_report_dao.get_all_reports.return_value = []

        result = controller.get_reported_reviews_for_admin(skip=0, limit=50)

        assert result['total'] == 0
        assert len(result['reports']) == 0
        assert result['has_more'] is False

    def test_get_reported_reviews_with_deleted_review(
        self, controller, mock_report_dao, mock_review_dao
    ):
        """Test handling of reports for deleted reviews."""
        mock_reports = [
            {
                'report_id': 'report_000001',
                'review_id': 'rev_001',
                'reporting_user_id': 'user_001',
                'reason': 'spam',
                'admin_viewed': False,
                'timestamp': datetime(2024, 1, 2, 10, 0, 0)
            },
            {
                'report_id': 'report_000002',
                'review_id': 'rev_deleted',
                'reporting_user_id': 'user_002',
                'reason': 'offensive',
                'admin_viewed': False,
                'timestamp': datetime(2024, 1, 1, 10, 0, 0)
            }
        ]
        mock_report_dao.get_all_reports.return_value = mock_reports

        # First review exists, second is deleted
        def get_review_mock(review_id):
            if review_id == 'rev_001':
                return {
                    'review_id': 'rev_001',
                    'movie_id': 'movie_001',
                    'user_id': 'user_001',
                    'rating': 3.0,
                    'review_text': 'Review',
                    'imdb_username': None
                }
            raise KeyError(f"Review {review_id} not found")

        mock_review_dao.get_review.side_effect = get_review_mock

        result = controller.get_reported_reviews_for_admin(skip=0, limit=50)

        # Should skip deleted review
        assert result['total'] == 2  # Total reports still 2
        assert len(result['reports']) == 1  # But only 1 returned
        assert result['reports'][0]['report_id'] == 'report_000001'

    def test_get_reported_reviews_includes_imdb_reviews(
        self, controller, mock_report_dao, mock_review_dao
    ):
        """Test that IMDB reviews are properly included."""
        mock_reports = [
            {
                'report_id': 'report_000001',
                'review_id': 'imdb_rev_001',
                'reporting_user_id': 'user_001',
                'reason': 'inappropriate',
                'admin_viewed': False,
                'timestamp': datetime(2024, 1, 1, 10, 0, 0)
            }
        ]
        mock_report_dao.get_all_reports.return_value = mock_reports

        mock_review_dao.get_review.return_value = {
            'review_id': 'imdb_rev_001',
            'movie_id': 'movie_001',
            'user_id': None,  # IMDB review
            'rating': 4.0,
            'review_text': 'IMDB review text',
            'imdb_username': 'john_doe'
        }

        result = controller.get_reported_reviews_for_admin(skip=0, limit=50)

        assert len(result['reports']) == 1
        report = result['reports'][0]
        assert report['reviewer_user_id'] is None
        assert report['imdb_username'] == 'john_doe'

    def test_get_reported_reviews_filter_unviewed(
        self, controller, mock_report_dao, mock_review_dao
    ):
        """Test filtering for only unviewed reports."""
        mock_reports = [
            {
                'report_id': 'report_000001',
                'review_id': 'rev_001',
                'reporting_user_id': 'user_001',
                'reason': 'spam',
                'admin_viewed': False,
                'timestamp': datetime(2024, 1, 3, 10, 0, 0)
            },
            {
                'report_id': 'report_000002',
                'review_id': 'rev_002',
                'reporting_user_id': 'user_002',
                'reason': 'offensive',
                'admin_viewed': True,
                'timestamp': datetime(2024, 1, 2, 10, 0, 0)
            },
            {
                'report_id': 'report_000003',
                'review_id': 'rev_003',
                'reporting_user_id': 'user_003',
                'reason': 'inappropriate',
                'admin_viewed': False,
                'timestamp': datetime(2024, 1, 1, 10, 0, 0)
            }
        ]
        mock_report_dao.get_all_reports.return_value = mock_reports

        def get_review_mock(review_id):
            return {
                'review_id': review_id,
                'movie_id': 'movie_001',
                'user_id': 'user_001',
                'rating': 3.0,
                'review_text': 'Review',
                'imdb_username': None
            }
        mock_review_dao.get_review.side_effect = get_review_mock

        # Filter for unviewed only
        result = controller.get_reported_reviews_for_admin(
            skip=0, limit=50, admin_viewed=False
        )

        assert result['total'] == 2
        assert len(result['reports']) == 2
        assert result['reports'][0]['report_id'] == 'report_000001'
        assert result['reports'][1]['report_id'] == 'report_000003'
        assert all(not r['admin_viewed'] for r in result['reports'])

    def test_get_reported_reviews_filter_viewed(
        self, controller, mock_report_dao, mock_review_dao
    ):
        """Test filtering for only viewed reports."""
        mock_reports = [
            {
                'report_id': 'report_000001',
                'review_id': 'rev_001',
                'reporting_user_id': 'user_001',
                'reason': 'spam',
                'admin_viewed': False,
                'timestamp': datetime(2024, 1, 3, 10, 0, 0)
            },
            {
                'report_id': 'report_000002',
                'review_id': 'rev_002',
                'reporting_user_id': 'user_002',
                'reason': 'offensive',
                'admin_viewed': True,
                'timestamp': datetime(2024, 1, 2, 10, 0, 0)
            }
        ]
        mock_report_dao.get_all_reports.return_value = mock_reports

        def get_review_mock(review_id):
            return {
                'review_id': review_id,
                'movie_id': 'movie_001',
                'user_id': 'user_001',
                'rating': 3.0,
                'review_text': 'Review',
                'imdb_username': None
            }
        mock_review_dao.get_review.side_effect = get_review_mock

        # Filter for viewed only
        result = controller.get_reported_reviews_for_admin(
            skip=0, limit=50, admin_viewed=True
        )

        assert result['total'] == 1
        assert len(result['reports']) == 1
        assert result['reports'][0]['report_id'] == 'report_000002'
        assert result['reports'][0]['admin_viewed'] is True


class TestReviewControllerMarkReportViewed:
    """Test marking reports as viewed by admin."""

    def test_mark_report_as_viewed_success(
        self, controller, mock_report_dao
    ):
        """Test successfully marking report as viewed."""
        mock_report = {
            'report_id': 'report_000001',
            'review_id': 'rev_001',
            'reporting_user_id': 'user_001',
            'reason': 'spam',
            'admin_viewed': False,
            'timestamp': '2024-01-01T10:00:00'
        }
        mock_report_dao.get_report.return_value = mock_report
        mock_report_dao.mark_as_viewed.return_value = True

        result = controller.mark_report_as_viewed('report_000001')

        mock_report_dao.get_report.assert_called_once_with('report_000001')
        mock_report_dao.mark_as_viewed.assert_called_once_with('report_000001')
        assert result['report_id'] == 'report_000001'
        assert result['admin_viewed'] is True
        assert 'marked as viewed' in result['message']

    def test_mark_report_as_viewed_not_found(
        self, controller, mock_report_dao
    ):
        """Test marking non-existent report as viewed."""
        mock_report_dao.get_report.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            controller.mark_report_as_viewed('report_999999')

        assert exc_info.value.status_code == 404
        assert 'not found' in str(exc_info.value.detail).lower()
        mock_report_dao.mark_as_viewed.assert_not_called()

    def test_mark_report_as_viewed_failure(
        self, controller, mock_report_dao
    ):
        """Test when marking report as viewed fails."""
        mock_report = {
            'report_id': 'report_000001',
            'review_id': 'rev_001',
            'reporting_user_id': 'user_001',
            'reason': 'spam',
            'admin_viewed': False,
            'timestamp': '2024-01-01T10:00:00'
        }
        mock_report_dao.get_report.return_value = mock_report
        mock_report_dao.mark_as_viewed.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            controller.mark_report_as_viewed('report_000001')

        assert exc_info.value.status_code == 500
        assert 'failed' in str(exc_info.value.detail).lower()


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
