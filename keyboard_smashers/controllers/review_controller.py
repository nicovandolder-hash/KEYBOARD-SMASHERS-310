import pandas as pd
from typing import List
from keyboard_smashers.models.review_model import Review
from keyboard_smashers.models.movie_model import Movie


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
    
    def _review_to_dict(self, review: Review) -> dict:
        movie = self.movies_by_id.get(review.movie_id)
        movie_title = movie.title if movie else "Unknown Movie"
        
        return {
            "review_id": review.review_id,
            "user_id": review.user_id,
            "movie_id": review.movie_id,
            "movie_title": movie_title, # <-- ADDED MOVIE TITLE HERE
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