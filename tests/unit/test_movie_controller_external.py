import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from keyboard_smashers.controllers.movie_controller import MovieController
from keyboard_smashers.external_services.movie_service import (
    ExternalMovieResult)


@pytest.fixture
def mock_movie_dao():
    dao = Mock()
    dao.movies = {}
    dao.get_all_movies = Mock(return_value=[])
    dao.get_movie = Mock()
    dao.create_movie = Mock()
    return dao


@pytest.fixture
def mock_external_service():
    service = Mock()
    return service


@pytest.fixture
def mock_review_dao():
    dao = Mock()
    dao.get_reviews_for_movie = Mock(return_value=[])
    return dao


@pytest.fixture
def controller_with_external_service(
    mock_movie_dao, mock_external_service, mock_review_dao
):
    with patch('keyboard_smashers.controllers.movie_controller.MovieDAO') as (
        mock_dao_class), \
            patch('keyboard_smashers.controllers.movie_controller.'
                  'review_dao_instance', mock_review_dao), \
            patch.dict('os.environ', {'TMDB_API_KEY': 'test_key'}), \
            patch('keyboard_smashers.controllers.movie_controller.'
                  'ExternalMovieService') as mock_service_class:

        mock_dao_class.return_value = mock_movie_dao
        mock_service_class.return_value = mock_external_service

        controller = MovieController()
        return controller


@pytest.fixture
def controller_without_external_service(mock_movie_dao, mock_review_dao):
    with patch('keyboard_smashers.controllers.movie_controller.MovieDAO') as (
        mock_dao_class), \
            patch('keyboard_smashers.controllers.movie_controller.'
                  'review_dao_instance', mock_review_dao), \
            patch.dict('os.environ', {}, clear=True):

        mock_dao_class.return_value = mock_movie_dao
        controller = MovieController()
        return controller


@pytest.fixture
def sample_external_movie():
    return ExternalMovieResult(
        external_id="27205",
        title="Inception",
        genre="Action/Science Fiction",
        year=2010,
        director="Christopher Nolan",
        description="Cobb, a skilled thief who commits corporate espionage...",
        poster_url="https://image.tmdb.org/t/p/w500/inception.jpg",
        rating=8.4
    )


class TestSearchExternalMovies:

    def test_search_external_movies_success(
        self, controller_with_external_service, sample_external_movie
    ):
        service = controller_with_external_service.external_service
        service.search_movies.return_value = [sample_external_movie]

        results = controller_with_external_service.search_external_movies(
            "inception", limit=5
        )

        assert len(results) == 1
        assert results[0].title == "Inception"
        mock_service = controller_with_external_service.external_service
        mock_service.search_movies.assert_called_once_with("inception", 5)

    def test_search_external_movies_handles_service_error(
        self, controller_with_external_service
    ):
        mock_service = controller_with_external_service.external_service
        mock_service.search_movies.side_effect = Exception("API Error")

        with pytest.raises(HTTPException) as exc_info:
            controller_with_external_service.search_external_movies("test")

        assert exc_info.value.status_code == 503
        assert "failed" in exc_info.value.detail.lower()

    def test_search_external_movies_empty_results(
        self, controller_with_external_service
    ):
        mock_service = controller_with_external_service.external_service
        mock_service.search_movies.return_value = []
        results = controller_with_external_service.search_external_movies(
            "nonexistent")

        assert results == []

    def test_search_external_movies_respects_limit(
        self, controller_with_external_service, sample_external_movie
    ):
        mock_service = controller_with_external_service.external_service
        mock_service.search_movies.return_value = [
            sample_external_movie] * 10

        results = controller_with_external_service.search_external_movies(
            "test", limit=3
        )

        mock_service.search_movies.assert_called_once_with("test", 3)
        assert len(results) == 10


class TestImportMovieFromExternal:

    def test_import_movie_success(
        self, controller_with_external_service, sample_external_movie
    ):
        controller = controller_with_external_service
        mock_service = controller.external_service
        mock_dao = controller.movie_dao
        mock_service.get_movie_by_id.return_value = sample_external_movie
        mock_dao.get_all_movies.return_value = []
        mock_dao.create_movie.return_value = {
            'movie_id': '11',
            'title': 'Inception',
            'genre': 'Action/Science Fiction',
            'year': 2010,
            'director': 'Christopher Nolan',
            'description': 'Cobb, a skilled thief...'}

        result = controller_with_external_service.import_movie_from_external(
            "27205")

        assert result.title == "Inception"
        assert result.year == 2010
        mock_service.get_movie_by_id.assert_called_once_with("27205")
        mock_dao.create_movie.assert_called_once()

    def test_import_movie_not_found_in_external(
        self, controller_with_external_service
    ):
        controller = controller_with_external_service
        controller.external_service.get_movie_by_id.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            controller_with_external_service.import_movie_from_external(
                "999999")

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    def test_import_movie_already_exists_locally(
        self, controller_with_external_service, sample_external_movie
    ):
        controller = controller_with_external_service
        controller.external_service.get_movie_by_id.return_value = (
            sample_external_movie
        )
        controller.movie_dao.get_all_movies.return_value = [
            {'movie_id': '1', 'title': 'inception', 'genre': 'Action',
             'year': 2010}
        ]

        with pytest.raises(HTTPException) as exc_info:
            controller_with_external_service.import_movie_from_external(
                "27205")

        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail.lower()

    def test_import_movie_case_insensitive_duplicate_check(
        self, controller_with_external_service, sample_external_movie
    ):
        controller = controller_with_external_service
        controller.external_service.get_movie_by_id.return_value = (
            sample_external_movie
        )
        controller.movie_dao.get_all_movies.return_value = [
            {'movie_id': '1', 'title': 'INCEPTION', 'genre': 'Action',
             'year': 2010}
        ]

        with pytest.raises(HTTPException) as exc_info:
            controller_with_external_service.import_movie_from_external(
                "27205")

        assert exc_info.value.status_code == 409

    def test_import_movie_transforms_data_correctly(
        self, controller_with_external_service, sample_external_movie
    ):
        controller = controller_with_external_service
        controller.external_service.get_movie_by_id.return_value = (
           sample_external_movie
        )
        controller.movie_dao.get_all_movies.return_value = []

        created_data = None

        def capture_create(data):
            nonlocal created_data
            created_data = data
            return {
                'movie_id': '11',
                'title': data['title'],
                'genre': data['genre'],
                'year': data['year'],
                'director': data['director'],
                'description': data['description']
            }

        controller = controller_with_external_service
        controller.movie_dao.create_movie.side_effect = capture_create
        controller_with_external_service.import_movie_from_external("27205")

        assert created_data['title'] == "Inception"
        assert created_data['genre'] == "Action/Science Fiction"
        assert created_data['year'] == 2010
        assert created_data['director'] == "Christopher Nolan"


class TestSearchAndImportSuggestions:

    def test_search_and_import_without_auto_import(
        self, controller_with_external_service, sample_external_movie
    ):
        controller = controller_with_external_service
        controller.external_service.search_movies.return_value = [
            sample_external_movie
        ]

        result = controller.search_and_import_suggestions(
            "inception", auto_import=False
        )

        assert result['query'] == "inception"
        assert len(result['results']) == 1
        assert result['imported'] is None
        assert result['message'] == "Search completed"

    def test_search_and_import_with_auto_import_success(
        self, controller_with_external_service, sample_external_movie
    ):
        controller = controller_with_external_service
        mock_service = controller.external_service
        mock_dao = controller.movie_dao

        mock_service.search_movies.return_value = [sample_external_movie]
        mock_service.get_movie_by_id.return_value = sample_external_movie
        mock_dao.get_all_movies.return_value = []
        mock_dao.create_movie.return_value = {
            'movie_id': '11',
            'title': 'Inception',
            'genre': 'Action/Science Fiction',
            'year': 2010,
            'director': 'Christopher Nolan',
            'description': 'Cobb...'}

        result = (
            controller_with_external_service.search_and_import_suggestions)(
            "inception", auto_import=True)

        assert result['query'] == "inception"
        assert len(result['results']) == 1
        assert result['imported'] is not None
        assert result['imported'].title == "Inception"
        assert "Imported" in result['message']

    def test_search_and_import_no_results(
        self, controller_with_external_service
    ):
        service = controller_with_external_service.external_service
        service.search_movies.return_value = []

        result = (
            controller_with_external_service.search_and_import_suggestions)(
            "nonexistent")

        assert result['query'] == "nonexistent"
        assert result['results'] == []
        assert result['imported'] is None
        assert result['message'] == "No movies found"

    def test_search_and_import_limits_search_results(
        self, controller_with_external_service, sample_external_movie
    ):
        many_movies = [sample_external_movie] * 10
        controller = controller_with_external_service
        service = controller.external_service

        service.search_movies.return_value = many_movies

        service.search_movies.assert_called_once_with("test", limit=5)

    def test_search_and_import_only_imports_top_result(
        self, controller_with_external_service
    ):
        movie1 = ExternalMovieResult(
            external_id="1", title="Movie 1", genre="Action",
            year=2020, director="Director", description="Desc"
        )
        movie2 = ExternalMovieResult(
            external_id="2", title="Movie 2", genre="Drama",
            year=2021, director="Director", description="Desc"
        )

        controller = controller_with_external_service
        service = controller.external_service
        dao = controller.movie_dao

        service.search_movies.return_value = [movie1, movie2]
        service.get_movie_by_id.return_value = movie1
        dao.get_all_movies.return_value = []
        dao.create_movie.return_value = {
            'movie_id': '10',
            'title': 'Movie 1',
            'genre': 'Action',
            'year': 2020,
            'director': 'Director',
            'description': 'Desc'
        }

        controller = controller_with_external_service
        service = controller.external_service

        result = controller.search_and_import_suggestions(
            "test",
            auto_import=True
        )

        service.get_movie_by_id.assert_called_once_with("1")
        assert result['imported'].title == "Movie 1"


class TestExternalServiceIntegration:

    def test_controller_initializes_without_api_key(
            self, mock_movie_dao, mock_review_dao):
        with patch(
            'keyboard_smashers.controllers.movie_controller.MovieDAO'
        ) as mock_dao_class, patch(
            'keyboard_smashers.controllers.movie_controller.'
            'review_dao_instance',
            mock_review_dao
        ), patch.dict(
           'os.environ', {}, clear=True
        ):

            mock_dao_class.return_value = mock_movie_dao
            controller = MovieController()

            assert controller.external_service is None

    def test_controller_initializes_with_api_key(
            self, mock_movie_dao, mock_review_dao):
        with patch(
            'keyboard_smashers.controllers.movie_controller.MovieDAO'
        ) as mock_dao_class, patch(
            'keyboard_smashers.controllers.movie_controller.'
            'review_dao_instance',
            mock_review_dao
        ), patch.dict(
            'os.environ', {'TMDB_API_KEY': 'test_key'}
        ), patch(
            'keyboard_smashers.controllers.movie_controller.'
            'ExternalMovieService'
        ) as mock_service_class:
            mock_dao_class.return_value = mock_movie_dao
            controller = MovieController()

            assert controller.external_service is not None
            mock_service_class.assert_called_once_with('test_key')
