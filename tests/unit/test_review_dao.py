from ReviewDAO import ReviewDAO
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),
                                              '../../keyboard_smashers/DAO')))


class TestReviewDAO(unittest.TestCase):
    def setUp(self):
        patcher_read_csv = patch('pandas.read_csv', return_value=MagicMock())
        patcher_to_csv = patch('pandas.DataFrame.to_csv')
        self.mock_read_csv = patcher_read_csv.start()
        self.mock_to_csv = patcher_to_csv.start()
        self.addCleanup(patcher_read_csv.stop)
        self.addCleanup(patcher_to_csv.stop)
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


    def test_update_review(self):
        review_data = {
            'movie_id': 1,
            'user_id': 'test_user1',
            'rating': 5,
            'review_text': 'Excellent movie!',
            'review_date': '2024-01-01'
        }
        new_review = self.dao.create_review(review_data)
        updated_review = self.dao.update_review(new_review.review_id, 
                                                {'rating': 4})
        self.assertEqual(updated_review.rating, 4)


    def test_delete_review(self):
        review_data = {
            'movie_id': 1,
            'user_id': 'test_user2',
            'rating': 5,
            'review_text': 'Excellent movie!',
            'review_date': '2024-01-01'
        }
        new_review = self.dao.create_review(review_data)
        success = self.dao.delete_review(new_review.review_id)
        self.assertTrue(success)


    def test_get_review(self):
        review_data = {
            'movie_id': 1,
            'user_id': 'test_user3',
            'rating': 5,
            'review_text': 'Excellent movie!',
            'review_date': '2024-01-01'
        }
        new_review = self.dao.create_review(review_data)
        fetched_review = self.dao.get_review(new_review.review_id)
        self.assertIsNotNone(fetched_review)
        self.assertEqual(fetched_review.review_id, new_review.review_id)
        