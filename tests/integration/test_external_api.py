import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from keyboard_smashers.api import app
from keyboard_smashers.auth import get_current_admin_user
from keyboard_smashers.external_services.movie_service import (
    ExternalMovieResult
)


@pytest.fixture
def client():
    def mock_get_current_admin_user():
        return "admin_user_123"

    app.dependency_overrides[get_current_admin_user] = (
        mock_get_current_admin_user)

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def mock_admin_token():
    return "mock_admin_token_12345"


@pytest.fixture
def sample_external_movie():
    return ExternalMovieResult(
        external_id="27205",
        title="Inception",
        genre="Action/Science Fiction",
        year=2010,
        director="Christopher Nolan",
        description=(
            "Cobb, a skilled thief who commits corporate espionage..."
        ),
        poster_url=(
            "https://image.tmdb.org/t/p/w500/inception.jpg"
        ),
        rating=8.4
    )


@pytest.fixture
def mock_external_service(sample_external_movie):
    service = Mock()
    service.search_movies = Mock(return_value=[sample_external_movie])
    service.get_movie_by_id = Mock(return_value=sample_external_movie)
    return service


class TestExternalSearchEndpoint:

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    def test_search_external_movies_endpoint_success(
        self, mock_service, client, sample_external_movie
    ):
        mock_service.search_movies.return_value = [sample_external_movie]

        response = client.get(
            "/movies/external/search?q=inception&limit=5"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['title'] == "Inception"
        assert data[0]['external_id'] == "27205"
        assert data[0]['director'] == "Christopher Nolan"

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    def test_search_external_movies_no_results(
        self, mock_service, client
    ):
        mock_service.search_movies.return_value = []

        response = client.get(
            "/movies/external/search?q=nonexistent"
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_search_external_movies_missing_query(self, client):
        response = client.get("/movies/external/search")
        assert response.status_code == 422

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    def test_search_external_movies_with_custom_limit(
        self, mock_service, client, sample_external_movie
    ):
        mock_service.search_movies.return_value = (
            [sample_external_movie] * 3
        )

        response = client.get(
            "/movies/external/search?q=test&limit=3"
        )

        assert response.status_code == 200
        mock_service.search_movies.assert_called_once_with("test", 3)

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service',
        None
    )
    def test_search_external_movies_service_not_configured(
        self, client
    ):
        response = client.get("/movies/external/search?q=test")

        assert response.status_code == 503
        assert (
            "not available"
            in response.json()['detail'].lower()
        )

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    def test_search_external_movies_service_error(
        self, mock_service, client
    ):
        mock_service.search_movies.side_effect = Exception("API Error")

        response = client.get("/movies/external/search?q=test")

        assert response.status_code == 503
        assert "failed" in response.json()['detail'].lower()


class TestImportMovieEndpoint:

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.movie_dao'
    )
    def test_import_movie_endpoint_success(
        self, mock_dao, mock_service, client,
        sample_external_movie
    ):
        mock_service.get_movie_by_id.return_value = (
            sample_external_movie
        )
        mock_dao.get_all_movies.return_value = []

        mock_dao.create_movie.return_value = {
            'movie_id': '11',
            'title': 'Inception',
            'genre': 'Action/Science Fiction',
            'year': 2010,
            'director': 'Christopher Nolan',
            'description': 'Cobb...'
        }

        response = client.post(
            "/movies/external/import/27205",
            headers={"Authorization": "Bearer mock_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['title'] == "Inception"
        assert data['movie_id'] == "11"

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.movie_dao'
    )
    def test_import_movie_already_exists(
        self, mock_dao, mock_service, client,
        sample_external_movie
    ):
        mock_service.get_movie_by_id.return_value = (
            sample_external_movie
        )
        mock_dao.get_all_movies.return_value = [
            {'movie_id': '1', 'title': 'inception', 'genre': 'Action'}
        ]

        response = client.post(
            "/movies/external/import/27205",
            headers={"Authorization": "Bearer mock_token"}
        )

        assert response.status_code == 409
        assert (
            "already exists"
            in response.json()['detail'].lower()
        )

    def test_import_movie_requires_auth(self, client):
        app.dependency_overrides.clear()
        response = client.post("/movies/external/import/27205")
        assert response.status_code == 401

    def mock_get_current_admin_user():
        return "admin_user_123"
    app.dependency_overrides[get_current_admin_user] = (
        mock_get_current_admin_user)

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    def test_import_movie_not_found_in_external(
        self, mock_service, client
    ):
        mock_service.get_movie_by_id.return_value = None

        response = client.post(
            "/movies/external/import/999999",
            headers={"Authorization": "Bearer mock_token"}
        )

        assert response.status_code == 404

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service',
        None
    )
    def test_import_movie_service_not_configured(
        self, client
    ):

        response = client.post(
            "/movies/external/import/27205",
            headers={"Authorization": "Bearer mock_token"}
        )

        assert response.status_code == 503


class TestSearchAndImportEndpoint:

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    def test_search_and_import_without_auto_import(
        self, mock_service, client,
        sample_external_movie
    ):
        mock_service.search_movies.return_value = [
            sample_external_movie
        ]

        response = client.post(
            "/movies/external/search-and-import?"
            "q=inception&auto_import=false",
            headers={"Authorization": "Bearer mock_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['query'] == "inception"
        assert len(data['results']) == 1
        assert data['imported'] is None
        assert "Search completed" in data['message']

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.movie_dao'
    )
    def test_search_and_import_with_auto_import(
        self, mock_dao, mock_service, client,
        sample_external_movie
    ):
        mock_service.search_movies.return_value = [
            sample_external_movie
        ]
        mock_service.get_movie_by_id.return_value = (
            sample_external_movie
        )
        mock_dao.get_all_movies.return_value = []

        mock_dao.create_movie.return_value = {
            'movie_id': '11',
            'title': 'Inception',
            'genre': 'Action/Science Fiction',
            'year': 2010,
            'director': 'Christopher Nolan',
            'description': 'Cobb...'
        }

        response = client.post(
            "/movies/external/search-and-import?"
            "q=inception&auto_import=true",
            headers={"Authorization": "Bearer mock_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['imported'] is not None
        assert data['imported']['title'] == "Inception"
        assert "Imported" in data['message']

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    def test_search_and_import_no_results(
        self, mock_service, client
    ):
        mock_service.search_movies.return_value = []

        response = client.post(
            "/movies/external/search-and-import?q=nonexistent",
            headers={"Authorization": "Bearer mock_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['results'] == []
        assert data['imported'] is None
        assert "No movies found" in data['message']

    def test_search_and_import_requires_auth(self, client):
        app.dependency_overrides.clear()
        response = client.post(
            "/movies/external/search-and-import?q=test"
        )
        assert response.status_code == 401

    def mock_get_current_admin_user():
        return "admin_user_123"
    app.dependency_overrides[get_current_admin_user] = (
        mock_get_current_admin_user)

    def test_search_and_import_missing_query(self, client):
        response = client.post(
            "/movies/external/search-and-import",
            headers={"Authorization": "Bearer mock_token"}
        )
        assert response.status_code == 422


class TestEndToEndWorkflow:

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.movie_dao'
    )
    def test_complete_search_and_import_workflow(
        self, mock_dao, mock_service, client,
        sample_external_movie
    ):
        mock_service.search_movies.return_value = [
            sample_external_movie
        ]
        mock_service.get_movie_by_id.return_value = (
            sample_external_movie
        )
        mock_dao.get_all_movies.return_value = []

        mock_dao.create_movie.return_value = {
            'movie_id': '11',
            'title': 'Inception',
            'genre': 'Action/Science Fiction',
            'year': 2010,
            'director': 'Christopher Nolan',
            'description': 'Cobb...'
        }

        search_resp = client.get(
            "/movies/external/search?q=inception"
        )
        assert search_resp.status_code == 200
        search_data = search_resp.json()
        assert len(search_data) > 0
        external_id = search_data[0]['external_id']

        import_resp = client.post(
            f"/movies/external/import/{external_id}",
            headers={"Authorization": "Bearer mock_token"}
        )
        assert import_resp.status_code == 200
        assert import_resp.json()['title'] == "Inception"

        mock_dao.get_all_movies.return_value = [
            {'movie_id': '11', 'title': 'inception', 'genre': 'Action'}
        ]

        dup_resp = client.post(
            f"/movies/external/import/{external_id}",
            headers={"Authorization": "Bearer mock_token"}
        )
        assert dup_resp.status_code == 409

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.movie_dao'
    )
    def test_search_review_and_import_workflow(
        self, mock_dao, mock_service, client
    ):
        movie1 = ExternalMovieResult(
            external_id="1",
            title="Good Movie",
            genre="Action",
            year=2020,
            director="Director A",
            description="Great",
            rating=8.5
        )
        movie2 = ExternalMovieResult(
            external_id="2",
            title="Bad Movie",
            genre="Drama",
            year=2021,
            director="Director B",
            description="Meh",
            rating=3.2
        )

        mock_service.search_movies.return_value = [
            movie1, movie2
        ]
        mock_service.get_movie_by_id.return_value = movie1
        mock_dao.get_all_movies.return_value = []

        mock_dao.create_movie.return_value = {
            'movie_id': '10',
            'title': 'Good Movie',
            'genre': 'Action',
            'year': 2020,
            'director': 'Director A',
            'description': 'Great'
        }

        search_resp = client.get(
            "/movies/external/search?q=movie"
        )
        assert search_resp.status_code == 200
        results = search_resp.json()
        assert len(results) == 2

        good = [m for m in results if m['rating'] > 8.0][0]

        import_resp = client.post(
            f"/movies/external/import/{good['external_id']}",
            headers={"Authorization": "Bearer mock_token"}
        )
        assert import_resp.status_code == 200
        assert import_resp.json()['title'] == "Good Movie"


class TestErrorHandling:

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    def test_handles_network_timeout(self, mock_service, client):
        import requests
        mock_service.search_movies.side_effect = (
            requests.exceptions.Timeout()
        )

        response = client.get("/movies/external/search?q=test")

        assert response.status_code == 503

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    def test_handles_invalid_external_id(
        self, mock_service, client
    ):
        mock_service.get_movie_by_id.return_value = None

        response = client.post(
            "/movies/external/import/invalid_id",
            headers={"Authorization": "Bearer mock_token"}
        )

        assert response.status_code == 404

    @patch(
        'keyboard_smashers.controllers.movie_controller.'
        'movie_controller_instance.external_service'
    )
    def test_handles_malformed_external_response(
        self, mock_service, client
    ):
        mock_service.search_movies.side_effect = KeyError(
            "Unexpected response"
        )

        response = client.get("/movies/external/search?q=test")

        assert response.status_code == 503
