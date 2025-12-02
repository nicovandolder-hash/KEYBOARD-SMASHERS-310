from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
import logging
import pandas as pd
from keyboard_smashers.dao.movie_dao import MovieDAO
from keyboard_smashers.auth import get_current_admin_user
from keyboard_smashers.external_services.movie_service import (
    ExternalMovieService,
    ExternalMovieResult
)
import os

# DEBUG: Check if API key is loaded
tmdb_key = os.getenv("TMDB_API_KEY")
print(f"DEBUG: TMDB_API_KEY loaded: {tmdb_key is not None}")
print(f"DEBUG: TMDB_API_KEY value: {tmdb_key[:10] if tmdb_key else 'None'}...")

logger = logging.getLogger(__name__)


class MovieSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    movie_id: str = Field(..., description="Unique movie ID")
    title: str = Field(..., description="Movie title")
    genre: str = Field("", description="Movie genre")
    year: int = Field(0, description="Release year")
    director: str = Field("", description="Director name")
    description: str = Field("", description="Movie description")


class MovieCreateSchema(BaseModel):
    title: str = Field(..., description="Movie title", min_length=1)
    genre: Optional[str] = Field("", description="Movie genre")
    year: Optional[int] = Field(0, description="Release year")
    director: Optional[str] = Field("", description="Director name")
    description: Optional[str] = Field("", description="Movie description")


class MovieUpdateSchema(BaseModel):
    title: Optional[str] = Field(None, description="Movie title", min_length=1)
    genre: Optional[str] = Field(None, description="Movie genre")
    year: Optional[int] = Field(None, description="Release year")
    director: Optional[str] = Field(None, description="Director name")
    description: Optional[str] = Field(None, description="Movie description")


class MovieController:
    def __init__(self, csv_path: str = "data/movies.csv"):
        self.movie_dao = MovieDAO(csv_path=csv_path)

        tmdb_api_key = os.getenv("TMDB_API_KEY")
        self.external_service = (
            ExternalMovieService(tmdb_api_key)
            if tmdb_api_key else None
        )

        logger.info(
            f"MovieController initialized with "
            f"{len(self.movie_dao.movies)} movies"
        )

    def _dict_to_schema(self, movie_dict: dict) -> MovieSchema:
        cleaned_dict = {}
        for key, value in movie_dict.items():
            if pd.isna(value):
                if key == 'year':
                    cleaned_dict[key] = 0
                else:
                    cleaned_dict[key] = ""
            else:
                cleaned_dict[key] = value
        return MovieSchema(**cleaned_dict)

    def get_all_movies(self) -> List[MovieSchema]:
        logger.info("Fetching all movies")
        movies = self.movie_dao.get_all_movies()
        return [self._dict_to_schema(movie) for movie in movies]

    def get_movie_by_id(self, movie_id: str) -> MovieSchema:
        logger.info(f"Fetching movie: {movie_id}")
        try:
            movie_dict = self.movie_dao.get_movie(movie_id)
            return self._dict_to_schema(movie_dict)
        except KeyError:
            logger.error(f"Movie not found: {movie_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Movie with ID '{movie_id}' not found"
            )

    def create_movie(self, movie_data: MovieCreateSchema) -> MovieSchema:
        logger.info(f"Creating movie: {movie_data.title}")
        all_movies = self.movie_dao.get_all_movies()
        if any(
            m['title'].lower() == movie_data.title.lower()
            for m in all_movies
        ):
            logger.warning(f"Duplicate title attempted: {movie_data.title}")
            raise HTTPException(
                status_code=400,
                detail=f"Movie with title '{movie_data.title}' already exists"
            )

        movie_dict = movie_data.model_dump()
        created_movie = self.movie_dao.create_movie(movie_dict)

        logger.info(
            f"Movie created successfully: {created_movie['movie_id']}"
        )
        return self._dict_to_schema(created_movie)

    def update_movie(
        self, movie_id: str, movie_data: MovieUpdateSchema
    ) -> MovieSchema:
        logger.info(f"Updating movie: {movie_id}")

        try:
            self.movie_dao.get_movie(movie_id)
        except KeyError:
            logger.error(f"Movie not found for update: {movie_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Movie with ID '{movie_id}' not found"
            )

        if movie_data.title:
            all_movies = self.movie_dao.get_all_movies()
            if any(
                m['title'].lower() == movie_data.title.lower() and
                m['movie_id'] != movie_id
                for m in all_movies
            ):
                logger.warning(
                    f"Duplicate title attempted: {movie_data.title}"
                )
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Movie with title '{movie_data.title}' "
                        f"already exists"
                    )
                )

        update_dict = movie_data.model_dump(exclude_none=True)

        if not update_dict:
            raise HTTPException(
                status_code=400, detail="No fields to update"
            )

        updated_movie = self.movie_dao.update_movie(movie_id, update_dict)
        logger.info(f"Movie updated successfully: {movie_id}")
        return self._dict_to_schema(updated_movie)

    def delete_movie(self, movie_id: str) -> dict:
        logger.info(f"Deleting movie: {movie_id}")
        try:
            self.movie_dao.delete_movie(movie_id)
            logger.info(f"Movie deleted successfully: {movie_id}")
            return {"message": f"Movie '{movie_id}' deleted successfully"}
        except KeyError:
            logger.error(f"Movie not found for deletion: {movie_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Movie with ID '{movie_id}' not found"
            )

    def search_movies_by_title(self, title: str) -> List[MovieSchema]:
        logger.info(f"Searching movies by title: {title}")
        all_movies = self.movie_dao.get_all_movies()

        title_lower = title.lower()
        matching_movies = [
            movie for movie in all_movies
            if title_lower in movie['title'].lower()
        ]

        logger.info(
            f"Found {len(matching_movies)} movies matching title: {title}"
        )
        return [self._dict_to_schema(movie) for movie in matching_movies]

    def get_movies_by_genre(self, genre: str) -> List[MovieSchema]:
        logger.info(f"Fetching movies by genre: {genre}")
        all_movies = self.movie_dao.get_all_movies()

        genre_lower = genre.lower()
        matching_movies = [
            movie for movie in all_movies
            if movie['genre'].lower() == genre_lower
        ]

        logger.info(f"Found {len(matching_movies)} movies in genre: {genre}")
        return [self._dict_to_schema(movie) for movie in matching_movies]

    def search_movies(self, query: str) -> List[MovieSchema]:
        logger.info(f"Searching movies with query: {query}")
        all_movies = self.movie_dao.get_all_movies()

        query_lower = query.lower()
        matching_movies = [
            movie for movie in all_movies
            if (query_lower in str(movie.get('title', '')).lower() or
                query_lower in str(movie.get('director', '')).lower() or
                query_lower in str(movie.get('description', '')).lower())
        ]

        logger.info(
            f"Found {len(matching_movies)} movies matching query: {query}"
        )
        return [self._dict_to_schema(movie) for movie in matching_movies]

    def search_external_movies(self, query: str, limit: int = 10) -> (
            List[ExternalMovieResult]):
        """
        Search for movies in external database (TMDB)

        Args:
            query: Search query string
            limit: Maximum results to return

        Returns:
            List of external movie results
        """
        if not self.external_service:
            logger.error("External movie service not configured")
            raise HTTPException(
                status_code=503,
                detail="External movie search is not available. "
                "Please configure TMDB_API_KEY."
            )

        logger.info(f"Searching external database for: {query}")

        try:
            results = self.external_service.search_movies(query, limit)
            logger.info(f"Found {len(results)} external movies")
            return results
        except Exception as e:
            logger.error(f"External search failed: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"External movie search failed: {str(e)}"
            )

    def import_movie_from_external(self, external_id: str) -> MovieSchema:
        """
        Import a movie from external database into local database

        Args:
            external_id: TMDB movie ID

        Returns:
            Created MovieSchema object
        """
        if not self.external_service:
            logger.error("External movie service not configured")
            raise HTTPException(
                status_code=503,
                detail="External movie import is not available."
            )

        logger.info(f"Importing movie from external ID: {external_id}")

        external_movie = self.external_service.get_movie_by_id(external_id)

        if not external_movie:
            raise HTTPException(
                status_code=404,
                detail=f"Movie with external ID '{external_id}' not found"
            )

        all_movies = self.movie_dao.get_all_movies()
        existing_movie = next(
            (m for m in all_movies
             if m['title'].lower() == external_movie.title.lower()),
            None
        )

        if existing_movie:
            logger.warning(
                f"Movie '{external_movie.title}' already exists locally"
            )
            raise HTTPException(
                status_code=409,
                detail=f"Movie '{external_movie.title}' "
                f"already exists in your database"
            )

        movie_data = MovieCreateSchema(
            title=external_movie.title,
            genre=external_movie.genre,
            year=external_movie.year,
            director=external_movie.director,
            description=external_movie.description
        )

        # Create movie in local database
        created_movie = self.create_movie(movie_data)

        logger.info(
            f"Successfully imported movie: {created_movie.title} "
            f"(ID: {created_movie.movie_id})"
        )

        return created_movie

    def search_and_import_suggestions(
        self,
        query: str,
        auto_import: bool = False
    ) -> dict:
        """
        Search external database and optionally import top result

        Args:
            query: Search query
            auto_import: If True, automatically import the top match

        Returns:
            Dictionary with search results and import status
        """
        if not self.external_service:
            raise HTTPException(
                status_code=503,
                detail="External movie service not available"
            )

        # Search external database
        external_results = self.search_external_movies(query, limit=5)

        if not external_results:
            return {
                "query": query,
                "results": [],
                "imported": None,
                "message": "No movies found"
            }

        imported_movie = None

        if auto_import:
            # Import the top match
            try:
                top_result = external_results[0]
                imported_movie = self.import_movie_from_external(
                    top_result.external_id
                )
            except HTTPException as e:
                # Movie might already exist
                logger.warning(f"Could not auto-import: {e.detail}")

        return {
            "query": query,
            "results": external_results,
            "imported": imported_movie,
            "message": (
                f"Imported '{imported_movie.title}'"
                if imported_movie
                else "Search completed"
            )
        }


# Global instance
movie_controller_instance = MovieController()

router = APIRouter(
    prefix="/movies",
    tags=["movies"],
)


# PUBLIC ENDPOINTS

@router.get("/", response_model=List[MovieSchema])
def get_all_movies():
    return movie_controller_instance.get_all_movies()


@router.get("/search", response_model=List[MovieSchema])
def search_movies(q: str):
    return movie_controller_instance.search_movies(q)


@router.get("/external/search", response_model=List[ExternalMovieResult])
def search_external_movies(q: str, limit: int = 10):
    """
    Args:
        q: Search query
        limit: Maximum number of results (default: 10)

    Returns:
        List of movies from external database
    """
    return movie_controller_instance.search_external_movies(q, limit)


@router.get("/genre/{genre}", response_model=List[MovieSchema])
def get_movies_by_genre(genre: str):
    return movie_controller_instance.get_movies_by_genre(genre)


@router.get("/{movie_id}", response_model=MovieSchema)
def get_movie(movie_id: str):
    return movie_controller_instance.get_movie_by_id(movie_id)


# ADMIN-ONLY ENDPOINTS


@router.post("/", response_model=MovieSchema, status_code=201)
def create_movie(
    movie_data: MovieCreateSchema,
    admin_user_id: str = Depends(get_current_admin_user)
):
    return movie_controller_instance.create_movie(movie_data)


@router.put("/{movie_id}", response_model=MovieSchema)
def update_movie(
    movie_id: str,
    movie_data: MovieUpdateSchema,
    admin_user_id: str = Depends(get_current_admin_user)
):
    return movie_controller_instance.update_movie(movie_id, movie_data)


@router.delete("/{movie_id}")
def delete_movie(
    movie_id: str,
    admin_user_id: str = Depends(get_current_admin_user)
):
    return movie_controller_instance.delete_movie(movie_id)


@router.post("/external/import/{external_id}",
             response_model=MovieSchema)
def import_movie(
    external_id: str,
    admin_user_id: str = Depends(get_current_admin_user)
):
    """
    Import a movie from external database (TMDB) into local database

    Args:
        external_id: TMDB movie ID

    Returns:
        Created movie object
    """
    return movie_controller_instance.import_movie_from_external(external_id)


@router.post("/external/search-and-import", response_model=dict)
def search_and_import(
    q: str,
    auto_import: bool = False,
    admin_user_id: str = Depends(get_current_admin_user)
):
    """
    Args:
        q: Search query
        auto_import: If True, automatically import the best match

    Returns:
        Search results and import status
    """
    return movie_controller_instance.search_and_import_suggestions(
        q,
        auto_import
    )
