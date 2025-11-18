import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class Review:
    def __init__(
        self,
        review_id: int,
        movie_id: int,
        user_id: str,
        rating: int,
        review_text: str,
        review_date: datetime
    ):
        self.review_id = review_id
        self.movie_id = movie_id
        self.user_id = user_id
        self.rating = rating
        self.review_text = review_text
        self.review_date = review_date


class ReviewDAO:
    def __init__(self, csv_path: str = 'data/reviews.csv'):
        self.csv_path = csv_path
        self.reviews: Dict[str, Review] = {}
        self.load_reviews()

    def load_reviews(self) -> None:
        path = Path(self.csv_path)
        if path.exists():
            df = pd.read_csv(self.csv_path)
            for _, row in df.iterrows():
                review = Review(
                    review_id=row['review_id'],
                    movie_id=row['movie_id'],
                    user_id=row['user_id'],
                    rating=row['rating'],
                    review_text=row['review_text'],
                    review_date=datetime.strptime(
                        row['review_date'], '%Y-%m-%d'
                    )
                )
                self.reviews[review.review_id] = review
        else:
            print(
                f"No review data found at {self.csv_path}. "
                "Please ensure the file exists."
            )

    def save_reviews(self) -> None:
        data = [
            {
                'review_id': r.review_id,
                'movie_id': r.movie_id,
                'user_id': r.user_id,
                'rating': r.rating,
                'review_text': r.review_text,
                'review_date': r.review_date
            }
            for r in self.reviews.values()
        ]
        df = pd.DataFrame(data)
        Path(self.csv_path).parent.mkdir(parents=True,
                                         exist_ok=True)
        df.to_csv(self.csv_path, index=False)

    def create_review(self, review_data: Dict) -> Review:
        existing_ids = [int(rid) for rid in self.reviews.keys()
                        if str(rid).isdigit()]
        review_id = max(existing_ids, default=0) + 1
        new_review = Review(
            review_id,
            review_data['movie_id'],
            review_data['user_id'],
            int(review_data['rating']),
            review_data.get('review_text', ''),
            review_data.get('review_date', datetime.now().isoformat())
        )
        self.reviews[review_id] = new_review
        self.save_reviews()
        return new_review

    def get_review(self, review_id: str) -> Optional[Review]:
        return self.reviews.get(review_id)

    def get_review_for_movie(self, movie_id: str) -> List[Review]:
        return [r for r in self.reviews.values() if r.movie_id == movie_id]

    def update_review(self, review_id: str, data: Dict) -> Optional[Review]:
        review = self.reviews.get(review_id)
        if not review:
            return None
        for key, value in data.items():
            if hasattr(review, key):
                setattr(review, key, value)
        self.save_reviews()
        return review

    def delete_review(self, review_id: str) -> bool:
        if review_id in self.reviews:
            del self.reviews[review_id]
            self.save_reviews()
            return True
        return False
