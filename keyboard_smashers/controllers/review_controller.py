
import logging
import pandas as pd
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
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
    review_date: Optional[str] = Field(None,
                                       description="Date of the "
                                       "review (ISO 8601)")


class ReviewUpdateSchema(BaseModel):
    """Schema for updating a review (all fields optional)"""
    rating: Optional[int] = Field(None, description="Rating given by the user")
    review_text: Optional[str] = Field(None, description="Text of the review")
    review_date: Optional[str] = Field(None,
                                       description="Date of the "
                                       "review (ISO 8601)")


class ReviewController:
    def __init__(self, csv_path: str = "data/reviews.csv"):
        from keyboard_smashers.dao.review_dao import review_dao
        self.review_dao = review_dao(csv_path=csv_path)
        logger.info(f"ReviewController initialized with "
                    f"{len(self.review_dao.reviews)} reviews")

    def _dict_to_schema(self, review_dict: dict) -> ReviewSchema:
        # Replace NaN with default values and ensure types
        cleaned = {}
        for key, value in review_dict.items():
            if pd.isna(value):
                if key == 'rating':
                    cleaned[key] = 0
                else:
                    cleaned[key] = ""
            else:
                cleaned[key] = value
        return ReviewSchema(**cleaned)

    def get_all_reviews(self, limit: int = 10) -> List[ReviewSchema]:
        logger.info(f"Fetching up to {limit} reviews")
        reviews = list(self.review_dao.reviews.values())[:limit]
        return [self._dict_to_schema(r) for r in reviews]

    def get_review_by_id(self, review_id: str) -> ReviewSchema:
        logger.info(f"Fetching review: {review_id}")
        review = self.review_dao.get_review(str(review_id))
        if not review:
            logger.error(f"Review not found: {review_id}")
            raise HTTPException(status_code=404,
                                detail=f"Review with ID '"
                                f"{review_id}' not found")
        return self._dict_to_schema(review)

    def create_review(self, review_data: ReviewCreateSchema) -> ReviewSchema:
        logger.info(f"Creating review for movie: {review_data.movie_id}")
        review_dict = review_data.model_dump()
        created_review = self.review_dao.create_review(review_dict)
        logger.info(f"Review created successfully: "
                    f"{created_review['review_id']}")
        return self._dict_to_schema(created_review)

    def update_review(self, review_id: str,
                      review_data: ReviewUpdateSchema) -> ReviewSchema:
        logger.info(f"Updating review: {review_id}")
        update_dict = review_data.model_dump(exclude_none=True)
        if not update_dict:
            raise HTTPException(status_code=400, detail="No fields to update")
        updated_review = self.review_dao.update_review(str(review_id),
                                                       update_dict)
        if not updated_review:
            logger.error(f"Review not found for update: {review_id}")
            raise HTTPException(status_code=404,
                                detail=f"Review with ID '"
                                f"{review_id}' not found")
        logger.info(f"Review updated successfully: {review_id}")
        return self._dict_to_schema(updated_review)

    def delete_review(self, review_id: str) -> dict:
        logger.info(f"Deleting review: {review_id}")
        success = self.review_dao.delete_review(str(review_id))
        if not success:
            logger.error(f"Review not found for deletion: {review_id}")
            raise HTTPException(status_code=404,
                                detail=f"Review with ID '"
                                f"{review_id}' not found")
        logger.info(f"Review deleted successfully: {review_id}")
        return {"message": f"Review '{review_id}' deleted successfully"}


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
