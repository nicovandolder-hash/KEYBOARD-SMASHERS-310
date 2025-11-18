import os
import pandas as pd
from datetime import datetime

file_path = 'data/reviews.csv'

if not os.path.exists(file_path):
    reviews = {
        'review_id': [1, 2, 3],
        'moview_id': [1, 2, 3],
        'user_id': ['u1', 'u2', 'u3'],
        'rating': [5, 4, 3],
        'review_text': ['Great product!',
                        'Good value for money.', 'Average quality.'],
        'review_date': [datetime.now().strftime('%Y-%m-%d')] * 3
    }
    df = pd.DataFrame(reviews)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_csv(file_path, index=False)
    print(f"Sample review data created at {file_path}")
else:
    print(f"Review data already exists at {file_path}")
