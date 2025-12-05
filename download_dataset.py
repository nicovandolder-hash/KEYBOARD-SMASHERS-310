import kagglehub  # noqa: F401
from pathlib import Path
import pandas as pd

print("Downloading IMDB dataset...")
dataset_path = kagglehub.dataset_download("sadmadlad/imdb-user-reviews")
print(f"Downloaded to: {dataset_path}")

# Create data directory
local_data_dir = Path("data")
local_data_dir.mkdir(exist_ok=True)

# Collect all CSV files from movie folders
dataset_dir = Path(dataset_path)
all_reviews = []

print("\nProcessing movie folders:")
for movie_folder in dataset_dir.iterdir():
    if movie_folder.is_dir():
        csv_file = movie_folder / "movieReviews.csv"
        if csv_file.exists():
            print(f"  Reading {movie_folder.name}...")
            df = pd.read_csv(csv_file)
            df['movie'] = movie_folder.name  # Add movie name column
            all_reviews.append(df)

# Combine all reviews into one DataFrame
if all_reviews:
    combined_df = pd.concat(all_reviews, ignore_index=True)
    output_file = local_data_dir / "imdb_reviews.csv"
    combined_df.to_csv(output_file, index=False)
    print(f"\nCombined {len(all_reviews)} movies into: {output_file}")
    print(f"Total reviews: {len(combined_df)}")
    print(f"Columns: {list(combined_df.columns)}")
else:
    print("\nNo CSV files found!")
