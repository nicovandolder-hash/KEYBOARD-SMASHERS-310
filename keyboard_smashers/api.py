from fastapi import FastAPI, Query
from pathlib import Path
from keyboard_smashers.controllers.review_controller import ReviewController

app = FastAPI(title="IMDB Reviews API")

controller = ReviewController()


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
    limit: int = Query(
        default=10, ge=1, le=100,
        description="Number of reviews to return"
    )
):
    reviews = controller.get_all_reviews(limit=limit)

    return {
        "count": len(reviews),
        "reviews": reviews
    }
