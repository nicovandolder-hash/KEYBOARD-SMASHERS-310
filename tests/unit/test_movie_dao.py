import pytest
import pandas as pd
import tempfile
import os
from keyboard_smashers.dao.movie_dao import MovieDAO


@pytest.fixture
def temp_csv():
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "test_movies.csv")

    # Create initial test data
    test_data = pd.DataFrame([
        {
            'movie_id': '1', 'title': 'Inception', 'genre': 'Sci-Fi',
            'director': 'Christopher Nolan', 'year': 2010,
            'description': 'A thief who steals secrets'
        },
        {
            'movie_id': '2', 'title': 'The Matrix', 'genre': 'Action',
            'director': 'Wachowskis', 'year': 1999,
            'description': 'A computer hacker learns the truth'
        },
        {
            'movie_id': '3', 'title': 'Interstellar', 'genre': 'Sci-Fi',
            'director': 'Christopher Nolan', 'year': 2014,
            'description': 'Explorers travel through a wormhole'
        }
    ])
    test_data.to_csv(csv_path, index=False)
    yield csv_path

    if os.path.exists(csv_path):
        os.remove(csv_path)
    os.rmdir(temp_dir)


@pytest.fixture
def movie_dao(temp_csv):
    return MovieDAO(csv_path=temp_csv)


class TestMovieDAOInitialization:

    def test_load_movies_from_csv(self, movie_dao):
        assert len(movie_dao.movies) == 3
        assert '1' in movie_dao.movies
        assert '2' in movie_dao.movies
        assert '3' in movie_dao.movies

    def test_loaded_movie_properties(self, movie_dao):
        movie = movie_dao.movies['1']
        assert isinstance(movie, dict)
        assert movie['movie_id'] == '1'
        assert movie['title'] == 'Inception'
        assert movie['director'] == 'Christopher Nolan'
        assert movie['year'] == 2010
        assert movie['genre'] == 'Sci-Fi'

    def test_load_from_nonexistent_file(self):
        dao = MovieDAO(csv_path="nonexistent.csv")
        assert len(dao.movies) == 0


class TestGetMovie:
    def test_get_existing_movie(self, movie_dao):
        movie = movie_dao.get_movie('1')
        assert isinstance(movie, dict)
        assert movie['title'] == 'Inception'
        assert movie['director'] == 'Christopher Nolan'

    def test_get_nonexistent_movie(self, movie_dao):
        with pytest.raises(KeyError, match="Movie with id 999 not found"):
            movie_dao.get_movie('999')

    def test_get_movie_with_int_id(self, movie_dao):
        movie = movie_dao.get_movie('2')
        assert movie['title'] == 'The Matrix'

    def test_get_movie_returns_copy(self, movie_dao):
        """Test that get_movie returns a copy, not the original"""
        movie = movie_dao.get_movie('1')
        movie['title'] = 'Modified Title'

        # Original should be unchanged
        assert movie_dao.movies['1']['title'] == 'Inception'


class TestGetAllMovies:
    def test_get_all_movies_returns_list(self, movie_dao):
        movies = movie_dao.get_all_movies()
        assert isinstance(movies, list)
        assert len(movies) == 3

    def test_all_movies_are_dicts(self, movie_dao):
        movies = movie_dao.get_all_movies()
        for movie in movies:
            assert isinstance(movie, dict)
            assert 'movie_id' in movie
            assert 'title' in movie

    def test_get_all_movies_empty_dao(self):
        dao = MovieDAO(csv_path="nonexistent.csv")
        movies = dao.get_all_movies()
        assert movies == []

    def test_get_all_movies_returns_copies(self, movie_dao):
        """Test that get_all_movies returns copies, not originals"""
        movies = movie_dao.get_all_movies()
        movies[0]['title'] = 'Modified'

        # Original should be unchanged
        assert movie_dao.movies['1']['title'] == 'Inception'


class TestCreateMovie:
    def test_create_new_movie_auto_id(self, movie_dao, temp_csv):
        """Test creating a movie with auto-generated ID"""
        new_movie_data = {
            'title': 'The Dark Knight',
            'genre': 'Action',
            'director': 'Christopher Nolan',
            'year': 2008,
            'description': 'Batman faces the Joker'
        }
        created_movie = movie_dao.create_movie(new_movie_data)

        # Should auto-generate ID '4'
        assert created_movie['movie_id'] == '4'
        assert '4' in movie_dao.movies
        assert movie_dao.movies['4']['title'] == 'The Dark Knight'

        # Check CSV persistence
        df = pd.read_csv(temp_csv)
        assert len(df) == 4
        assert '4' in df['movie_id'].astype(str).values

    def test_create_movie_with_missing_optional_fields(self, movie_dao):
        new_movie_data = {
            'title': 'Minimal Movie'
        }

        created_movie = movie_dao.create_movie(new_movie_data)
        assert created_movie['title'] == 'Minimal Movie'
        assert created_movie['director'] == ''
        assert created_movie['genre'] == ''
        assert created_movie['description'] == ''
        assert created_movie['year'] == 0

    def test_create_movie_returns_dict(self, movie_dao):
        new_movie_data = {'title': 'Test Movie'}
        result = movie_dao.create_movie(new_movie_data)
        assert isinstance(result, dict)
        assert 'movie_id' in result


class TestUpdateMovie:

    def test_update_movie_title(self, movie_dao, temp_csv):
        updated_movie = movie_dao.update_movie('1', {'title': 'Inception 2'})

        assert updated_movie['title'] == 'Inception 2'
        assert movie_dao.movies['1']['title'] == 'Inception 2'

        # Check CSV persistence
        df = pd.read_csv(temp_csv)
        row = df[df['movie_id'].astype(str) == '1'].iloc[0]
        assert row['title'] == 'Inception 2'

    def test_update_multiple_fields(self, movie_dao):
        update_data = {
            'title': 'New Title',
            'director': 'New Director',
            'year': 2020,
            'genre': 'Drama'
        }

        updated_movie = movie_dao.update_movie('2', update_data)

        assert updated_movie['title'] == 'New Title'
        assert updated_movie['director'] == 'New Director'
        assert updated_movie['year'] == 2020
        assert updated_movie['genre'] == 'Drama'

        # Check internal state
        movie = movie_dao.movies['2']
        assert movie['title'] == 'New Title'
        assert movie['director'] == 'New Director'
        assert movie['year'] == 2020
        assert movie['genre'] == 'Drama'

    def test_update_single_field(self, movie_dao):
        original_title = movie_dao.movies['3']['title']

        updated_movie = movie_dao.update_movie(
            '3', {'director': 'Updated Director'}
        )

        assert updated_movie['title'] == original_title
        assert updated_movie['director'] == 'Updated Director'

    def test_update_nonexistent_movie(self, movie_dao):
        with pytest.raises(KeyError, match="Movie with id 999 not found"):
            movie_dao.update_movie('999', {'title': 'Test'})

    def test_update_returns_dict(self, movie_dao):
        result = movie_dao.update_movie('1', {'title': 'Updated'})
        assert isinstance(result, dict)


class TestDeleteMovie:
    def test_delete_existing_movie(self, movie_dao, temp_csv):
        assert '2' in movie_dao.movies

        movie_dao.delete_movie('2')

        assert '2' not in movie_dao.movies
        assert len(movie_dao.movies) == 2

        # Check CSV persistence
        df = pd.read_csv(temp_csv)
        assert len(df) == 2
        assert '2' not in df['movie_id'].astype(str).values

    def test_delete_nonexistent_movie(self, movie_dao):
        with pytest.raises(KeyError, match="Movie with id 999 not found"):
            movie_dao.delete_movie('999')

    def test_delete_all_movies(self, movie_dao, temp_csv):
        movie_dao.delete_movie('1')
        movie_dao.delete_movie('2')
        movie_dao.delete_movie('3')

        assert len(movie_dao.movies) == 0

        # Check CSV has correct structure even when empty
        df = pd.read_csv(temp_csv)
        assert len(df) == 0
        assert list(df.columns) == [
            'movie_id', 'title', 'genre', 'year', 'director',
            'description'
        ]

    def test_delete_returns_none(self, movie_dao):
        result = movie_dao.delete_movie('1')
        assert result is None


class TestPersistence:

    def test_changes_persist_across_instances(self, temp_csv):
        """Test that creating a movie persists to CSV"""
        dao1 = MovieDAO(csv_path=temp_csv)
        dao1.create_movie({
            'title': 'Persisted Movie',
            'genre': 'Test',
            'director': 'Test Director',
            'year': 2023,
            'description': 'A test movie'
        })

        # Create new instance - should reload from CSV
        dao2 = MovieDAO(csv_path=temp_csv)
        assert '4' in dao2.movies
        assert dao2.movies['4']['title'] == 'Persisted Movie'

    def test_update_persists(self, temp_csv):
        """Test that updates persist to CSV"""
        dao1 = MovieDAO(csv_path=temp_csv)
        dao1.update_movie('1', {'title': 'Updated Title'})

        # Create new instance - should reload from CSV
        dao2 = MovieDAO(csv_path=temp_csv)
        assert dao2.movies['1']['title'] == 'Updated Title'

    def test_delete_persists(self, temp_csv):
        """Test that deletions persist to CSV"""
        dao1 = MovieDAO(csv_path=temp_csv)
        dao1.delete_movie('1')

        # Create new instance - should reload from CSV
        dao2 = MovieDAO(csv_path=temp_csv)
        assert '1' not in dao2.movies
        assert len(dao2.movies) == 2


class TestEdgeCases:

    def test_movie_id_string_conversion(self, movie_dao):
        """Test that integer IDs are converted to strings"""
        movie = movie_dao.get_movie(1)  # Pass int
        assert movie['movie_id'] == '1'

    def test_empty_string_fields(self, movie_dao):
        """Test handling of empty string fields"""
        new_movie = movie_dao.create_movie({
            'title': 'Empty Fields Movie',
            'genre': '',
            'director': '',
            'description': ''
        })
        assert new_movie['genre'] == ''
        assert new_movie['director'] == ''
        assert new_movie['description'] == ''

    def test_year_zero_handling(self, movie_dao):
        """Test that year=0 is handled correctly"""
        new_movie = movie_dao.create_movie({
            'title': 'No Year Movie',
            'year': 0
        })
        assert new_movie['year'] == 0
