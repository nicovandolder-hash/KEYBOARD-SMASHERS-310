from fastapi import FastAPI, Query
from fastapi import HTTPException
from pathlib import Path
from keyboard_smashers.controllers.review_controller import ReviewController

from pydantic import BaseModel
from typing import Optional


app = FastAPI(title="IMDB Reviews API")


controller = ReviewController()


#added
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
#


@app.on_event("startup")
async def load_data():
    try:
        dataset_dir = Path("data")
        csv_files = list(dataset_dir.glob("*.csv"))

        if not csv_files:
            raise FileNotFoundError("No CSV files found in data directory")

        csv_file = csv_files[0]

        controller.load_dataset(str(csv_file))
        print("Application ready.")

    except Exception as e:
        print(f"FATAL ERROR loading dataset: {e}")
        raise


@app.get("/")
async def root():
    return {
        "message": "IMDB Reviews API",
        "status": "online",
        "total_reviews": len(controller.reviews),
        "total_movies": len(controller.movies),
    }


@app.get("/reviews")
async def get_reviews(
    limit: int = Query(default=10, ge=1, le=100,
                     description="Number of reviews to return")
):
    reviews = controller.get_all_reviews(limit=limit)
    
    return {
        "count": len(reviews),
        "reviews": reviews
    }


# CRUD endpoints for reviews
@app.get("/reviews/{review_id}")
async def get_review(review_id: str):
    review = controller.get_review_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.post("/reviews", status_code=201)
async def create_review(review: ReviewCreate):
    try:
        new_review = controller.create_review(review.model_dump())
        return {"message": "Review created successfully", "review": new_review}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/reviews/{review_id}")
async def update_review(review_id: str, review_update: ReviewUpdate):
    update_data = review_update.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    updated_review = controller.update_review(review_id, update_data)
    if not updated_review:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review updated successfully", "review": updated_review}


@app.delete("/reviews/{review_id}")
async def delete_review(review_id: str):
    success = controller.delete_review(review_id)
    if not success:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": f"Review '{review_id}' deleted successfully"}
