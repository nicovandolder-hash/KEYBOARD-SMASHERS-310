import os
import pandas as pd
from datetime import datetime

file_path = 'data/reviews.csv'

if not os.path.exists(file_path):
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
    df = pd.DataFrame(reviews)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_csv(file_path, index=False)
    print(f"Sample review data created at {file_path}")
else:
    print(f"Review data already exists at {file_path}")
