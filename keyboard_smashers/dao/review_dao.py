import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class ReviewDAO:

    def __init__(self, imdb_csv_path: str = "data/imdb_reviews.csv",
                 new_reviews_csv_path: str = "data/reviews_new.csv"):
        self.imdb_csv_path = imdb_csv_path
        self.new_reviews_csv_path = new_reviews_csv_path
        self.reviews: Dict[str, Dict[str, Any]] = {}
        # Indexed lookups for fast filtering
        self.reviews_by_movie: Dict[str, List[str]] = {}
        self.reviews_by_user: Dict[str, List[str]] = {}
        # Thread safety lock for concurrent operations
        self._lock = Lock()
        # Cached max review ID (initialized after loading)
        self._max_review_id = 0
        # Operation counter for auto-compaction
        self._operation_count = 0
        self._compact_threshold = 100  # Compact after this many operations
        self._load_reviews()
        # Compact on startup if file exists
        self._maybe_compact_on_startup()
        logger.info(f"ReviewDAO initialized with {len(self.reviews)} reviews")

    def _load_reviews(self) -> None:
        # Build movie title to ID mapping
        movie_title_to_id = {}
        movies_csv_path = 'data/movies.csv'
        if Path(movies_csv_path).exists():
            movies_df = pd.read_csv(movies_csv_path)
            for _, movie_row in movies_df.iterrows():
                title = str(movie_row.get('title', '')).strip()
                movie_id = str(movie_row.get('movie_id', ''))
                movie_title_to_id[title] = movie_id

        # Load original IMDB reviews (read-only)
        if Path(self.imdb_csv_path).exists():
            df = pd.read_csv(self.imdb_csv_path)

            for idx, row in df.iterrows():
                # Generate sequential review IDs
                review_id = f"review_{str(idx).zfill(6)}"

                # Extract rating (convert from 0-10 to 1-5 scale)
                raw_rating = row.get("User's Rating out of 10", 0)
                if pd.notna(raw_rating):
                    try:
                        rating = max(1, min(5, round(float(raw_rating) / 2)))
                    except (ValueError, TypeError):
                        rating = 3
                else:
                    rating = 3

                # Truncate review text to 250 chars if needed
                review_text = str(row.get('Review', ''))[
                    :250] if pd.notna(row.get('Review')) else ''

                # Map movie title to numeric ID
                movie_title = str(row.get('movie', '')).strip()
                movie_id = movie_title_to_id.get(
                    movie_title, movie_title)  # Fallback to title if not found

                review_dict = {
                    'review_id': review_id,
                    'movie_id': movie_id,
                    'user_id': None,  # Legacy IMDB reviews
                    'imdb_username': (
                        str(row.get('User', ''))
                        if pd.notna(row.get('User')) else ''
                    ),
                    'rating': rating,
                    'review_text': review_text,
                    'review_date': (
                        str(row.get('Date of Review', ''))
                        if pd.notna(row.get('Date of Review')) else ''
                    )
                }

                self._add_review_to_indexes(review_id, review_dict)

        # Load new reviews from users (append-only file)
        if Path(self.new_reviews_csv_path).exists():
            df = pd.read_csv(self.new_reviews_csv_path)

            for _, row in df.iterrows():
                review_id = str(row['review_id'])
                operation = row.get('operation', 'create')

                if operation == 'delete':
                    # Remove from memory
                    self._remove_review_from_indexes(review_id)
                else:
                    # Create or update (latest entry wins)
                    user_id_val = row.get('user_id')
                    imdb_user_val = row.get('imdb_username')

                    review_dict = {
                        'review_id': review_id,
                        'movie_id': str(row.get('movie_id', '')),
                        'user_id': (
                            str(user_id_val)
                            if pd.notna(user_id_val) else None
                        ),
                        'imdb_username': (
                            str(imdb_user_val)
                            if pd.notna(imdb_user_val) else None
                        ),
                        'rating': int(row.get('rating', 3)),
                        'review_text': str(row.get('review_text', '')),
                        'review_date': str(row.get('review_date', ''))
                    }
                    self._add_review_to_indexes(review_id, review_dict)

        # Initialize cached max review ID
        self._initialize_max_review_id()

    def _initialize_max_review_id(self) -> None:
        """Initialize the max review ID counter from existing reviews"""
        existing_ids = [
            int(rid.replace('review_', ''))
            for rid in self.reviews.keys()
            if rid.startswith('review_')
        ]
        self._max_review_id = max(existing_ids) if existing_ids else 0

    def _maybe_compact_on_startup(self) -> None:
        """Compact reviews file on startup if it has grown large"""
        if not Path(self.new_reviews_csv_path).exists():
            return
        try:
            df = pd.read_csv(self.new_reviews_csv_path)
            if len(df) > self._compact_threshold:
                logger.info(
                    f"Compacting reviews on startup ({len(df)} operations)")
                self.compact_reviews()
        except Exception as e:
            logger.warning(f"Failed to check/compact on startup: {e}")

    def _maybe_compact(self) -> None:
        """Trigger compaction if operation threshold is reached"""
        self._operation_count += 1
        if self._operation_count >= self._compact_threshold:
            logger.info(
                f"Auto-compacting after {self._operation_count} operations")
            self.compact_reviews()
            self._operation_count = 0

    def _add_review_to_indexes(
            self, review_id: str, review_dict: Dict[str, Any]) -> None:
        """Add or update a review in memory and indexes"""
        # Add to main dictionary
        self.reviews[review_id] = review_dict

        # Build movie index
        movie_id = review_dict['movie_id']
        if movie_id not in self.reviews_by_movie:
            self.reviews_by_movie[movie_id] = []
        if review_id not in self.reviews_by_movie[movie_id]:
            self.reviews_by_movie[movie_id].append(review_id)

        # Build user index if user_id present
        user_id = review_dict.get('user_id')
        if user_id:
            if user_id not in self.reviews_by_user:
                self.reviews_by_user[user_id] = []
            if review_id not in self.reviews_by_user[user_id]:
                self.reviews_by_user[user_id].append(review_id)

    def _remove_review_from_indexes(self, review_id: str) -> None:
        """Remove a review from memory and indexes"""
        if review_id not in self.reviews:
            return

        review = self.reviews[review_id]
        movie_id = review['movie_id']
        user_id = review.get('user_id')

        # Remove from indexes
        movie_reviews = self.reviews_by_movie.get(movie_id, [])
        if review_id in movie_reviews:
            movie_reviews.remove(review_id)
            if not movie_reviews:
                del self.reviews_by_movie[movie_id]

        if user_id:
            user_reviews = self.reviews_by_user.get(user_id, [])
            if review_id in user_reviews:
                user_reviews.remove(review_id)
                if not user_reviews:
                    del self.reviews_by_user[user_id]

        del self.reviews[review_id]

    def _append_review(self,
                       review_dict: Dict[str,
                                         Any],
                       operation: str = 'create') -> None:
        """Append a review operation to the new reviews file"""
        Path(
            self.new_reviews_csv_path).parent.mkdir(
            parents=True,
            exist_ok=True)

        # Prepare row with operation marker
        row_data = {
            'operation': operation,
            'review_id': review_dict['review_id'],
            'movie_id': review_dict['movie_id'],
            'user_id': review_dict.get('user_id', ''),
            'imdb_username': review_dict.get('imdb_username', ''),
            'rating': review_dict['rating'],
            'review_text': review_dict['review_text'],
            'review_date': review_dict['review_date']
        }

        df = pd.DataFrame([row_data])

        # Append to CSV
        if Path(self.new_reviews_csv_path).exists():
            df.to_csv(
                self.new_reviews_csv_path,
                mode='a',
                header=False,
                index=False)
        else:
            df.to_csv(
                self.new_reviews_csv_path,
                mode='w',
                header=True,
                index=False)

    def create_review(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            # Check for duplicate: one review per user per movie
            movie_id = review_data.get('movie_id')
            user_id = review_data.get('user_id')

            if user_id and user_id in self.reviews_by_user:
                # Check if user already reviewed this movie (direct index
                # lookup)
                for review_id in self.reviews_by_user[user_id]:
                    # Only check if review still exists (not deleted)
                    existing_review = self.reviews.get(review_id)
                    if (existing_review and
                            existing_review['movie_id'] == movie_id):
                        raise ValueError(
                            f"User {user_id} already reviewed movie "
                            f"{movie_id}"
                        )

            # Auto-generate review_id using cached counter
            self._max_review_id += 1
            review_id = f"review_{str(self._max_review_id).zfill(6)}"

            new_review = {
                'review_id': review_id,
                'movie_id': str(
                    review_data.get(
                        'movie_id',
                        '')),
                'user_id': review_data.get('user_id'),
                'imdb_username': review_data.get('imdb_username'),
                'rating': review_data.get(
                    'rating',
                    3),
                'review_text': review_data.get(
                    'review_text',
                    ''),
                'review_date': review_data.get(
                    'review_date',
                    datetime.now().isoformat())}

            # Add to memory and indexes
            self._add_review_to_indexes(review_id, new_review)

            # Append to file
            self._append_review(new_review, operation='create')

            # Check if compaction needed
            self._maybe_compact()
            return new_review

    def get_review(self, review_id: str) -> Dict[str, Any]:
        if review_id not in self.reviews:
            raise KeyError(f"Review with id {review_id} not found")
        return self.reviews[review_id].copy()

    def get_reviews_for_movie(self, movie_id: str) -> List[Dict[str, Any]]:
        """Get all reviews for a specific movie"""
        review_ids = self.reviews_by_movie.get(movie_id, [])
        return [self.reviews[rid].copy() for rid in review_ids]

    def get_reviews_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all reviews by a specific user"""
        review_ids = self.reviews_by_user.get(user_id, [])
        return [self.reviews[rid].copy() for rid in review_ids]

    def update_review(self,
                      review_id: str,
                      update_data: Dict[str,
                                        Any]) -> Dict[str,
                                                      Any]:
        with self._lock:
            if review_id not in self.reviews:
                raise KeyError(f"Review with id {review_id} not found")

            review = self.reviews[review_id]

            # Update only provided fields
            if 'rating' in update_data:
                review['rating'] = update_data['rating']
            if 'review_text' in update_data:
                # Enforce 250 char limit
                review['review_text'] = update_data['review_text'][:250]
            if 'review_date' in update_data:
                review['review_date'] = update_data['review_date']

            # Append update to file
            self._append_review(review, operation='update')

            # Check if compaction needed
            self._maybe_compact()
            return review.copy()

    def delete_review(self, review_id: str) -> None:
        with self._lock:
            if review_id not in self.reviews:
                raise KeyError(f"Review with id {review_id} not found")

            review = self.reviews[review_id].copy()

            # Remove from indexes and memory
            self._remove_review_from_indexes(review_id)

            # Append deletion marker to file
            self._append_review(review, operation='delete')

            # Check if compaction needed
            self._maybe_compact()

    def compact_reviews(self) -> int:
        """
        Compact the reviews_new.csv file by removing old operations.
        Only keeps the latest state of each review.
        Returns the number of operations removed.
        """
        with self._lock:
            if not Path(self.new_reviews_csv_path).exists():
                logger.info("No reviews file to compact")
                return 0

            # Read current append-only file
            df = pd.read_csv(self.new_reviews_csv_path)
            original_size = len(df)

            # Get only user-created reviews (not IMDB legacy ones)
            user_reviews = {
                rid: review for rid, review in self.reviews.items()
                if review.get('user_id') is not None
            }

            if not user_reviews:
                logger.info("No user reviews to compact")
                return 0

            # Create new dataframe with only current state
            compacted_data = []
            for review_id, review in user_reviews.items():
                compacted_data.append({
                    # All treated as creates after compaction
                    'operation': 'create',
                    'review_id': review['review_id'],
                    'movie_id': review['movie_id'],
                    'user_id': review.get('user_id', ''),
                    'imdb_username': review.get('imdb_username', ''),
                    'rating': review['rating'],
                    'review_text': review['review_text'],
                    'review_date': review['review_date']
                })

            # Write compacted file
            df_compacted = pd.DataFrame(compacted_data)
            df_compacted.to_csv(self.new_reviews_csv_path, index=False)

            operations_removed = original_size - len(df_compacted)
            logger.info(
                f"Compacted reviews: removed {operations_removed} "
                f"operations, kept {len(df_compacted)} current reviews"
            )
            return operations_removed

    def delete_reviews_by_movie(self, movie_id: str) -> int:
        """
        Delete all user-created reviews for a specific movie.
        Does not delete IMDB legacy reviews (those without user_id).
        Returns the number of reviews deleted.
        """
        with self._lock:
            movie_id = str(movie_id)
            review_ids = self.reviews_by_movie.get(movie_id, []).copy()
            deleted_count = 0

            for review_id in review_ids:
                review = self.reviews.get(review_id)
                if review and review.get('user_id') is not None:
                    # Only delete user-created reviews
                    self._remove_review_from_indexes(review_id)
                    self._append_review(review, operation='delete')
                    deleted_count += 1

            if deleted_count > 0:
                self._maybe_compact()
                logger.info(
                    f"Deleted {deleted_count} reviews for movie {movie_id}"
                )

            return deleted_count


# Global shared instance
review_dao_instance = ReviewDAO()
