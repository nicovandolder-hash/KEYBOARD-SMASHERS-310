from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
import logging
import pandas as pd
from keyboard_smashers.dao.movie_dao import MovieDAO
from keyboard_smashers.auth import get_current_admin_user

logger = logging.getLogger(__name__)


class MovieSchema(BaseModel):
    """Schema for movie API responses"""
    model_config = ConfigDict(from_attributes=True)

    movie_id: str = Field(..., description="Unique movie ID")
    title: str = Field(..., description="Movie title")
    genre: str = Field("", description="Movie genre")
    year: int = Field(0, description="Release year")
    director: str = Field("", description="Director name")
    description: str = Field("", description="Movie description")


class MovieCreateSchema(BaseModel):
    """Schema for creating a new movie"""
    title: str = Field(..., description="Movie title", min_length=1)
    genre: Optional[str] = Field("", description="Movie genre")
    year: Optional[int] = Field(0, description="Release year")
    director: Optional[str] = Field("", description="Director name")
    description: Optional[str] = Field("", description="Movie description")


class MovieUpdateSchema(BaseModel):
    """Schema for updating a movie (all fields optional)"""
    title: Optional[str] = Field(None, description="Movie title", min_length=1)
    genre: Optional[str] = Field(None, description="Movie genre")
    year: Optional[int] = Field(None, description="Release year")
    director: Optional[str] = Field(None, description="Director name")
    description: Optional[str] = Field(None, description="Movie description")


class MovieController:
    def __init__(self, csv_path: str = "data/movies.csv"):
        self.movie_dao = MovieDAO(csv_path=csv_path)
        logger.info(f"MovieController initialized with {len(self.movie_dao.movies)} movies")

    def _dict_to_schema(self, movie_dict: dict) -> MovieSchema:
        """Convert movie dictionary to MovieSchema, handling NaN values"""
        # Replace NaN with default values
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
        """Get all movies"""
        logger.info("Fetching all movies")
        movies = self.movie_dao.get_all_movies()
        return [self._dict_to_schema(movie) for movie in movies]

    def get_movie_by_id(self, movie_id: str) -> MovieSchema:
        """Get a single movie by ID"""
        logger.info(f"Fetching movie: {movie_id}")
        try:
            movie_dict = self.movie_dao.get_movie(movie_id)
            return self._dict_to_schema(movie_dict)
        except KeyError:
            logger.error(f"Movie not found: {movie_id}")
            raise HTTPException(status_code=404, detail=f"Movie with ID '{movie_id}' not found")

    def create_movie(self, movie_data: MovieCreateSchema) -> MovieSchema:
        """Create a new movie (Admin only)"""
        logger.info(f"Creating movie: {movie_data.title}")

        # Validate: Check for duplicate titles
        all_movies = self.movie_dao.get_all_movies()
        if any(m['title'].lower() == movie_data.title.lower() for m in all_movies):
            logger.warning(f"Duplicate title attempted: {movie_data.title}")
            raise HTTPException(
                status_code=400,
                detail=f"Movie with title '{movie_data.title}' already exists"
            )

        # Convert to dict and create
        movie_dict = movie_data.model_dump()
        created_movie = self.movie_dao.create_movie(movie_dict)

        logger.info(f"Movie created successfully: {created_movie['movie_id']}")
        return self._dict_to_schema(created_movie)

    def update_movie(self, movie_id: str, movie_data: MovieUpdateSchema) -> MovieSchema:
        """Update an existing movie (Admin only)"""
        logger.info(f"Updating movie: {movie_id}")

        # Check if movie exists
        try:
            self.movie_dao.get_movie(movie_id)
        except KeyError:
            logger.error(f"Movie not found for update: {movie_id}")
            raise HTTPException(status_code=404, detail=f"Movie with ID '{movie_id}' not found")

        # Validate: Check for duplicate title if title is being updated
        if movie_data.title:
            all_movies = self.movie_dao.get_all_movies()
            if any(m['title'].lower() == movie_data.title.lower() and m['movie_id'] != movie_id
                   for m in all_movies):
                logger.warning(f"Duplicate title attempted: {movie_data.title}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Movie with title '{movie_data.title}' already exists"
                )

        # Convert to dict (exclude None values)
        update_dict = movie_data.model_dump(exclude_none=True)

        if not update_dict:
            raise HTTPException(status_code=400, detail="No fields to update")

        updated_movie = self.movie_dao.update_movie(movie_id, update_dict)
        logger.info(f"Movie updated successfully: {movie_id}")
        return self._dict_to_schema(updated_movie)

    def delete_movie(self, movie_id: str) -> dict:
        """Delete a movie (Admin only)"""
        logger.info(f"Deleting movie: {movie_id}")
        try:
            self.movie_dao.delete_movie(movie_id)
            logger.info(f"Movie deleted successfully: {movie_id}")
            return {"message": f"Movie '{movie_id}' deleted successfully"}
        except KeyError:
            logger.error(f"Movie not found for deletion: {movie_id}")
            raise HTTPException(status_code=404, detail=f"Movie with ID '{movie_id}' not found")

    def search_movies_by_title(self, title: str) -> List[MovieSchema]:
        """Search movies by title (partial match, case-insensitive)"""
        logger.info(f"Searching movies by title: {title}")
        all_movies = self.movie_dao.get_all_movies()

        title_lower = title.lower()
        matching_movies = [
            movie for movie in all_movies
            if title_lower in movie['title'].lower()
        ]

        logger.info(f"Found {len(matching_movies)} movies matching title: {title}")
        return [self._dict_to_schema(movie) for movie in matching_movies]

    def get_movies_by_genre(self, genre: str) -> List[MovieSchema]:
        """Get all movies of a specific genre (exact match, case-insensitive)"""
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
        """General search across title, director, and description"""
        logger.info(f"Searching movies with query: {query}")
        all_movies = self.movie_dao.get_all_movies()

        query_lower = query.lower()
        matching_movies = [
            movie for movie in all_movies
            if (query_lower in str(movie.get('title', '')).lower() or
                query_lower in str(movie.get('director', '')).lower() or
                query_lower in str(movie.get('description', '')).lower())
        ]

        logger.info(f"Found {len(matching_movies)} movies matching query: {query}")
        return [self._dict_to_schema(movie) for movie in matching_movies]


# Global instance
movie_controller_instance = MovieController()

# API Router
router = APIRouter(
    prefix="/movies",
    tags=["movies"],
)


# PUBLIC ENDPOINTS

@router.get("/", response_model=List[MovieSchema])
def get_all_movies():
    """Get all movies"""
    return movie_controller_instance.get_all_movies()


@router.get("/search", response_model=List[MovieSchema])
def search_movies(q: str):
    """Search movies by title, director, or description"""
    return movie_controller_instance.search_movies(q)


@router.get("/genre/{genre}", response_model=List[MovieSchema])
def get_movies_by_genre(genre: str):
    """Get all movies of a specific genre"""
    return movie_controller_instance.get_movies_by_genre(genre)


@router.get("/{movie_id}", response_model=MovieSchema)
def get_movie(movie_id: str):
    """Get a specific movie by ID"""
    return movie_controller_instance.get_movie_by_id(movie_id)


# ADMIN-ONLY ENDPOINTS

@router.post("/", response_model=MovieSchema, status_code=201)
def create_movie(
    movie_data: MovieCreateSchema,
    admin_user_id: str = Depends(get_current_admin_user)
):
    """Create a new movie (Admin only)"""
    return movie_controller_instance.create_movie(movie_data)


@router.put("/{movie_id}", response_model=MovieSchema)
def update_movie(
    movie_id: str,
    movie_data: MovieUpdateSchema,
    admin_user_id: str = Depends(get_current_admin_user)
):
    """Update a movie (Admin only)"""
    return movie_controller_instance.update_movie(movie_id, movie_data)


@router.delete("/{movie_id}")
def delete_movie(
    movie_id: str,
    admin_user_id: str = Depends(get_current_admin_user)
):
    """Delete a movie (Admin only)"""
    return movie_controller_instance.delete_movie(movie_id)
