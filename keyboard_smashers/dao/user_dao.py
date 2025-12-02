import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class UserDAO:

    def __init__(self, csv_path: str = "data/users.csv"):
        self.csv_path = csv_path
        self.users: Dict[str, Dict[str, Any]] = {}
        self.email_index: Dict[str, str] = {}
        self.username_index: Dict[str, str] = {}
        self.user_counter = 1
        self.load_users()

    def load_users(self) -> None:
        csv_file = Path(self.csv_path)
        if not csv_file.exists():
            logger.warning(f"User CSV file not found at: {self.csv_path}")
            return

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    creation_date = (
                        datetime.fromisoformat(row['creation_date'])
                        if row.get('creation_date')
                        else datetime.now()
                    )

                    user_dict = {
                        'userid': row['userid'],
                        'username': row['username'],
                        'email': row['email'],
                        'password': row.get('password', ''),
                        'reputation': int(row.get('reputation', 3)),
                        'creation_date': creation_date,
                        'is_admin': (
                            row.get('is_admin', 'false').lower() ==
                            'true'
                        ),
                        'is_suspended': (
                            row.get('is_suspended', 'false').lower() ==
                            'true'
                        ),
                        'total_reviews': int(row.get('total_reviews', 0)),
                        'total_penalty_count': int(
                            row.get('total_penalty_count', 0)
                        )
                    }

                    self.users[user_dict['userid']] = user_dict
                    self.email_index[user_dict['email'].lower()] = (
                        user_dict['userid']
                    )
                    self.username_index[user_dict['username'].lower()] = (
                        user_dict['userid']
                    )

                    if user_dict['userid'].startswith("user_"):
                        try:
                            user_num = int(user_dict['userid'].split("_")[1])
                            self.user_counter = (
                                 max(self.user_counter, user_num + 1)
                            )
                        except (IndexError, ValueError):
                            pass

            logger.info(f"Loaded {len(self.users)} users from {self.csv_path}")
        except Exception as e:
            logger.error(f"Error loading users from {self.csv_path}: {e}")
            raise

    def save_users(self) -> None:
        try:
            csv_file = Path(self.csv_path)
            csv_file.parent.mkdir(parents=True, exist_ok=True)

            with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                fieldnames = [
                    'userid',
                    'username',
                    'email',
                    'password',
                    'reputation',
                    'creation_date',
                    'is_admin',
                    'is_suspended',
                    'total_reviews',
                    'total_penalty_count'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for user in self.users.values():
                    writer.writerow({
                        'userid': user['userid'],
                        'username': user['username'],
                        'email': user['email'],
                        'password': user['password'],
                        'reputation': user['reputation'],
                        'creation_date': (
                            user['creation_date'].isoformat()
                        ),
                        'is_admin': str(user['is_admin']).lower(),
                        'is_suspended': (
                            str(user.get('is_suspended', False)).lower()
                        ),
                        'total_reviews': user['total_reviews'],
                        'total_penalty_count': (
                            user.get('total_penalty_count', 0)
                        )
                    })

            logger.info(f"Saved {len(self.users)} users to {self.csv_path}")
        except Exception as e:
            logger.error(f"Error saving users to CSV: {e}")
            raise

    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        email_lower = user_data['email'].lower()
        if email_lower in self.email_index:
            raise ValueError(f"Email '{user_data['email']}'"
                             f" already registered")

        username_lower = user_data['username'].lower()
        if username_lower in self.username_index:
            raise ValueError(f"Username '{user_data['username']}'"
                             f" already taken")

        user_id = f"user_{self.user_counter:03d}"
        self.user_counter += 1

        user_dict = {
            'userid': user_id,
            'username': user_data['username'],
            'email': user_data['email'],
            'password': user_data.get('password', ''),
            'reputation': user_data.get('reputation', 3),
            'creation_date': user_data.get('creation_date', datetime.now()),
            'is_admin': user_data.get('is_admin', False),
            'is_suspended': user_data.get('is_suspended', False),
            'total_reviews': 0,
            'total_penalty_count': 0
        }

        self.users[user_id] = user_dict
        self.email_index[email_lower] = user_id
        self.username_index[username_lower] = user_id
        self.save_users()

        logger.info(f"Created user: {user_id} - {user_data['username']}")
        return user_dict.copy()

    def get_user(self, userid: str) -> Dict[str, Any]:
        if userid not in self.users:
            raise KeyError(f"User with ID '{userid}' not found")
        return self.users[userid].copy()

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        email_lower = email.lower()
        userid = self.email_index.get(email_lower)
        if userid:
            return self.users[userid].copy()
        return None

    def get_all_users(self) -> List[Dict[str, Any]]:
        return [user.copy() for user in self.users.values()]

    def update_user(self, userid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if userid not in self.users:
            raise KeyError(f"User with ID '{userid}' not found")

        user = self.users[userid]

        if 'email' in data:
            new_email_lower = data['email'].lower()
            if (new_email_lower in self.email_index and
               self.email_index[new_email_lower] != userid):
                raise ValueError(f"Email '{data['email']}' already registered")

            old_email_lower = user['email'].lower()
            if old_email_lower in self.email_index:
                del self.email_index[old_email_lower]

            user['email'] = data['email']
            self.email_index[new_email_lower] = userid

        if 'username' in data:
            new_username_lower = data['username'].lower()
            if (new_username_lower in self.username_index and
               self.username_index[new_username_lower] != userid):
                raise ValueError(f"Username '{data['username']}'"
                                 f" already taken")

            old_username_lower = user['username'].lower()
            if old_username_lower in self.username_index:
                del self.username_index[old_username_lower]

            user['username'] = data['username']
            self.username_index[new_username_lower] = userid

        if 'password' in data:
            user['password'] = data['password']
        if 'reputation' in data:
            user['reputation'] = data['reputation']
        if 'is_admin' in data:
            user['is_admin'] = data['is_admin']
        if 'total_reviews' in data:
            user['total_reviews'] = data['total_reviews']

        self.save_users()
        logger.info(f"Updated user: {userid}")
        return user.copy()

    def delete_user(self, userid: str) -> None:
        if userid not in self.users:
            raise KeyError(f"User with ID '{userid}' not found")

        user = self.users[userid]
        email_lower = user['email'].lower()

        if email_lower in self.email_index:
            del self.email_index[email_lower]

        del self.users[userid]
        self.save_users()
        logger.info(f"Deleted user: {userid}")

    def increment_review_count(self, userid: str) -> None:
        if userid not in self.users:
            raise KeyError(f"User with ID '{userid}' not found")

        self.users[userid]['total_reviews'] += 1
        self.save_users()

    def increment_penalty_count(self, userid: str) -> None:
        if userid not in self.users:
            raise KeyError(f"User with ID '{userid}' not found")

        if 'total_penalty_count' not in self.users[userid]:
            self.users[userid]['total_penalty_count'] = 0

        self.users[userid]['total_penalty_count'] += 1
        self.save_users()
        logger.info(f"Incremented penalty count for user: {userid}"
                    f"self.users[userid]['total_penalties']"
                    )

    def suspend_user(self, userid: str) -> None:
        """Suspend a user account."""
        if userid not in self.users:
            raise KeyError(f"User with ID '{userid}' not found")

        self.users[userid]['is_suspended'] = True
        self.save_users()
        logger.info(f"Suspended user: {userid}")

    def reactivate_user(self, userid: str) -> None:
        """Reactivate a suspended user account."""
        if userid not in self.users:
            raise KeyError(f"User with ID '{userid}' not found")

        self.users[userid]['is_suspended'] = False
        self.save_users()
        logger.info(f"Reactivated user: {userid}")
