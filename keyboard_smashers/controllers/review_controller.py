from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
import logging
from keyboard_smashers.dao.review_dao import ReviewDAO
from keyboard_smashers.auth import get_current_user, get_current_admin_user

logger = logging.getLogger(__name__)


class ReviewSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    review_id: str = Field(..., description="Unique review ID")
    movie_id: str = Field(..., description="Movie ID being reviewed")
    user_id: Optional[str] = Field(None, description="User ID (null for IMDB reviews)")
    imdb_username: Optional[str] = Field(None, description="IMDB username for legacy reviews")
    rating: float = Field(..., description="Rating from 1-5", ge=1, le=5)
    review_text: str = Field(..., description="Review text content")
    review_date: str = Field(..., description="Review date")


class ReviewCreateSchema(BaseModel):
    movie_id: str = Field(..., description="Movie ID to review", min_length=1)
    rating: float = Field(..., description="Rating from 1-5", ge=1, le=5)
    review_text: str = Field(..., description="Review text", max_length=250, min_length=1)


class ReviewUpdateSchema(BaseModel):
    rating: Optional[float] = Field(None, description="Rating from 1-5", ge=1, le=5)
    review_text: Optional[str] = Field(None, description="Review text", max_length=250, min_length=1)


class ReviewController:
    def __init__(
        self,
        imdb_csv_path: str = "data/imdb_reviews.csv",
        new_reviews_csv_path: str = "data/reviews_new.csv"
    ):
        self.review_dao = ReviewDAO(
            imdb_csv_path=imdb_csv_path,
            new_reviews_csv_path=new_reviews_csv_path
        )
        logger.info(
            f"ReviewController initialized with "
            f"{len(self.review_dao.reviews)} reviews"
        )

    def _dict_to_schema(self, review_dict: dict) -> ReviewSchema:
        return ReviewSchema(**review_dict)

    def get_review_by_id(self, review_id: str) -> ReviewSchema:
        logger.info(f"Fetching review: {review_id}")
        try:
            review_dict = self.review_dao.get_review(review_id)
            return self._dict_to_schema(review_dict)
        except KeyError:
            logger.error(f"Review not found: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )

    def get_reviews_for_movie(self, movie_id: str) -> List[ReviewSchema]:
        logger.info(f"Fetching reviews for movie: {movie_id}")
        reviews = self.review_dao.get_reviews_for_movie(movie_id)
        logger.info(f"Found {len(reviews)} reviews for movie: {movie_id}")
        return [self._dict_to_schema(review) for review in reviews]

    def get_reviews_by_user(self, user_id: str) -> List[ReviewSchema]:
        logger.info(f"Fetching reviews by user: {user_id}")
        reviews = self.review_dao.get_reviews_by_user(user_id)
        logger.info(f"Found {len(reviews)} reviews by user: {user_id}")
        return [self._dict_to_schema(review) for review in reviews]

    def create_review(
        self,
        review_data: ReviewCreateSchema,
        user_id: str
    ) -> ReviewSchema:
        logger.info(
            f"Creating review for movie {review_data.movie_id} by user {user_id}"
        )

        # Verify movie exists
        from keyboard_smashers.controllers.movie_controller import (
            movie_controller_instance
        )
        try:
            movie_controller_instance.get_movie_by_id(review_data.movie_id)
        except HTTPException:
            logger.error(f"Movie not found: {review_data.movie_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Movie with ID '{review_data.movie_id}' not found"
            )

        # Create review (DAO handles duplicate check)
        try:
            review_dict = review_data.model_dump()
            review_dict['user_id'] = user_id
            created_review = self.review_dao.create_review(review_dict)
            logger.info(
                f"Review created successfully: {created_review['review_id']}"
            )
            return self._dict_to_schema(created_review)
        except ValueError as e:
            # Duplicate review for this user/movie
            logger.warning(f"Duplicate review attempt: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )

    def update_review(
        self,
        review_id: str,
        review_data: ReviewUpdateSchema,
        current_user_id: str
    ) -> ReviewSchema:
        logger.info(f"Updating review: {review_id}")

        # Get existing review
        try:
            existing_review = self.review_dao.get_review(review_id)
        except KeyError:
            logger.error(f"Review not found for update: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )

        # Authorization check - only owner can update
        if existing_review.get('user_id') != current_user_id:
            logger.warning(
                f"Unauthorized update attempt on review {review_id} "
                f"by user {current_user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="You can only update your own reviews"
            )

        # Check if IMDB review (cannot be updated)
        if not existing_review.get('user_id'):
            logger.warning(
                f"Attempted to update IMDB review: {review_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Cannot update legacy IMDB reviews"
            )

        update_dict = review_data.model_dump(exclude_none=True)

        if not update_dict:
            raise HTTPException(
                status_code=400,
                detail="No fields to update"
            )

        try:
            updated_review = self.review_dao.update_review(review_id, update_dict)
            logger.info(f"Review updated successfully: {review_id}")
            return self._dict_to_schema(updated_review)
        except KeyError:
            logger.error(f"Review not found during update: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )

    def delete_review(self, review_id: str, current_user_id: str) -> dict:
        logger.info(f"Deleting review: {review_id}")

        # Get existing review
        try:
            existing_review = self.review_dao.get_review(review_id)
        except KeyError:
            logger.error(f"Review not found for deletion: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )

        # Authorization check - only owner can delete
        if existing_review.get('user_id') != current_user_id:
            logger.warning(
                f"Unauthorized delete attempt on review {review_id} "
                f"by user {current_user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own reviews"
            )

        # Check if IMDB review (cannot be deleted)
        if not existing_review.get('user_id'):
            logger.warning(
                f"Attempted to delete IMDB review: {review_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Cannot delete legacy IMDB reviews"
            )

        try:
            self.review_dao.delete_review(review_id)
            logger.info(f"Review deleted successfully: {review_id}")
            return {"message": f"Review '{review_id}' deleted successfully"}
        except KeyError:
            logger.error(f"Review not found during deletion: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )

    def admin_delete_review(self, review_id: str) -> dict:
        """Admin can delete any review (for moderation)"""
        logger.info(f"Admin deleting review: {review_id}")

        try:
            existing_review = self.review_dao.get_review(review_id)
        except KeyError:
            logger.error(f"Review not found for admin deletion: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )

        # Check if IMDB review (cannot be deleted)
        if not existing_review.get('user_id'):
            logger.warning(
                f"Admin attempted to delete IMDB review: {review_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Cannot delete legacy IMDB reviews"
            )

        try:
            self.review_dao.delete_review(review_id)
            logger.info(f"Review deleted by admin: {review_id}")
            return {"message": f"Review '{review_id}' deleted by admin"}
        except KeyError:
            logger.error(f"Review not found during admin deletion: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )


# Global instance
review_controller_instance = ReviewController()

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)


# PUBLIC ENDPOINTS

@router.get("/movie/{movie_id}", response_model=List[ReviewSchema])
def get_reviews_for_movie(movie_id: str):
    """Get all reviews for a specific movie"""
    return review_controller_instance.get_reviews_for_movie(movie_id)


@router.get("/user/{user_id}", response_model=List[ReviewSchema])
def get_reviews_by_user(user_id: str):
    """Get all reviews by a specific user"""
    return review_controller_instance.get_reviews_by_user(user_id)


@router.get("/{review_id}", response_model=ReviewSchema)
def get_review(review_id: str):
    """Get a specific review by ID"""
    return review_controller_instance.get_review_by_id(review_id)


# AUTHENTICATED ENDPOINTS (LOGGED-IN USERS)

@router.post("/", response_model=ReviewSchema, status_code=201)
def create_review(
    review_data: ReviewCreateSchema,
    current_user_id: str = Depends(get_current_user)
):
    """Create a new review (requires authentication)"""
    return review_controller_instance.create_review(review_data, current_user_id)


@router.put("/{review_id}", response_model=ReviewSchema)
def update_review(
    review_id: str,
    review_data: ReviewUpdateSchema,
    current_user_id: str = Depends(get_current_user)
):
    """Update your own review (requires authentication)"""
    return review_controller_instance.update_review(
        review_id, review_data, current_user_id
    )


@router.delete("/{review_id}")
def delete_review(
    review_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """Delete your own review (requires authentication)"""
    return review_controller_instance.delete_review(review_id, current_user_id)


# ADMIN-ONLY ENDPOINTS

@router.delete("/{review_id}/admin")
def admin_delete_review(
    review_id: str,
    admin_user_id: str = Depends(get_current_admin_user)
):
    """Admin delete any review for moderation (requires admin privileges)"""
    return review_controller_instance.admin_delete_review(review_id)
