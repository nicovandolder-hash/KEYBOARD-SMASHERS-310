import pandas as pd
from pathlib import Path
from typing import List, Dict, Any


class MovieDAO:
    """
    Data Access Object for Movie persistence.
    Handles all CSV read/write operations and works exclusively with
    dictionaries. No business logic - just pure data access.
    """

    def __init__(self, csv_path: str = "data/movies.csv"):
        """
        Initialize MovieDAO with path to CSV file.

        Args:
            csv_path: Path to the movies CSV file
        """
        self.csv_path = csv_path
        self.movies: Dict[str, Dict[str, Any]] = {}
        self._load_movies()

    def _load_movies(self) -> None:
        """Load movies from CSV file into memory as dictionaries."""
        if not Path(self.csv_path).exists():
            return

        df = pd.read_csv(self.csv_path)
        for _, row in df.iterrows():
            movie_dict = {
                'movie_id': str(row['movie_id']),
                'title': row['title'],
                'genre': row.get('genre', ''),
                'year': int(row['year']) if pd.notna(row.get('year')) else 0,
                'director': row.get('director', ''),
                'description': row.get('description', '')
            }
            self.movies[movie_dict['movie_id']] = movie_dict

    def _save_movies(self) -> None:
        """Save all movies from memory to CSV file."""
        if not self.movies:
            df = pd.DataFrame(
                columns=[
                    'movie_id', 'title', 'genre', 'year',
                    'director', 'description'
                ]
            )
        else:
            movies_data = list(self.movies.values())
            df = pd.DataFrame(movies_data)

        Path(self.csv_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.csv_path, index=False)

    def create_movie(self, movie_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new movie entry.

        Args:
            movie_data: Dictionary containing movie information
                       (title, director, year, genre, description)

        Returns:
            Dictionary representing the created movie with generated movie_id

        Raises:
            ValueError: If movie_id already exists
        """
        # Auto-generate movie_id
        existing_ids = [int(mid)
                        for mid in self.movies.keys() if mid.isdigit()]
        movie_id = str(max(existing_ids) + 1) if existing_ids else "1"

        if movie_id in self.movies:
            raise ValueError(f"Movie with id {movie_id} already exists")

        movie_dict = {
            'movie_id': movie_id,
            'title': movie_data['title'],
            'genre': movie_data.get('genre', ''),
            'year': movie_data.get('year', 0),
            'director': movie_data.get('director', ''),
            'description': movie_data.get('description', '')
        }

        self.movies[movie_id] = movie_dict
        self._save_movies()
        return movie_dict.copy()

    def get_movie(self, movie_id: str) -> Dict[str, Any]:
        """
        Retrieve a single movie by ID.

        Args:
            movie_id: The ID of the movie to retrieve

        Returns:
            Dictionary representing the movie

        Raises:
            KeyError: If movie with given ID does not exist
        """
        movie_id = str(movie_id)
        if movie_id not in self.movies:
            raise KeyError(f"Movie with id {movie_id} not found")
        return self.movies[movie_id].copy()

    def get_all_movies(self) -> List[Dict[str, Any]]:
        """
        Retrieve all movies.

        Returns:
            List of dictionaries, each representing a movie
        """
        return [movie.copy() for movie in self.movies.values()]

    def update_movie(
        self, movie_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing movie.

        Args:
            movie_id: The ID of the movie to update
            data: Dictionary containing fields to update
                  (title, director, year, genre, description)

        Returns:
            Dictionary representing the updated movie

        Raises:
            KeyError: If movie with given ID does not exist
        """
        movie_id = str(movie_id)
        if movie_id not in self.movies:
            raise KeyError(f"Movie with id {movie_id} not found")

        movie = self.movies[movie_id]

        # Update only provided fields
        if 'title' in data:
            movie['title'] = data['title']
        if 'genre' in data:
            movie['genre'] = data['genre']
        if 'director' in data:
            movie['director'] = data['director']
        if 'year' in data:
            movie['year'] = data['year']
        if 'description' in data:
            movie['description'] = data['description']

        self._save_movies()
        return movie.copy()

    def delete_movie(self, movie_id: str) -> None:
        """
        Delete a movie.

        Args:
            movie_id: The ID of the movie to delete

        Raises:
            KeyError: If movie with given ID does not exist
        """
        movie_id = str(movie_id)
        if movie_id not in self.movies:
            raise KeyError(f"Movie with id {movie_id} not found")

        del self.movies[movie_id]
        self._save_movies()
