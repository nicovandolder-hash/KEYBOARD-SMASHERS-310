from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from pathlib import Path
from keyboard_smashers.logging_config import setup_logging
from keyboard_smashers.controllers.review_controller import (
     router as review_router, review_controller_instance
)
from keyboard_smashers.controllers.user_controller import (
     router as user_router, user_controller_instance  # noqa: F401
)
from keyboard_smashers.controllers.movie_controller import (
     router as movie_router, movie_controller_instance
)
import logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="IMDB Reviews API")

app.include_router(review_router)
app.include_router(user_router)
app.include_router(movie_router)


class ReviewCreate(BaseModel):
    user_id: Optional[str] = "#anonymous"
    movie_id: str
    rating: Optional[int] = 0
    comment: Optional[str] = ""
    review_date: Optional[str] = ""
    helpful_votes: Optional[int] = 0


class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None
    review_date: Optional[str] = None
    helpful_votes: Optional[int] = None


@app.on_event("startup")
async def load_data():
    try:
        dataset_dir = Path("data")
        csv_files = list(dataset_dir.glob("*.csv"))

        review_csv_files = [f for f in csv_files if f.name != "users.csv"]

        if not review_csv_files:
            logger.error("No review CSV files found in data directory")
            raise FileNotFoundError(
                "No review CSV files found in data directory")

        csv_file = review_csv_files[0]
        logger.info(f"Loading reviews from: {csv_file}")
        review_controller_instance.load_dataset(str(csv_file))
        logger.info(
            f"Loaded {len(review_controller_instance.reviews)} "
            f"reviews for {len(review_controller_instance.movies)} movies."
            )

        logger.info("Application ready.")

    except Exception as e:
        print(f"FATAL ERROR loading dataset: {e}")
        raise


@app.get("/")
async def root():
    return {
        "message": "IMDB Reviews API",
        "status": "online",
        "total_reviews": len(review_controller_instance.reviews),
        "total_movies": len(movie_controller_instance.movies),
    }


@app.get("/reviews")
async def get_reviews(
    limit: int = Query(default=10, ge=1, le=100,
                       description="Number of reviews to return")
):
    reviews = review_controller_instance.get_all_reviews(limit=limit)
    return {
        "count": len(reviews),
        "reviews": reviews
    }


# CRUD endpoints for reviews
@app.get("/reviews/{review_id}")
async def get_review_by_id(review_id: str):
    review = review_controller_instance.get_review_by_id(str(review_id))
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.post("/reviews", status_code=201)
async def create_review(review: ReviewCreate):
    try:
        new_review = review_controller_instance.create_review(
            review.model_dump())
        return {"message": "Review created successfully", "review": new_review}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/reviews/{review_id}")
async def update_review_by_id(review_id: str, review_update: ReviewUpdate):
    update_data = review_update.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    updated_review = review_controller_instance.update_review(
        str(review_id), update_data)
    if not updated_review:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review updated successfully", "review": updated_review}


@app.delete("/reviews/{review_id}")
async def delete_review_by_id(review_id: str):
    success = review_controller_instance.delete_review(str(review_id))
    if not success:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": f"Review '{review_id}' deleted successfully"}
