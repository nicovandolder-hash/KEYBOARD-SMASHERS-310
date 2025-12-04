import pytest
from unittest.mock import Mock, patch
import requests
from keyboard_smashers.external_services.movie_service import (
    ExternalMovieService,
    ExternalMovieResult
)


@pytest.fixture
def mock_api_key():
    return "test_api_key_12345"


@pytest.fixture
def external_service(mock_api_key):
    return ExternalMovieService(mock_api_key)


@pytest.fixture
def mock_genre_response():
    return {
        "genres": [
            {"id": 28, "name": "Action"},
            {"id": 12, "name": "Adventure"},
            {"id": 878, "name": "Science Fiction"}
        ]
    }


@pytest.fixture
def mock_search_response():
    return {
        "results": [
            {
                "id": 27205,
                "title": "Inception",
                "genre_ids": [28, 878],
                "release_date": "2010-07-16",
                "overview": "Cobb, a skilled thief...",
                "poster_path": "/inception.jpg",
                "vote_average": 8.4
            },
            {
                "id": 603,
                "title": "The Matrix",
                "genre_ids": [28, 878],
                "release_date": "1999-03-31",
                "overview": "Set in the 22nd century...",
                "poster_path": "/matrix.jpg",
                "vote_average": 8.7
            }
        ]
    }


@pytest.fixture
def mock_credits_response():
    return {
        "crew": [
            {"name": "Christopher Nolan", "job": "Director"},
            {"name": "Emma Thomas", "job": "Producer"}
        ]
    }


@pytest.fixture
def mock_movie_details_response():
    return {
        "id": 27205,
        "title": "Inception",
        "genres": [
            {"id": 28, "name": "Action"},
            {"id": 878, "name": "Science Fiction"}
        ],
        "release_date": "2010-07-16",
        "overview": "Cobb, a skilled thief...",
        "poster_path": "/inception.jpg",
        "vote_average": 8.4
    }


class TestExternalMovieServiceInitialization:

    def test_service_initializes_with_api_key(self, mock_api_key):
        service = ExternalMovieService(mock_api_key)
        assert service.api_key == mock_api_key
        assert service.base_url == "https://api.themoviedb.org/3"
        assert service.genre_cache is None

    def test_service_stores_base_url(self, external_service):
        assert external_service.base_url == "https://api.themoviedb.org/3"


class TestGenreMapping:

    @patch('requests.get')
    def test_get_genre_mapping_success(
        self, mock_get, external_service, mock_genre_response
    ):
        mock_response = Mock()
        mock_response.json.return_value = mock_genre_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = external_service._get_genre_mapping()

        assert result == {
            28: "Action",
            12: "Adventure",
            878: "Science Fiction"}
        assert external_service.genre_cache is not None
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_get_genre_mapping_uses_cache(
        self, mock_get, external_service, mock_genre_response
    ):
        external_service.genre_cache = {28: "Action"}

        result = external_service._get_genre_mapping()

        assert result == {28: "Action"}
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_genre_mapping_handles_api_error(
        self, mock_get, external_service
    ):
        mock_get.side_effect = requests.exceptions.RequestException(
            "API Error")

        result = external_service._get_genre_mapping()

        assert result == {}

    @patch('requests.get')
    def test_get_genre_mapping_handles_empty_response(
        self, mock_get, external_service
    ):
        mock_response = Mock()
        mock_response.json.return_value = {"genres": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = external_service._get_genre_mapping()

        assert result == {}


class TestMovieCredits:

    @patch('requests.get')
    def test_get_movie_credits_success(
        self, mock_get, external_service, mock_credits_response
    ):
        mock_response = Mock()
        mock_response.json.return_value = mock_credits_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = external_service._get_movie_credits(27205)

        assert result == "Christopher Nolan"
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_get_movie_credits_no_director(self, mock_get, external_service):
        mock_response = Mock()
        mock_response.json.return_value = {
            "crew": [{"name": "Producer Name", "job": "Producer"}]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = external_service._get_movie_credits(27205)

        assert result == "Unknown"

    @patch('requests.get')
    def test_get_movie_credits_handles_api_error(
        self, mock_get, external_service
    ):
        mock_get.side_effect = requests.exceptions.RequestException(
            "API Error")

        result = external_service._get_movie_credits(27205)

        assert result == "Unknown"

    @patch('requests.get')
    def test_get_movie_credits_handles_timeout(
        self, mock_get, external_service
    ):
        mock_get.side_effect = requests.exceptions.Timeout()

        result = external_service._get_movie_credits(27205)

        assert result == "Unknown"


class TestSearchMovies:

    @patch.object(ExternalMovieService, '_get_movie_credits')
    @patch.object(ExternalMovieService, '_get_genre_mapping')
    @patch('requests.get')
    def test_search_movies_success(
        self, mock_get, mock_genre_map, mock_credits,
        external_service, mock_search_response
    ):
        mock_response = Mock()
        mock_response.json.return_value = mock_search_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        mock_genre_map.return_value = {28: "Action", 878: "Science Fiction"}
        mock_credits.return_value = "Christopher Nolan"

        results = external_service.search_movies("inception", limit=5)

        assert len(results) == 2
        assert isinstance(results[0], ExternalMovieResult)
        assert results[0].title == "Inception"
        assert results[0].year == 2010
        assert results[0].director == "Christopher Nolan"
        assert results[0].genre == "Action/Science Fiction"

    @patch.object(ExternalMovieService, '_get_movie_credits')
    @patch.object(ExternalMovieService, '_get_genre_mapping')
    @patch('requests.get')
    def test_search_movies_respects_limit(
        self, mock_get, mock_genre_map, mock_credits, external_service
    ):
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [{"id": i, "title": f"Movie {i}"} for i in range(20)]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        mock_genre_map.return_value = {}
        mock_credits.return_value = "Director"

        results = external_service.search_movies("test", limit=5)

        assert len(results) == 5

    @patch('requests.get')
    def test_search_movies_handles_api_error(
        self, mock_get, external_service
    ):
        mock_get.side_effect = requests.exceptions.RequestException(
            "API Error")

        with pytest.raises(Exception) as exc_info:
            external_service.search_movies("test")
        assert "Failed to search external movie database" in str(
            exc_info.value)

    @patch.object(ExternalMovieService, '_get_movie_credits')
    @patch.object(ExternalMovieService, '_get_genre_mapping')
    @patch('requests.get')
    def test_search_movies_handles_no_results(
        self, mock_get, mock_genre_map, mock_credits, external_service
    ):
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        mock_genre_map.return_value = {}

        results = external_service.search_movies("nonexistent")

        assert results == []

    @patch.object(ExternalMovieService, '_get_movie_credits')
    @patch.object(ExternalMovieService, '_get_genre_mapping')
    @patch('requests.get')
    def test_search_movies_builds_correct_url(
        self, mock_get, mock_genre_map, mock_credits,
        external_service, mock_search_response
    ):
        mock_response = Mock()
        mock_response.json.return_value = mock_search_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        mock_genre_map.return_value = {}
        mock_credits.return_value = "Director"

        external_service.search_movies("test query", limit=10)

        call_args = mock_get.call_args
        assert call_args[0][0] == "https://api.themoviedb.org/3/search/movie"
        assert call_args[1]["params"]["query"] == "test query"
        assert call_args[1]["params"]["api_key"] == "test_api_key_12345"


class TestGetMovieById:

    @patch.object(ExternalMovieService, '_get_movie_credits')
    @patch('requests.get')
    def test_get_movie_by_id_success(
        self, mock_get, mock_credits,
        external_service, mock_movie_details_response
    ):
        mock_response = Mock()
        mock_response.json.return_value = mock_movie_details_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        mock_credits.return_value = "Christopher Nolan"

        result = external_service.get_movie_by_id("27205")

        assert result is not None
        assert isinstance(result, ExternalMovieResult)
        assert result.external_id == "27205"
        assert result.title == "Inception"
        assert result.year == 2010
        assert result.director == "Christopher Nolan"

    @patch('requests.get')
    def test_get_movie_by_id_handles_api_error(
        self, mock_get, external_service
    ):
        mock_get.side_effect = requests.exceptions.RequestException(
            "API Error")

        result = external_service.get_movie_by_id("27205")

        assert result is None

    @patch.object(ExternalMovieService, '_get_movie_credits')
    @patch('requests.get')
    def test_get_movie_by_id_handles_404(
        self, mock_get, mock_credits, external_service
    ):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError("404")
        )
        mock_get.return_value = mock_response

        result = external_service.get_movie_by_id("999999")

        assert result is None

    @patch.object(ExternalMovieService, '_get_movie_credits')
    @patch('requests.get')
    def test_get_movie_by_id_handles_missing_fields(
        self, mock_get, mock_credits, external_service
    ):
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": 123,
            "genres": [],
            "release_date": ""
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        mock_credits.return_value = "Unknown"

        result = external_service.get_movie_by_id("123")

        assert result is not None
        assert result.title == "Unknown"
        assert result.year == 0
        assert result.genre == "Unknown"


class TestExternalMovieResult:

    def test_external_movie_result_creation(self):
        movie = ExternalMovieResult(
            external_id="123",
            title="Test Movie",
            genre="Action",
            year=2020,
            director="Test Director",
            description="Test description",
            poster_url="http://example.com/poster.jpg",
            rating=8.5
        )

        assert movie.external_id == "123"
        assert movie.title == "Test Movie"
        assert movie.genre == "Action"
        assert movie.year == 2020
        assert movie.director == "Test Director"
        assert movie.rating == 8.5

    def test_external_movie_result_optional_fields(self):
        movie = ExternalMovieResult(
            external_id="123",
            title="Test Movie",
            genre="Action",
            year=2020,
            director="Test Director",
            description="Test description"
        )

        assert movie.poster_url is None
        assert movie.rating is None
