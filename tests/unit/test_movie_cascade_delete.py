import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from keyboard_smashers.controllers.movie_controller import MovieController


@pytest.fixture
def mock_movie_dao():
    """Create a mock MovieDAO"""
    mock = Mock()
    mock.movies = {}
    return mock


@pytest.fixture
def mock_review_dao():
    """Create a mock ReviewDAO"""
    mock = Mock()
    return mock


@pytest.fixture
def controller(mock_movie_dao):
    """Create a MovieController instance with mocked DAO"""
    with patch('keyboard_smashers.controllers.movie_controller.MovieDAO',
               return_value=mock_movie_dao):
        controller = MovieController()
        controller.movie_dao = mock_movie_dao
        return controller


class TestDeleteMovieProtection:
    """Tests for protected legacy IMDB movies (IDs 1-10)"""

    def test_cannot_delete_movie_id_1(self, controller, mock_movie_dao):
        """Test that movie ID 1 cannot be deleted (protected)"""
        with pytest.raises(HTTPException) as exc_info:
            controller.delete_movie('1')

        assert exc_info.value.status_code == 403
        assert 'legacy imdb' in exc_info.value.detail.lower()
        mock_movie_dao.delete_movie.assert_not_called()

    def test_cannot_delete_movie_id_5(self, controller, mock_movie_dao):
        """Test that movie ID 5 cannot be deleted (protected)"""
        with pytest.raises(HTTPException) as exc_info:
            controller.delete_movie('5')

        assert exc_info.value.status_code == 403
        assert 'legacy imdb' in exc_info.value.detail.lower()
        mock_movie_dao.delete_movie.assert_not_called()

    def test_cannot_delete_movie_id_10(self, controller, mock_movie_dao):
        """Test that movie ID 10 cannot be deleted (protected)"""
        with pytest.raises(HTTPException) as exc_info:
            controller.delete_movie('10')

        assert exc_info.value.status_code == 403
        assert 'legacy imdb' in exc_info.value.detail.lower()
        mock_movie_dao.delete_movie.assert_not_called()

    @patch('keyboard_smashers.dao.review_dao.review_dao_instance')
    def test_can_delete_movie_id_11(self, mock_review_instance,
                                    controller, mock_movie_dao):
        """Test that movie ID 11 can be deleted (not protected)"""
        mock_review_instance.delete_reviews_by_movie.return_value = 0
        mock_movie_dao.delete_movie.return_value = None

        result = controller.delete_movie('11')

        assert 'deleted successfully' in result['message'].lower()
        mock_movie_dao.delete_movie.assert_called_once_with('11')

    @patch('keyboard_smashers.dao.review_dao.review_dao_instance')
    def test_can_delete_movie_id_100(self, mock_review_instance,
                                     controller, mock_movie_dao):
        """Test that movie ID 100 can be deleted (not protected)"""
        mock_review_instance.delete_reviews_by_movie.return_value = 0
        mock_movie_dao.delete_movie.return_value = None

        result = controller.delete_movie('100')

        assert 'deleted successfully' in result['message'].lower()
        mock_movie_dao.delete_movie.assert_called_once_with('100')

    @patch('keyboard_smashers.dao.review_dao.review_dao_instance')
    def test_can_delete_non_numeric_id(self, mock_review_instance,
                                       controller, mock_movie_dao):
        """Test that non-numeric movie IDs can be deleted"""
        mock_review_instance.delete_reviews_by_movie.return_value = 0
        mock_movie_dao.delete_movie.return_value = None

        result = controller.delete_movie('abc123')

        assert 'deleted successfully' in result['message'].lower()
        mock_movie_dao.delete_movie.assert_called_once_with('abc123')


class TestDeleteMovieCascade:
    """Tests for cascade delete of reviews when movie is deleted"""

    @patch('keyboard_smashers.dao.review_dao.review_dao_instance')
    def test_cascade_deletes_reviews(self, mock_review_instance,
                                     controller, mock_movie_dao):
        """Test that reviews are deleted when movie is deleted"""
        mock_review_instance.delete_reviews_by_movie.return_value = 5
        mock_movie_dao.delete_movie.return_value = None

        result = controller.delete_movie('15')

        mock_review_instance.delete_reviews_by_movie.assert_called_once_with(
            '15'
        )
        mock_movie_dao.delete_movie.assert_called_once_with('15')
        assert result['reviews_deleted'] == 5

    @patch('keyboard_smashers.dao.review_dao.review_dao_instance')
    def test_cascade_delete_zero_reviews(self, mock_review_instance,
                                         controller, mock_movie_dao):
        """Test deletion when movie has no reviews"""
        mock_review_instance.delete_reviews_by_movie.return_value = 0
        mock_movie_dao.delete_movie.return_value = None

        result = controller.delete_movie('20')

        mock_review_instance.delete_reviews_by_movie.assert_called_once_with(
            '20'
        )
        assert result['reviews_deleted'] == 0

    @patch('keyboard_smashers.dao.review_dao.review_dao_instance')
    def test_reviews_deleted_before_movie(self, mock_review_instance,
                                          controller, mock_movie_dao):
        """Test that reviews are deleted before the movie"""
        call_order = []

        def track_review_delete(movie_id):
            call_order.append('reviews')
            return 3

        def track_movie_delete(movie_id):
            call_order.append('movie')
            return None

        mock_review_instance.delete_reviews_by_movie.side_effect = \
            track_review_delete
        mock_movie_dao.delete_movie.side_effect = track_movie_delete

        controller.delete_movie('25')

        assert call_order == ['reviews', 'movie']

    @patch('keyboard_smashers.dao.review_dao.review_dao_instance')
    def test_movie_not_found_after_review_delete(self, mock_review_instance,
                                                 controller, mock_movie_dao):
        """Test error handling when movie not found"""
        mock_review_instance.delete_reviews_by_movie.return_value = 0
        mock_movie_dao.delete_movie.side_effect = KeyError("Movie not found")

        with pytest.raises(HTTPException) as exc_info:
            controller.delete_movie('999')

        assert exc_info.value.status_code == 404
