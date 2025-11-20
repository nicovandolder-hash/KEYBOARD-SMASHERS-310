from fastapi import FastAPI
from pathlib import Path
from keyboard_smashers.logging_config import setup_logging
from keyboard_smashers.controllers.review_controller import (
     router as review_router, review_controller_instance
)
from keyboard_smashers.controllers.user_controller import (
     router as user_router, user_controller_instance
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


@app.on_event("startup")
async def load_data():
    try:
        logger.info("Starting up and loading dataset...")
        dataset_dir = Path("data")

        # Load users
        user_csv = dataset_dir / "users.csv"
        if user_csv.exists():
            logger.info(f"Loading users from: {user_csv}")
            logger.info(f"Loaded "
                        f"{len(user_controller_instance.user_dao.users)}"
                        f"users.")
        else:
            logger.warning(f"Warning: User CSV not found at {user_csv}")

        # Load movies
        movie_csv = dataset_dir / "movies.csv"
        if movie_csv.exists():
            logger.info(f"Movies loaded from: {movie_csv}")
            logger.info(
                f"Loaded {len(movie_controller_instance.movie_dao.movies)}"
                f" movies."
            )
        else:
            logger.warning(f"Warning: Movie CSV not found at {movie_csv}")

        # Load reviews
        csv_files = list(dataset_dir.glob("*.csv"))
        review_csv_files = [
            f for f in csv_files
            if f.name not in ["users.csv", "movies.csv"]
        ]

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
        logger.error(f"ERROR loading dataset: {e}")
        raise


@app.on_event("shutdown")
async def save_data():
    try:
        logger.info("Shutting down and saving user data...")
        dataset_dir = Path("data")
        user_csv = dataset_dir / "users.csv"
        user_controller_instance.save_users_to_csv(str(user_csv))
        logger.info("User data saved successfully.")
    except Exception as e:
        logger.error(f"Error saving user data: {e}")


@app.get("/")
async def root():
    return {
        "message": "IMDB Reviews API",
        "status": "online",
        "total_reviews": len(review_controller_instance.reviews),
        "total_movies": (
            len(review_controller_instance.movies) +
            len(movie_controller_instance.movie_dao.movies)
        ),
        "total_users": len(user_controller_instance.users),
    }
