import unittest
from review_dao import ReviewDAO


class TestReviewDAO(unittest.TestCase):
    def setUp(self):
        self.dao = ReviewDAO(csv_path='tests/unit/test_reviews.csv')
        # Start with a clean slate for each test
        self.dao.reviews = {}
    
    def test_create_review(self):
        review_data = {
            'movie_id': 1,
            'user_id': 'test_user',
            'rating': 5,
            'review_text': 'Excellent movie!',
            'review_date': '2024-01-01'
        }
        new_review = self.dao.create_review(review_data)
        self.assertEqual(new_review.movie_id, review_data['movie_id'])
        self.assertEqual(new_review.user_id, review_data['user_id'])
        self.assertEqual(new_review.rating, review_data['rating'])
        self.assertEqual(new_review.review_text, review_data['review_text'])
        self.assertEqual(new_review.review_date, review_data['review_date'])
        self.assertIn(new_review.review_id, self.dao.reviews)