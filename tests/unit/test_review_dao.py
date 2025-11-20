
from datetime import datetime
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
from keyboard_smashers.dao.review_dao import ReviewDAO


@pytest.fixture
def temp_csv_data():
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "test_reviews.csv")
    reviews = pd.DataFrame({
        'review_id': '1',
        'movie_id': '1',
        'user_id': '1',
        'rating': '4',
        'review_text': ['Great product!',
                        'Good value for money.', 'Average quality.'],
        'review_date': datetime.now().strftime('%Y-%m-%d')
    }, {
        'review_id': '2',
        'movie_id': '1',
        'user_id': '2',
        'rating': '4',
        'review_text': ['Great product!',
                        'Good value for money.', 'Average quality.'],
        'review_date': datetime.now().strftime('%Y-%m-%d')
    }, {
        'review_id': '3',
        'movie_id': '2',
        'user_id': '3',
        'rating': '5',
        'review_text': ['Great product!',
                        'Good value for money.', 'Average quality.'],
        'review_date': datetime.now().strftime('%Y-%m-%d')
    }, {
        'review_id': '4',
        'movie_id': '2',
        'user_id': '4',
        'rating': '3',
        'review_text': ['Great product!',
                        'Good value for money.', 'Average quality.'],
        'review_date': datetime.now().strftime('%Y-%m-%d')
    })
    reviews.to_csv(csv_path, index=False)
    yield csv_path

    if os.path.exists(csv_path):
        os.remove(csv_path)
    os.rmdir(temp_dir)


@pytest.fixture
class TestReviewDAO(unittest.TestCase):
    def setUp(self):
        patcher_read_csv = patch('pandas.read_csv', return_value=MagicMock())
        patcher_to_csv = patch('pandas.DataFrame.to_csv')
        self.mock_read_csv = patcher_read_csv.start()
        self.mock_to_csv = patcher_to_csv.start()
        self.addCleanup(patcher_read_csv.stop)
        self.addCleanup(patcher_to_csv.stop)
        self.dao = ReviewDAO(csv_path='tests/unit/test_reviews.csv')

    def test_create_review(self):
        review_data = {
            'movie_id': '1',
            'user_id': 'user6',
            'rating': 5,
            'review_text': 'Excellent movie!',
            'review_date': '2024-01-01'
        }
        new_review = self.dao.create_review(review_data)
        self.assertEqual(new_review['movie_id'], review_data['movie_id'])
        self.assertEqual(new_review['user_id'], review_data['user_id'])
        self.assertEqual(new_review['rating'], review_data['rating'])
        self.assertEqual(new_review['review_text'], review_data['review_text'])
        self.assertEqual(new_review['review_date'], '2024-01-01T00:00:00')

    def test_update_review(self):
        updated_review = self.dao.update_review('1', {'rating': 4})
        self.assertEqual(updated_review['rating'], 5)

    def test_delete_review(self):
        success = self.dao.delete_review('4')
        self.assertTrue(success)

    def test_get_review(self):
        fetched_review = self.dao.get_review('1')
        self.assertIsNotNone(fetched_review)
        self.assertEqual(fetched_review['review_id'], '1')

    def test_get_review_by_movie(self):
        reviews = self.dao.get_review_for_movie('2')
        self.assertTrue(isinstance(reviews, list))
        self.assertEqual(len(reviews), 2)
        for review in reviews:
            self.assertEqual(review['movie_id'], '2')
