class Movie:
    def __init__(
            self,
            movie_id,
            title,
            genre,
            release_year,
            director,
            cast,
            description):
        self.movie_id = movie_id
        self.title = title
        self.genre = genre
        self.release_year = release_year
        self.director = director
        self.cast = cast
        self.description = description
        self.reviews = []
        self.average_rating = 0.0
        self.total_reviews = 0

    def add_review(self, review):
        self.reviews.append(review)
        self.total_reviews = len(self.reviews)
        self.calculate_average_rating()

    def calculate_average_rating(self):
        if not self.reviews:
            self.average_rating = 0.0
            return

        ratings = [r.rating for r in self.reviews if r.rating > 0]
        self.average_rating = sum(ratings) / len(ratings) if ratings else 0.0

    def get_top_reviews(self, limit=10):
        sorted_reviews = sorted(
            self.reviews,
            key=lambda r: (r.rating, r.helpful_votes),
            reverse=True
        )
        return sorted_reviews[:limit]
