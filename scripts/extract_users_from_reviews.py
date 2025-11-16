import csv
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_users_from_reviews(input_file: Path, output_file: Path):

    try:

        BASE_DIR = Path(__file__).resolve().parent.parent
        DATA_DIR = BASE_DIR / "data"
        transferring_users = set()
        users_file = DATA_DIR / "users.csv"
        review_file = DATA_DIR / "imdb_reviews.csv"

        if users_file.exists():
            logger.info(f"Reading existing users from {users_file}")
            with open(users_file, mode='r', encoding='utf-8') as uf:
                reader = csv.reader(uf)
                for row in reader:
                    if row:
                        transferring_users.add(row[1])
            logger.info(f"Loaded {len(transferring_users)} existing users.")
        logger.info(f"Reading reviews from {review_file}")
        unique_users = {}
        user_review_count = {}
        with open(review_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                username = row.get('User', 'anonymous').strip()

                if username and username not in transferring_users:
                    if username not in unique_users:
                        unique_users[username] = {
                            'first_review_date': row.get('Date of Review',
                                                         ''),
                            'rating': row.get("User's Rating out of 10", 0)
                        }
                        user_review_count[username] = 1
                    else:
                        user_review_count[username] += 1

        logger.info(f"Found {len(unique_users)} new unique users from reviews")

        new_users = []
        user_counter = 1

        if users_file.exists():
            with open(users_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['userid'].startswith('user_'):
                        try:
                            user_num = int(row['userid'].split('_')[1])
                            user_counter = max(user_counter, user_num + 1)
                        except (IndexError, ValueError):
                            pass

        for username, details in unique_users.items():
            user_id = f"user_{user_counter:03d}"

            try:
                review_date = datetime.strptime(details['first_review_date'],
                                                '%d %B %Y')
            except Exception:
                review_date = datetime.now()

            total_reviews = user_review_count[username]
            reputation = min(3 + (total_reviews // 5), 10)

            new_user = {
                'userid': user_id,
                'username': username,
                'email': f"{username.lower().replace(' ', '_')}@ubc.stu.ca",
                'password': user_id + 'Default123!',
                'reputation': reputation,
                'creation_date': review_date.isoformat(),
                'is_admin': 'false',
                'total_reviews': total_reviews
            }

            new_users.append(new_user)
            user_counter += 1

        if new_users:
            logger.info(f"Adding {len(new_users)} new users to {users_file}")

            existing_rows = []
            if users_file.exists():
                with open(users_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    existing_rows = list(reader)

            with open(users_file, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ['userid', 'username', 'email', 'password',
                              'reputation',
                              'creation_date', 'is_admin', 'total_reviews']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for row in existing_rows:
                    writer.writerow(row)

                for user in new_users:
                    writer.writerow(user)

            logger.info(f"Successfully added {len(new_users)} new users!")
        else:
            logger.info("All reviewers are already in users file.")

        return len(new_users)

    except Exception as e:
        logger.error(f"Error extracting users: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    reviews_csv = "data/IMDB_reviews.csv"
    users_csv = "data/users.csv"

    new_user_count = extract_users_from_reviews(reviews_csv, users_csv)
    print(f"\n{'='*60}")
    print(f"Extraction complete! Added {new_user_count} new users.")
    print(f"{'='*60}\n")
