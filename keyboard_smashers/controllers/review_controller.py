from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
import logging
import pandas as pd
from keyboard_smashers.dao.movie_dao import MovieDAO
from keyboard_smashers.auth import get_current_admin_user

logger = logging.getLogger(__name__)


class ReviewSchema(BaseModel):
    """Schema for review API responses"""
    review_id: str = Field(..., description="Unique review ID")
    movie_id: str = Field(..., description="Movie ID this review is for")
    user_id: str = Field(..., description="User who wrote the review")
    rating: int = Field(..., description="Rating given by the user")
    review_text: str = Field("", description="Text of the review")
    review_date: str = Field("", description="Date of the review (ISO 8601)")


class ReviewCreateSchema(BaseModel):
    """Schema for creating a new review"""
    movie_id: str = Field(..., description="Movie ID this review is for")
    user_id: str = Field(..., description="User who wrote the review")
    rating: int = Field(..., description="Rating given by the user")
    review_text: Optional[str] = Field("", description="Text of the review")
    review_date: Optional[str] = Field(None, description="Date of the review (ISO 8601)")


class ReviewUpdateSchema(BaseModel):
    """Schema for updating a review (all fields optional)"""
    rating: Optional[int] = Field(None, description="Rating given by the user")
    review_text: Optional[str] = Field(None, description="Text of the review")
    review_date: Optional[str] = Field(None, description="Date of the review (ISO 8601)")


class ReviewController:
    def __init__(self):
        self.df = None
        self.reviews: List[Review] = []
        self.movies = {}
        self.movies_by_id = {}

    def load_dataset(self, file_path: str):
        print(f"Loading dataset from: {file_path}")
        self.df = pd.read_csv(file_path)
        print(f"Dataset loaded: {len(self.df)} total rows.")

        self._initialize_movies()
        self._initialize_reviews()
        return True

    def _initialize_movies(self):
        print("Initializing movie models...")
        unique_movies = self.df['movie'].unique()
        for idx, movie_name in enumerate(unique_movies):
            movie_id = f"movie_{idx}"
            movie = Movie(
                movie_id=movie_id,
                title=movie_name,
                genre="",
                release_year=0,
                director="",
                cast=[],
                description=""
            )
            self.movies[movie_name] = movie
            self.movies_by_id[movie_id] = movie
        print(f"Initialized {len(self.movies)} unique movies.")

    def _initialize_reviews(self):
        print("Initializing review models...")
        for idx, row in self.df.iterrows():
            movie_title = row['movie']
            review = Review(
                review_id=f"review_{idx}",
                user_id=row.get('User', 'anonymous'),
                movie_id=self.movies[movie_title].movie_id,
                movie_title=movie_title,
                rating=row.get("User's Rating out of 10", 0),
                comment=row.get('Review', ''),
                review_date=row.get('Date of Review', ''),
                helpful_votes=row.get('Usefulness Vote', 0)
            )
            self.reviews.append(review)
            self.movies[movie_title].reviews.append(review)

        print(f"Initialized {len(self.reviews)} total reviews.")

    def get_all_reviews(self, limit: int = 10) -> List[dict]:
        return [self._review_to_dict(r) for r in self.reviews[:limit]]

    def get_review_by_id(self, review_id: str):
        # Always treat review_id as string
        review_id = str(review_id)
        for review in self.reviews:
            if str(review.review_id) == review_id:
                return self._review_to_dict(review)
        return None

    def create_review(self, review_data: dict):
        # Ensure review_id is always a string
        new_id = f"review_{len(self.reviews)}"
        movie_id = str(review_data.get("movie_id"))
        review = Review(
            review_id=new_id,
            user_id=review_data.get("user_id", "anonymous"),
            movie_id=movie_id,
            movie_title=review_data.get("movie_title", ""),
            rating=review_data.get("rating", 0),
            comment=review_data.get("comment", ""),
            review_date=review_data.get("review_date", ""),
            helpful_votes=review_data.get("helpful_votes", 0)
        )
        self.reviews.append(review)
        self.movies_by_id[movie_id].reviews.append(review)
        return self._review_to_dict(review)

    def update_review(self, review_id: str, update_data: dict):
        review_id = str(review_id)
        for review in self.reviews:
            if str(review.review_id) == review_id:
                for key, value in update_data.items():
                    if hasattr(review, key):
                        setattr(review, key, value)
                return self._review_to_dict(review)
        return None

    def delete_review(self, review_id: str):
        review_id = str(review_id)
        for i, review in enumerate(self.reviews):
            if str(review.review_id) == review_id:
                # Remove from movie's review list
                movie = self.movies_by_id.get(review.movie_id)
                if movie and review in movie.reviews:
                    movie.reviews.remove(review)
                del self.reviews[i]
                return True
        return False

    def _review_to_dict(self, review: Review) -> dict:
        movie = self.movies_by_id.get(review.movie_id)
        movie_title = movie.title if movie else "Unknown Movie"

        return {
            "review_id": review.review_id,
            "user_id": review.user_id,
            "movie_id": review.movie_id,
            "movie_title": movie_title,
            "rating": review.rating,
            "comment": review.comment,
            "helpful_votes": review.helpful_votes,

        }


review_controller_instance = ReviewController()

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)


@router.get("/")
def get_reviews_endpoint(limit: int = 10):
    reviews = review_controller_instance.get_all_reviews(limit=limit)
    return {
        "count": len(reviews),
        "reviews": reviews
    }
