import os
import pandas as pd

reviews_file = "data/imdb_reviews.csv"
movies_file = "data/movies.csv"

if not os.path.exists(movies_file):
    print("📖 Reading IMDB reviews to extract unique movies...")

    # Read the IMDB reviews CSV
    df_reviews = pd.read_csv(reviews_file)

    # Extract unique movie titles from the 'movie' column
    unique_movies = df_reviews['movie'].unique()

    print(f"✅ Found {len(unique_movies)} unique movies")

    # Create movie records with auto-generated IDs
    movies = []
    for idx, movie_title in enumerate(unique_movies, start=1):
        movies.append({
            "movie_id": idx,
            "title": movie_title,
            "genre": "",  # Empty - can be populated later
            "director": "",  # Empty - can be populated later
            "year": 0  # Default - can be populated later
        })

    # Save to CSV
    df_movies = pd.DataFrame(movies)
    df_movies.to_csv(movies_file, index=False)
    print(f"✅ movies.csv created with {len(movies)} movies!")
else:
    print("⚠️ movies.csv already exists — no action taken.")
