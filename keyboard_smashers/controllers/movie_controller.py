from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
import logging
import pandas as pd
from keyboard_smashers.dao.movie_dao import MovieDAO
from keyboard_smashers.dao.review_dao import review_dao_instance
from keyboard_smashers.auth import get_current_admin_user

logger = logging.getLogger(__name__)


class MovieSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    movie_id: str = Field(..., description="Unique movie ID")
    title: str = Field(..., description="Movie title")
    genre: str = Field("", description="Movie genre")
    year: int = Field(0, description="Release year")
    director: str = Field("", description="Director name")
    description: str = Field("", description="Movie description")
    average_rating: Optional[float] = Field(
        None, description="Community average rating (1-5)"
    )


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


class PaginatedMoviesResponse(BaseModel):
    movies: List[MovieSchema] = Field(..., description="List of movies")
    total: int = Field(..., description="Total number of movies")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")


class MovieController:
    def __init__(self, csv_path: str = "data/movies.csv"):
        self.movie_dao = MovieDAO(csv_path=csv_path)
        self.review_dao = review_dao_instance
        logger.info(
            f"MovieController initialized with "
            f"{len(self.movie_dao.movies)} movies"
        )

    def _calculate_average_rating(self, movie_id: str) -> Optional[float]:
        """
        Calculate average rating for a movie from all reviews.
        Returns None if no reviews exist.
        """
        try:
            reviews = self.review_dao.get_reviews_for_movie(movie_id)
            if not reviews:
                return None

            total_rating = sum(review['rating'] for review in reviews)
            avg_rating = total_rating / len(reviews)
            return round(avg_rating, 2)
        except Exception as e:
            logger.warning(
                f"Error calculating average rating for {movie_id}: {e}"
            )
            return None

    def _dict_to_schema(
        self, movie_dict: dict, include_rating: bool = False
    ) -> MovieSchema:
        cleaned_dict = {}
        for key, value in movie_dict.items():
            if pd.isna(value):
                if key == 'year':
                    cleaned_dict[key] = 0
                else:
                    cleaned_dict[key] = ""
            else:
                cleaned_dict[key] = value

        if include_rating:
            cleaned_dict['average_rating'] = self._calculate_average_rating(
                movie_dict['movie_id']
            )

        return MovieSchema(**cleaned_dict)

    def get_all_movies(
        self, skip: int = 0, limit: int = 20
    ) -> PaginatedMoviesResponse:
        logger.info(f"Fetching movies with skip={skip}, limit={limit}")
        all_movies = self.movie_dao.get_all_movies()
        total = len(all_movies)

        # Apply pagination
        paginated_movies = all_movies[skip:skip + limit]
        movie_schemas = [
            self._dict_to_schema(movie) for movie in paginated_movies
        ]

        page = (skip // limit) + 1 if limit > 0 else 1

        return PaginatedMoviesResponse(
            movies=movie_schemas,
            total=total,
            page=page,
            page_size=limit
        )

    def get_movie_by_id(self, movie_id: str) -> MovieSchema:
        logger.info(f"Fetching movie: {movie_id}")
        try:
            movie_dict = self.movie_dao.get_movie(movie_id)
            return self._dict_to_schema(movie_dict, include_rating=True)
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

        genre_lower = genre.lower().strip()
        matching_movies = []

        for movie in all_movies:
            current_genres = [
                g.strip().lower()
                for g in movie['genre'].replace(',', '/').split('/')
            ]

            if genre_lower in current_genres:
                matching_movies.append(movie)

        logger.info(f"Found {len(matching_movies)} movies in genre: {genre}")
        return [self._dict_to_schema(movie) for movie in matching_movies]

    def search_movies(
        self,
        query: str,
        sort_by: Optional[str] = None
    ) -> List[MovieSchema]:
        logger.info(f"Searching movies with query: {query}, sort: {sort_by}")
        all_movies = self.movie_dao.get_all_movies()

        query_lower = query.lower()
        matching_movies = [
            movie for movie in all_movies
            if (query_lower in str(movie.get('title', '')).lower() or
                query_lower in str(movie.get('director', '')).lower() or
                query_lower in str(movie.get('description', '')).lower())
        ]

        # Apply sorting if requested
        if sort_by:
            if sort_by == "year":
                matching_movies.sort(
                    key=lambda m: m.get('year', 0),
                    reverse=True
                )
            elif sort_by == "title":
                matching_movies.sort(
                    key=lambda m: str(m.get('title', '')).lower()
                )

        logger.info(
            f"Found {len(matching_movies)} movies matching query: {query}"
        )
        return [self._dict_to_schema(movie) for movie in matching_movies]


# Global instance
movie_controller_instance = MovieController()

router = APIRouter(
    prefix="/movies",
    tags=["movies"],
)


# PUBLIC ENDPOINTS

@router.get("/", response_model=PaginatedMoviesResponse)
def get_all_movies(skip: int = 0, limit: int = 20):
    return movie_controller_instance.get_all_movies(skip=skip, limit=limit)


@router.get("/search", response_model=List[MovieSchema])
def search_movies(q: str, sort_by: Optional[str] = None):
    return movie_controller_instance.search_movies(q, sort_by=sort_by)


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
