from fastapi import FastAPI
from pathlib import Path
from keyboard_smashers.logging_config import setup_logging
from keyboard_smashers.controllers.review_controller import (
     router as review_router, review_controller_instance
)

import logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="IMDB Reviews API")

app.include_router(review_router)


@app.on_event("startup")
async def load_data():
    try:
        logger.info("Starting up and loading dataset...")
        dataset_dir = Path("data")

        # Load reviews from imdb_reviews.csv
        review_csv = dataset_dir / "imdb_reviews.csv"
        if not review_csv.exists():
            logger.error("imdb_reviews.csv file not found in data directory")
            raise FileNotFoundError("imdb_reviews.csv file not found in data directory")

        logger.info(f"Loading reviews from: {review_csv}")
        review_controller_instance.review_dao.load_reviews()
        logger.info(
            f"Loaded {len(review_controller_instance.get_all_reviews())} reviews."
        )
        logger.info("Application ready.")

    except Exception as e:
        logger.error(f"ERROR loading dataset: {e}")
        raise


@app.on_event("shutdown")
async def save_data():
    try:
        logger.info("Shutting down and saving review data...")
        # Add any review-specific save logic here if needed
        logger.info("Review data saved successfully.")
    except Exception as e:
        logger.error(f"Error saving review data: {e}")


@app.get("/")
async def root():
    return {
        "message": "IMDB Reviews API",
        "status": "online",
        "total_reviews": len(review_controller_instance.reviews),
    }
