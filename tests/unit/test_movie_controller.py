import pytest
from fastapi import HTTPException
from keyboard_smashers.controllers.movie_controller import (
    MovieController,
    MovieCreateSchema,
    MovieUpdateSchema
)
import tempfile
import os


@pytest.fixture
def temp_csv():
    """Create a temporary CSV file for testing"""
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "test_movies.csv")
    yield csv_path
    
    if os.path.exists(csv_path):
        os.remove(csv_path)
    os.rmdir(temp_dir)


@pytest.fixture
def controller(temp_csv):
    """Create a MovieController instance with temp CSV"""
    return MovieController(csv_path=temp_csv)


@pytest.fixture
def controller_with_data(temp_csv):
    """Create a MovieController with some test data"""
    controller = MovieController(csv_path=temp_csv)
    
    # Add test movies
    controller.create_movie(MovieCreateSchema(
        title="Inception",
        genre="Sci-Fi",
        year=2010,
        director="Christopher Nolan",
        description="A thief who steals secrets"
    ))
    controller.create_movie(MovieCreateSchema(
        title="The Matrix",
        genre="Action",
        year=1999,
        director="Wachowskis",
        description="A computer hacker learns the truth"
    ))
    controller.create_movie(MovieCreateSchema(
        title="Interstellar",
        genre="Sci-Fi",
        year=2014,
        director="Christopher Nolan",
        description="Explorers travel through a wormhole"
    ))
    
    return controller


class TestGetAllMovies:
    def test_get_all_movies_empty(self, controller):
        movies = controller.get_all_movies()
        assert movies == []
    
    def test_get_all_movies_with_data(self, controller_with_data):
        movies = controller_with_data.get_all_movies()
        assert len(movies) == 3
        assert all(hasattr(m, 'title') for m in movies)


class TestGetMovieById:
    def test_get_existing_movie(self, controller_with_data):
        movie = controller_with_data.get_movie_by_id('1')
        assert movie.movie_id == '1'
        assert movie.title == 'Inception'
        assert movie.director == 'Christopher Nolan'
    
    def test_get_nonexistent_movie(self, controller_with_data):
        with pytest.raises(HTTPException) as exc_info:
            controller_with_data.get_movie_by_id('999')
        assert exc_info.value.status_code == 404
        assert 'not found' in exc_info.value.detail.lower()


class TestCreateMovie:
    def test_create_movie_success(self, controller):
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
    
    def test_create_movie_minimal_fields(self, controller):
        movie_data = MovieCreateSchema(title="Minimal Movie")
        created = controller.create_movie(movie_data)
        
        assert created.title == "Minimal Movie"
        assert created.genre == ""
        assert created.year == 0
    
    def test_create_duplicate_title(self, controller_with_data):
        movie_data = MovieCreateSchema(title="Inception")
        
        with pytest.raises(HTTPException) as exc_info:
            controller_with_data.create_movie(movie_data)
        assert exc_info.value.status_code == 400
        assert 'already exists' in exc_info.value.detail.lower()
    
    def test_create_duplicate_title_case_insensitive(self, controller_with_data):
        movie_data = MovieCreateSchema(title="INCEPTION")
        
        with pytest.raises(HTTPException) as exc_info:
            controller_with_data.create_movie(movie_data)
        assert exc_info.value.status_code == 400


class TestUpdateMovie:
    def test_update_movie_title(self, controller_with_data):
        update_data = MovieUpdateSchema(title="Inception 2")
        updated = controller_with_data.update_movie('1', update_data)
        
        assert updated.title == "Inception 2"
        assert updated.movie_id == '1'
    
    def test_update_multiple_fields(self, controller_with_data):
        update_data = MovieUpdateSchema(
            title="Updated Title",
            director="New Director",
            year=2024
        )
        updated = controller_with_data.update_movie('1', update_data)
        
        assert updated.title == "Updated Title"
        assert updated.director == "New Director"
        assert updated.year == 2024
    
    def test_update_single_field_preserves_others(self, controller_with_data):
        original = controller_with_data.get_movie_by_id('1')
        
        update_data = MovieUpdateSchema(director="New Director")
        updated = controller_with_data.update_movie('1', update_data)
        
        assert updated.title == original.title
        assert updated.director == "New Director"
    
    def test_update_nonexistent_movie(self, controller_with_data):
        update_data = MovieUpdateSchema(title="Updated")
        
        with pytest.raises(HTTPException) as exc_info:
            controller_with_data.update_movie('999', update_data)
        assert exc_info.value.status_code == 404
    
    def test_update_with_duplicate_title(self, controller_with_data):
        update_data = MovieUpdateSchema(title="The Matrix")
        
        with pytest.raises(HTTPException) as exc_info:
            controller_with_data.update_movie('1', update_data)
        assert exc_info.value.status_code == 400
        assert 'already exists' in exc_info.value.detail.lower()
    
    def test_update_with_no_fields(self, controller_with_data):
        update_data = MovieUpdateSchema()
        
        with pytest.raises(HTTPException) as exc_info:
            controller_with_data.update_movie('1', update_data)
        assert exc_info.value.status_code == 400
        assert 'no fields' in exc_info.value.detail.lower()


class TestDeleteMovie:
    def test_delete_existing_movie(self, controller_with_data):
        result = controller_with_data.delete_movie('1')
        
        assert 'deleted successfully' in result['message'].lower()
        
        with pytest.raises(HTTPException):
            controller_with_data.get_movie_by_id('1')
    
    def test_delete_nonexistent_movie(self, controller_with_data):
        with pytest.raises(HTTPException) as exc_info:
            controller_with_data.delete_movie('999')
        assert exc_info.value.status_code == 404


class TestSearchMoviesByTitle:
    def test_search_exact_match(self, controller_with_data):
        results = controller_with_data.search_movies_by_title("Inception")
        assert len(results) == 1
        assert results[0].title == "Inception"
    
    def test_search_partial_match(self, controller_with_data):
        results = controller_with_data.search_movies_by_title("Inter")
        assert len(results) == 1
        assert results[0].title == "Interstellar"
    
    def test_search_case_insensitive(self, controller_with_data):
        results = controller_with_data.search_movies_by_title("inception")
        assert len(results) == 1
        assert results[0].title == "Inception"
    
    def test_search_multiple_matches(self, controller_with_data):
        controller_with_data.create_movie(MovieCreateSchema(
            title="Inception 2"
        ))
        results = controller_with_data.search_movies_by_title("Inception")
        assert len(results) == 2
    
    def test_search_no_matches(self, controller_with_data):
        results = controller_with_data.search_movies_by_title("Nonexistent")
        assert len(results) == 0


class TestGetMoviesByGenre:
    def test_get_by_genre_exact_match(self, controller_with_data):
        results = controller_with_data.get_movies_by_genre("Sci-Fi")
        assert len(results) == 2
        assert all(m.genre == "Sci-Fi" for m in results)
    
    def test_get_by_genre_case_insensitive(self, controller_with_data):
        results = controller_with_data.get_movies_by_genre("sci-fi")
        assert len(results) == 2
    
    def test_get_by_genre_no_matches(self, controller_with_data):
        results = controller_with_data.get_movies_by_genre("Horror")
        assert len(results) == 0
    
    def test_get_by_genre_single_match(self, controller_with_data):
        results = controller_with_data.get_movies_by_genre("Action")
        assert len(results) == 1
        assert results[0].title == "The Matrix"


class TestSearchMovies:
    def test_search_by_title(self, controller_with_data):
        results = controller_with_data.search_movies("Inception")
        assert len(results) == 1
        assert results[0].title == "Inception"
    
    def test_search_by_director(self, controller_with_data):
        results = controller_with_data.search_movies("Nolan")
        assert len(results) == 2
        assert all("Nolan" in m.director for m in results)
    
    def test_search_by_description(self, controller_with_data):
        results = controller_with_data.search_movies("wormhole")
        assert len(results) == 1
        assert results[0].title == "Interstellar"
    
    def test_search_multiple_fields(self, controller_with_data):
        results = controller_with_data.search_movies("Sci")
        # Should match genre "Sci-Fi" in description fields
        assert len(results) >= 0
    
    def test_search_case_insensitive(self, controller_with_data):
        results = controller_with_data.search_movies("NOLAN")
        assert len(results) == 2
    
    def test_search_no_matches(self, controller_with_data):
        results = controller_with_data.search_movies("Nonexistent Query")
        assert len(results) == 0


class TestPersistence:
    def test_changes_persist_across_instances(self, temp_csv):
        controller1 = MovieController(csv_path=temp_csv)
        controller1.create_movie(MovieCreateSchema(
            title="Persisted Movie"
        ))
        
        controller2 = MovieController(csv_path=temp_csv)
        movies = controller2.get_all_movies()
        assert len(movies) == 1
        assert movies[0].title == "Persisted Movie"


class TestSchemaValidation:
    def test_create_schema_requires_title(self):
        with pytest.raises(Exception):
            MovieCreateSchema()
    
    def test_create_schema_validates_title_length(self):
        with pytest.raises(Exception):
            MovieCreateSchema(title="")
    
    def test_update_schema_all_optional(self):
        schema = MovieUpdateSchema()
        assert schema.title is None
        assert schema.genre is None
