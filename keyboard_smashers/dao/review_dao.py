import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class ReviewDAO:
    def __init__(self, csv_path: str = 'data/imdb_reviews.csv'):
        self.csv_path = csv_path
        self.reviews: Dict[str, dict] = {}
        logging.info(f"Initializing review_dao with csv_path={csv_path}")
        self.load_reviews()

    def load_reviews(self) -> None:
        path = Path(self.csv_path)
        if path.exists():
            df = pd.read_csv(self.csv_path)

            # Map columns to expected names
            column_mapping = {
                'Date of Review': 'review_date',
                'User': 'user_id',
                "User's Rating out of 10": 'rating',
                'Review': 'review_text',
                'movie': 'movie_id'
            }
            df.rename(columns=column_mapping, inplace=True)

            count = 0

            # Ensure 'review_id' column exists
            if 'review_id' not in df.columns:
                logging.warning("'review_id' column missing. "
                                "Generating unique IDs.")
                df['review_id'] = range(1, len(df) + 1)

            # Clean the 'rating' column in bulk
            df['rating'] = pd.to_numeric(df['rating'],
                                         errors='coerce').fillna(0).astype(int)

            for _, row in df.iterrows():
                # Check if 'review_date' column exists
                review_date = row['review_date'] if (
                    'review_date' in row)else None
                if pd.notnull(review_date):
                    try:
                        dt = pd.to_datetime(review_date)
                        review_date = dt.isoformat()
                    except Exception:
                        review_date = str(review_date)
                else:
                    review_date = ""

                review = {
                    'review_id': str(row['review_id']),
                    'movie_id': str(row['movie_id']),
                    'user_id': row['user_id'],
                    'rating': row['rating'],
                    'review_text': row['review_text'],
                    'review_date': review_date,
                }
                self.reviews[review['review_id']] = review
                count += 1
            logging.info(f"Loaded {count} reviews from {self.csv_path}")
        else:
            logging.warning(f"No review data found at {self.csv_path}"
                            ". Please ensure the file exists.")

    def save_reviews(self) -> None:
        data = list(self.reviews.values())
        df = pd.DataFrame(data)
        Path(self.csv_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.csv_path, index=False)
        logging.info(f"Saved {len(data)} reviews to {self.csv_path}")

    def create_review(self, review_data: Dict) -> dict:
        existing_ids = [int(rid) for rid in self.reviews.keys()
                        if str(rid).isdigit()]
        review_id = str(max(existing_ids, default=0) + 1)
        review_date = review_data.get('review_date')
        if review_date:
            try:
                dt = pd.to_datetime(review_date)
                review_date = dt.isoformat()
            except Exception:
                review_date = str(review_date)
        else:
            review_date = datetime.now().isoformat()
        new_review = {
            'review_id': review_id,
            'movie_id': str(review_data['movie_id']),
            'user_id': review_data['user_id'],
            'rating': int(review_data['rating']),
            'review_text': review_data.get('review_text', ''),
            'review_date': review_date,
        }
        self.reviews[review_id] = new_review
        self.save_reviews()
        logging.info(f"Created review {review_id} for movie "
                     f"{new_review['movie_id']}")
        return new_review

    def get_review_by_id(self, review_id: str) -> Optional[dict]:
        review = self.reviews.get(str(review_id))
        if review:
            logging.info(f"Fetched review {review_id}")
        else:
            logging.warning(f"Review {review_id} not found")
        return review

    def get_review_for_movie(self, movie_id: str) -> List[dict]:
        reviews = [r for r in self.reviews.values()
                   if r['movie_id'] == str(movie_id)]
        logging.info(f"Fetched {len(reviews)} reviews for movie {movie_id}")
        return reviews

    def update_review_by_id(self, review_id: str,
                            data: Dict) -> Optional[dict]:
        review = self.reviews.get(str(review_id))
        if not review:
            logging.warning(f"Review {review_id} not found for update")
            return None
        for key, value in data.items():
            if key == 'review_date' and value:
                try:
                    dt = pd.to_datetime(value)
                    value = dt.isoformat()
                except Exception:
                    value = str(value)
            if key in review:
                review[key] = value
        self.save_reviews()
        logging.info(f"Updated review {review_id}")
        return review

    def delete_review_by_id(self, review_id: str) -> bool:
        if str(review_id) in self.reviews:
            del self.reviews[str(review_id)]
            self.save_reviews()
            logging.info(f"Deleted review {review_id}")
            return True
        logging.warning(f"Review {review_id} not found for deletion")
        return False
