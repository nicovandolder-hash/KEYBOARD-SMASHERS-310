import requests
import logging
from typing import List, Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ExternalMovieResult(BaseModel):
    external_id: str
    title: str
    genre: str
    year: int
    director: str
    description: str
    poster_url: Optional[str] = None
    rating: Optional[float] = None


class ExternalMovieService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.genre_cache = None

    def _get_genre_mapping(self) -> Dict[int, str]:
        if self.genre_cache:
            return self.genre_cache

        try:
            url = f"{self.base_url}/genre/movie/list"
            params = {"api_key": self.api_key}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            genres = response.json().get("genres", [])
            self.genre_cache = {g["id"]: g["name"] for g in genres}
            return self.genre_cache
        except Exception as e:
            logger.error(f"Failed to fetch genres: {e}")
            return {}

    def _get_movie_credits(self, movie_id: int) -> str:
        try:
            url = f"{self.base_url}/movie/{movie_id}/credits"
            params = {"api_key": self.api_key}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            crew = response.json().get("crew", [])
            directors = [
                member["name"]
                for member in crew
                if member.get("job") == "Director"
            ]
            return directors[0] if directors else "Unknown"
        except Exception as e:
            logger.error(f"Failed to fetch credits for movie {movie_id}: {e}")
            return "Unknown"

    def search_movies(self, query: str, limit: int = 10) -> (
            List[ExternalMovieResult]):
        """
        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of ExternalMovieResult objects
        """
        try:
            url = f"{self.base_url}/search/movie"
            params = {
                "api_key": self.api_key,
                "query": query,
                "language": "en-US",
                "page": 1
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            results = response.json().get("results", [])[:limit]
            genre_map = self._get_genre_mapping()

            movies = []
            for movie in results:
                director = self._get_movie_credits(movie["id"])

                genre_ids = movie.get("genre_ids", [])
                genres = [genre_map.get(gid, "") for gid in genre_ids[:2]]
                genre_str = "/".join(filter(None, genres)) or "Unknown"

                release_date = movie.get("release_date", "")
                year = int(release_date[:4]) if release_date else 0

                poster_path = movie.get("poster_path")
                poster_url = (
                    f"https://image.tmdb.org/t/p/w500{poster_path}"
                    if poster_path else None
                )

                external_movie = ExternalMovieResult(
                    external_id=str(movie["id"]),
                    title=movie.get("title", "Unknown"),
                    genre=genre_str,
                    year=year,
                    director=director,
                    description=movie.get("overview", ""),
                    poster_url=poster_url,
                    rating=movie.get("vote_average")
                )
                movies.append(external_movie)

            logger.info(f"Found {len(movies)} movies for query: {query}")
            return movies

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise Exception(f"Failed to search external movie database:"
                            f" {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in search_movies: {e}")
            raise

    def get_movie_by_id(self, external_id: str) -> (
            Optional[ExternalMovieResult]):

        """
        Args:
            external_id: TMDB movie ID

        Returns:
            ExternalMovieResult object or None
        """
        try:
            url = f"{self.base_url}/movie/{external_id}"
            params = {
                "api_key": self.api_key,
                "language": "en-US"
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            movie = response.json()

            director = self._get_movie_credits(int(external_id))

            genres = movie.get("genres", [])
            genre_str = "/".join([g["name"] for g in genres[:2]]) or "Unknown"

            release_date = movie.get("release_date", "")
            year = int(release_date[:4]) if release_date else 0

            poster_path = movie.get("poster_path")
            poster_url = (
                f"https://image.tmdb.org/t/p/w500{poster_path}"
                if poster_path else None
            )

            return ExternalMovieResult(
                external_id=external_id,
                title=movie.get("title", "Unknown"),
                genre=genre_str,
                year=year,
                director=director,
                description=movie.get("overview", ""),
                poster_url=poster_url,
                rating=movie.get("vote_average")
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for movie {external_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_movie_by_id: {e}")
            return None
