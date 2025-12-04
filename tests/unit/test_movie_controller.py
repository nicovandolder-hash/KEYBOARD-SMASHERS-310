import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from keyboard_smashers.controllers.movie_controller import (
    MovieController,
    MovieCreateSchema,
    MovieUpdateSchema
)


@pytest.fixture
def mock_dao():
    """Create a mock MovieDAO"""
    mock = Mock()
    mock.movies = {}  # Add movies attribute for __init__ logging
    return mock


@pytest.fixture
def controller(mock_dao):
    """Create a MovieController instance with mocked DAO"""
    with patch('keyboard_smashers.controllers.movie_controller.MovieDAO',
               return_value=mock_dao):
        controller = MovieController()
        controller.movie_dao = mock_dao  # Ensure the mock is set
        return controller


@pytest.fixture
def sample_movie_dict():
    """Sample movie dictionary as returned by DAO"""
    return {
        'movie_id': '1',
        'title': 'Inception',
        'genre': 'Sci-Fi',
        'director': 'Christopher Nolan',
        'year': 2010,
        'description': 'A thief who steals secrets'
    }


@pytest.fixture
def sample_movies_list():
    """Sample list of movie dictionaries"""
    return [
        {
            'movie_id': '1',
            'title': 'Inception',
            'genre': 'Sci-Fi',
            'director': 'Christopher Nolan',
            'year': 2010,
            'description': 'A thief who steals secrets'
        },
        {
            'movie_id': '2',
            'title': 'The Matrix',
            'genre': 'Action',
            'director': 'Wachowskis',
            'year': 1999,
            'description': 'A computer hacker learns the truth'
        },
        {
            'movie_id': '3',
            'title': 'Interstellar',
            'genre': 'Sci-Fi',
            'director': 'Christopher Nolan',
            'year': 2014,
            'description': 'Explorers travel through a wormhole'
        }
    ]


class TestGetAllMovies:
    def test_get_all_movies_empty(self, controller, mock_dao):
        """Test getting all movies when DAO returns empty list."""
        mock_dao.get_all_movies.return_value = []

        response = controller.get_all_movies()

        assert response.movies == []
        assert response.total == 0
        assert response.page == 1
        assert response.page_size == 20
        mock_dao.get_all_movies.assert_called_once()

    def test_get_all_movies_with_data(self, controller, mock_dao,
                                      sample_movies_list):
        """Test getting all movies when DAO returns data."""
        mock_dao.get_all_movies.return_value = sample_movies_list

        response = controller.get_all_movies()

        assert len(response.movies) == 3
        assert response.total == 3
        assert all(hasattr(m, 'title') for m in response.movies)
        assert response.movies[0].title == 'Inception'
        mock_dao.get_all_movies.assert_called_once()


class TestGetMovieById:
    def test_get_existing_movie(self, controller, mock_dao,
                                sample_movie_dict):
        """Test getting an existing movie by ID."""
        mock_dao.get_movie.return_value = sample_movie_dict

        movie = controller.get_movie_by_id('1')

        assert movie.movie_id == '1'
        assert movie.title == 'Inception'
        assert movie.director == 'Christopher Nolan'
        mock_dao.get_movie.assert_called_once_with('1')

    def test_get_nonexistent_movie(self, controller, mock_dao):
        """Test getting a nonexistent movie raises HTTPException."""
        mock_dao.get_movie.side_effect = KeyError("Movie with id 999 "
                                                  "not found")

        with pytest.raises(HTTPException) as exc_info:
            controller.get_movie_by_id('999')

        assert exc_info.value.status_code == 404
        assert 'not found' in exc_info.value.detail.lower()
        mock_dao.get_movie.assert_called_once_with('999')


class TestCreateMovie:
    def test_create_movie_success(self, controller, mock_dao):
        """Test successfully creating a movie."""
        mock_dao.get_all_movies.return_value = []
        mock_dao.create_movie.return_value = {
            'movie_id': '1',
            'title': 'Test Movie',
            'genre': 'Drama',
            'director': 'Test Director',
            'year': 2023,
            'description': 'A test movie'
        }

        movie_data = MovieCreateSchema(
            title="Test Movie",
            genre="Drama",
            year=2023,
            director="Test Director",
            description="A test movie"
        )

        created = controller.create_movie(movie_data)

        assert created.title == "Test Movie"
        assert created.genre == "Drama"
        assert created.movie_id is not None
        mock_dao.create_movie.assert_called_once()

    def test_create_movie_minimal_fields(self, controller, mock_dao):
        """Test creating a movie with minimal fields."""
        mock_dao.get_all_movies.return_value = []
        mock_dao.create_movie.return_value = {
            'movie_id': '1',
            'title': 'Minimal Movie',
            'genre': '',
            'director': '',
            'year': 0,
            'description': ''
        }

        movie_data = MovieCreateSchema(title="Minimal Movie")
        created = controller.create_movie(movie_data)

        assert created.title == "Minimal Movie"
        assert created.genre == ""
        assert created.year == 0
        mock_dao.create_movie.assert_called_once()

    def test_create_duplicate_title(self, controller, mock_dao,
                                    sample_movies_list):
        """Test creating a movie with duplicate title raises error."""
        mock_dao.get_all_movies.return_value = sample_movies_list

        movie_data = MovieCreateSchema(title="Inception")

        with pytest.raises(HTTPException) as exc_info:
            controller.create_movie(movie_data)

        assert exc_info.value.status_code == 400
        assert 'already exists' in exc_info.value.detail.lower()
        mock_dao.create_movie.assert_not_called()

    def test_create_duplicate_title_case_insensitive(self, controller,
                                                     mock_dao,
                                                     sample_movies_list):
        """Test duplicate detection is case-insensitive."""
        mock_dao.get_all_movies.return_value = sample_movies_list

        movie_data = MovieCreateSchema(title="INCEPTION")

        with pytest.raises(HTTPException) as exc_info:
            controller.create_movie(movie_data)

        assert exc_info.value.status_code == 400
        mock_dao.create_movie.assert_not_called()


class TestUpdateMovie:
    def test_update_movie_title(self, controller, mock_dao,
                                sample_movie_dict):
        """Test updating a movie's title."""
        mock_dao.get_movie.return_value = sample_movie_dict
        mock_dao.get_all_movies.return_value = [sample_movie_dict]
        updated_dict = sample_movie_dict.copy()
        updated_dict['title'] = 'Inception 2'
        mock_dao.update_movie.return_value = updated_dict

        update_data = MovieUpdateSchema(title="Inception 2")
        updated = controller.update_movie('1', update_data)

        assert updated.title == "Inception 2"
        assert updated.movie_id == '1'
        mock_dao.update_movie.assert_called_once()

    def test_update_multiple_fields(self, controller, mock_dao,
                                    sample_movie_dict):
        """Test updating multiple fields."""
        mock_dao.get_movie.return_value = sample_movie_dict
        mock_dao.get_all_movies.return_value = [sample_movie_dict]
        updated_dict = sample_movie_dict.copy()
        updated_dict.update({
            'title': 'Updated Title',
            'director': 'New Director',
            'year': 2024
        })
        mock_dao.update_movie.return_value = updated_dict

        update_data = MovieUpdateSchema(
            title="Updated Title",
            director="New Director",
            year=2024
        )
        updated = controller.update_movie('1', update_data)

        assert updated.title == "Updated Title"
        assert updated.director == "New Director"
        assert updated.year == 2024
        mock_dao.update_movie.assert_called_once()

    def test_update_single_field_preserves_others(self, controller, mock_dao,
                                                  sample_movie_dict):
        """Test updating single field preserves other fields."""
        mock_dao.get_movie.return_value = sample_movie_dict
        mock_dao.get_all_movies.return_value = [sample_movie_dict]
        updated_dict = sample_movie_dict.copy()
        updated_dict['director'] = 'New Director'
        mock_dao.update_movie.return_value = updated_dict

        update_data = MovieUpdateSchema(director="New Director")
        updated = controller.update_movie('1', update_data)

        assert updated.title == sample_movie_dict['title']
        assert updated.director == "New Director"
        mock_dao.update_movie.assert_called_once()

    def test_update_nonexistent_movie(self, controller, mock_dao):
        """Test updating nonexistent movie raises error."""
        mock_dao.get_movie.side_effect = KeyError("Movie with id 999 "
                                                  "not found")

        update_data = MovieUpdateSchema(title="Updated")

        with pytest.raises(HTTPException) as exc_info:
            controller.update_movie('999', update_data)

        assert exc_info.value.status_code == 404
        mock_dao.update_movie.assert_not_called()

    def test_update_with_duplicate_title(self, controller, mock_dao,
                                         sample_movies_list):
        """Test updating with duplicate title raises error."""
        mock_dao.get_movie.return_value = sample_movies_list[0]
        mock_dao.get_all_movies.return_value = sample_movies_list

        update_data = MovieUpdateSchema(title="The Matrix")

        with pytest.raises(HTTPException) as exc_info:
            controller.update_movie('1', update_data)

        assert exc_info.value.status_code == 400
        assert 'already exists' in exc_info.value.detail.lower()
        mock_dao.update_movie.assert_not_called()

    def test_update_with_no_fields(self, controller, mock_dao,
                                   sample_movie_dict):
        """Test updating with no fields raises error."""
        mock_dao.get_movie.return_value = sample_movie_dict

        update_data = MovieUpdateSchema()

        with pytest.raises(HTTPException) as exc_info:
            controller.update_movie('1', update_data)

        assert exc_info.value.status_code == 400
        assert 'no fields' in exc_info.value.detail.lower()
        mock_dao.update_movie.assert_not_called()


class TestDeleteMovie:
    def test_delete_existing_movie(self, controller, mock_dao,
                                   sample_movie_dict):
        """Test deleting an existing movie."""
        mock_dao.get_movie.return_value = sample_movie_dict
        mock_dao.delete_movie.return_value = None

        # Use ID > 10 to avoid protected legacy IMDB movies
        result = controller.delete_movie('11')

        assert 'deleted successfully' in result['message'].lower()
        mock_dao.delete_movie.assert_called_once_with('11')

    def test_delete_nonexistent_movie(self, controller, mock_dao):
        """Test deleting nonexistent movie raises error."""
        mock_dao.delete_movie.side_effect = KeyError("Movie with id 999 "
                                                     "not found")

        with pytest.raises(HTTPException) as exc_info:
            controller.delete_movie('999')

        assert exc_info.value.status_code == 404
        mock_dao.delete_movie.assert_called_once_with('999')


class TestSearchMoviesByTitle:
    def test_search_exact_match(self, controller, mock_dao,
                                sample_movies_list):
        """Test searching with exact title match."""
        mock_dao.get_all_movies.return_value = [sample_movies_list[0]]

        results = controller.search_movies_by_title("Inception")

        assert len(results) == 1
        assert results[0].title == "Inception"
        mock_dao.get_all_movies.assert_called_once()

    def test_search_partial_match(self, controller, mock_dao):
        """Test searching with partial title match."""
        mock_dao.get_all_movies.return_value = [{
            'movie_id': '3',
            'title': 'Interstellar',
            'genre': 'Sci-Fi',
            'director': 'Christopher Nolan',
            'year': 2014,
            'description': 'Explorers travel through a wormhole'
        }]

        results = controller.search_movies_by_title("Inter")

        assert len(results) == 1
        assert results[0].title == "Interstellar"

    def test_search_case_insensitive(self, controller, mock_dao,
                                     sample_movie_dict):
        """Test search is case-insensitive."""
        mock_dao.get_all_movies.return_value = [sample_movie_dict]

        results = controller.search_movies_by_title("inception")

        assert len(results) == 1
        assert results[0].title == "Inception"

    def test_search_multiple_matches(self, controller, mock_dao):
        """Test searching returns multiple matches."""
        mock_dao.get_all_movies.return_value = [
            {
                'movie_id': '1',
                'title': 'Inception',
                'genre': 'Sci-Fi',
                'director': 'Christopher Nolan',
                'year': 2010,
                'description': 'A thief'
            },
            {
                'movie_id': '4',
                'title': 'Inception 2',
                'genre': 'Sci-Fi',
                'director': 'Christopher Nolan',
                'year': 2024,
                'description': 'A sequel'
            }
        ]

        results = controller.search_movies_by_title("Inception")

        assert len(results) == 2

    def test_search_no_matches(self, controller, mock_dao):
        """Test searching with no matches returns empty list."""
        mock_dao.get_all_movies.return_value = []

        results = controller.search_movies_by_title("Nonexistent")

        assert len(results) == 0


class TestGetMoviesByGenre:
    def test_get_by_genre_exact_match(self, controller, mock_dao):
        """Test getting movies by exact genre match."""
        mock_dao.get_all_movies.return_value = [
            {
                'movie_id': '1',
                'title': 'Inception',
                'genre': 'Sci-Fi',
                'director': 'Christopher Nolan',
                'year': 2010,
                'description': 'A thief'
            },
            {
                'movie_id': '3',
                'title': 'Interstellar',
                'genre': 'Sci-Fi',
                'director': 'Christopher Nolan',
                'year': 2014,
                'description': 'Explorers'
            }
        ]

        results = controller.get_movies_by_genre("Sci-Fi")

        assert len(results) == 2
        assert all(m.genre == "Sci-Fi" for m in results)

    def test_get_by_genre_case_insensitive(self, controller, mock_dao):
        """Test genre search is case-insensitive."""
        mock_dao.get_all_movies.return_value = [
            {
                'movie_id': '1',
                'title': 'Inception',
                'genre': 'Sci-Fi',
                'director': 'Christopher Nolan',
                'year': 2010,
                'description': 'A thief'
            }
        ]

        results = controller.get_movies_by_genre("sci-fi")

        assert len(results) == 1

    def test_get_by_genre_no_matches(self, controller, mock_dao):
        """Test getting movies by genre with no matches."""
        mock_dao.get_all_movies.return_value = []

        results = controller.get_movies_by_genre("Horror")

        assert len(results) == 0

    def test_get_by_genre_single_match(self, controller, mock_dao):
        """Test getting movies by genre with single match."""
        mock_dao.get_all_movies.return_value = [{
            'movie_id': '2',
            'title': 'The Matrix',
            'genre': 'Action',
            'director': 'Wachowskis',
            'year': 1999,
            'description': 'A computer hacker'
        }]

        results = controller.get_movies_by_genre("Action")

        assert len(results) == 1
        assert results[0].title == "The Matrix"


class TestSearchMovies:
    def test_search_by_title(self, controller, mock_dao, sample_movie_dict):
        """Test searching movies by title."""
        mock_dao.get_all_movies.return_value = [sample_movie_dict]

        results = controller.search_movies("Inception")

        assert len(results) == 1
        assert results[0].title == "Inception"

    def test_search_by_director(self, controller, mock_dao,
                                sample_movies_list):
        """Test searching movies by director."""
        nolan_movies = [m for m in sample_movies_list
                        if "Nolan" in m['director']]
        mock_dao.get_all_movies.return_value = nolan_movies

        results = controller.search_movies("Nolan")

        assert len(results) == 2
        assert all("Nolan" in m.director for m in results)

    def test_search_by_description(self, controller, mock_dao):
        """Test searching movies by description."""
        mock_dao.get_all_movies.return_value = [{
            'movie_id': '3',
            'title': 'Interstellar',
            'genre': 'Sci-Fi',
            'director': 'Christopher Nolan',
            'year': 2014,
            'description': 'Explorers travel through a wormhole'
        }]

        results = controller.search_movies("wormhole")

        assert len(results) == 1
        assert results[0].title == "Interstellar"

    def test_search_case_insensitive(self, controller, mock_dao,
                                     sample_movies_list):
        """Test search is case-insensitive."""
        nolan_movies = [m for m in sample_movies_list
                        if "Nolan" in m['director']]
        mock_dao.get_all_movies.return_value = nolan_movies

        results = controller.search_movies("NOLAN")

        assert len(results) == 2

    def test_search_no_matches(self, controller, mock_dao):
        """Test searching with no matches returns empty list."""
        mock_dao.get_all_movies.return_value = []

        results = controller.search_movies("Nonexistent Query")

        assert len(results) == 0


class TestSchemaValidation:
    def test_create_schema_requires_title(self):
        """Test MovieCreateSchema requires title field."""
        with pytest.raises(Exception):
            MovieCreateSchema()

    def test_create_schema_validates_title_length(self):
        """Test MovieCreateSchema validates title is not empty."""
        with pytest.raises(Exception):
            MovieCreateSchema(title="")

    def test_update_schema_all_optional(self):
        """Test MovieUpdateSchema has all optional fields."""
        schema = MovieUpdateSchema()
        assert schema.title is None
        assert schema.genre is None
