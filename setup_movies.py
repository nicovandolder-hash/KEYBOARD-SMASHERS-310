import os
import pandas as pd

file_path = "data/movies.csv"
if not os.path.exists(file_path):
    movies = [
                {
                    "movie_id": 1,
                    "title": "Avengers Endgame",
                    "genre": "Action",
                    "director": "Anthony & Joe Russo",
                    "year": 2019
                },
                {
                    "movie_id": 2,
                    "title": "Inception",
                    "genre": "Sci-Fi",
                    "director": "Christopher Nolan",
                    "year": 2010
                },
                {
                    "movie_id": 3,
                    "title": "Joker",
                    "genre": "Thriller",
                    "director": "Todd Phillips",
                    "year": 2019
                },
                {
                    "movie_id": 4,
                    "title": "Interstellar",
                    "genre": "Sci-Fi",
                    "director": "Christopher Nolan",
                    "year": 2014
                },
                {
                    "movie_id": 5,
                    "title": "Parasite",
                    "genre": "Drama",
                    "director": "Bong Joon Ho",
                    "year": 2019
                },
                {
                    "movie_id": 6,
                    "title": "The Dark Knight",
                    "genre": "Action",
                    "director": "Christopher Nolan",
                    "year": 2008
                }
            ]

    df = pd.DataFrame(movies)
    df.to_csv(file_path, index=False)
    print("✅ movies.csv created successfully!")
else:
    print("⚠️ movies.csv already exists — no action taken.")
