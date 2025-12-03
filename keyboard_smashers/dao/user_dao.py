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

                    favorites_str = row.get('favorites', '')
                    favorites = (
                        [
                            f.strip()
                            for f in favorites_str.split(',') if f.strip()
                        ]
                        if favorites_str else []
                    )

                    following_str = row.get('following', '')
                    following = (
                        [
                            f.strip()
                            for f in following_str.split(',') if f.strip()
                        ]
                        if following_str else []
                    )

                    followers_str = row.get('followers', '')
                    followers = (
                        [
                            f.strip()
                            for f in followers_str.split(',') if f.strip()
                        ]
                        if followers_str else []
                    )

                    blocked_str = row.get('blocked_users', '')
                    blocked_users = (
                        [
                            f.strip()
                            for f in blocked_str.split(',') if f.strip()
                        ]
                        if blocked_str else []
                    )

                    # Load notifications (stored as JSON-like string)
                    notifications = []
                    notifications_str = row.get('notifications', '')
                    if notifications_str:
                        try:
                            import json
                            notifications = json.loads(notifications_str)
                        except (json.JSONDecodeError, ValueError):
                            notifications = []

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
                        ),
                        'favorites': favorites,
                        'following': following,
                        'followers': followers,
                        'blocked_users': blocked_users,
                        'notifications': notifications
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
                    'total_penalty_count',
                    'favorites',
                    'following',
                    'followers',
                    'blocked_users',
                    'notifications'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for user in self.users.values():
                    favorites_str = (
                        ','.join(user.get('favorites', []))
                    )
                    following_str = (
                        ','.join(user.get('following', []))
                    )
                    followers_str = (
                        ','.join(user.get('followers', []))
                    )
                    blocked_str = (
                        ','.join(user.get('blocked_users', []))
                    )
                    # Serialize notifications to JSON
                    import json
                    notifications = user.get('notifications', [])
                    # Convert datetime objects to strings for JSON serialization
                    notifications_serializable = []
                    for notif in notifications:
                        notif_copy = notif.copy()
                        if 'timestamp' in notif_copy and hasattr(notif_copy['timestamp'], 'isoformat'):
                            notif_copy['timestamp'] = notif_copy['timestamp'].isoformat()
                        notifications_serializable.append(notif_copy)
                    notifications_str = json.dumps(notifications_serializable)

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
                        ),
                        'favorites': favorites_str,
                        'following': following_str,
                        'followers': followers_str,
                        'blocked_users': blocked_str,
                        'notifications': notifications_str
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
            'total_penalty_count': 0,
            'favorites': [],
            'following': [],
            'followers': [],
            'blocked_users': [],
            'notifications': []
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

    def toggle_favorite(self, userid: str, movie_id: str) -> bool:
        """
        Toggle a movie in user's favorites list.
        Returns True if added, False if removed.
        """
        if userid not in self.users:
            raise KeyError(f"User with ID '{userid}' not found")

        if 'favorites' not in self.users[userid]:
            self.users[userid]['favorites'] = []

        favorites = self.users[userid]['favorites']

        if movie_id in favorites:
            favorites.remove(movie_id)
            self.save_users()
            logger.info(
                f"Removed movie {movie_id} from"
                f" user {userid}'s favorites"
            )
            return False
        else:
            favorites.append(movie_id)
            self.save_users()
            logger.info(
                f"Added movie {movie_id} to"
                f" user {userid}'s favorites"
            )
            return True

    def follow_user(self, follower_id: str, followee_id: str) -> None:
        """
        Make follower_id follow followee_id.
        Sends notification to followee.
        """
        if follower_id not in self.users:
            raise KeyError(f"User with ID '{follower_id}' not found")
        if followee_id not in self.users:
            raise KeyError(f"User with ID '{followee_id}' not found")
        if follower_id == followee_id:
            raise ValueError("Users cannot follow themselves")

        follower = self.users[follower_id]
        followee = self.users[followee_id]

        # Check if users have blocked each other
        if self.is_blocked(follower_id, followee_id):
            raise ValueError("Cannot follow a user you have blocked or who has blocked you")

        if 'following' not in follower:
            follower['following'] = []
        if 'followers' not in followee:
            followee['followers'] = []

        # Idempotent - only add if not already following
        if followee_id not in follower['following']:
            follower['following'].append(followee_id)
            followee['followers'].append(follower_id)

            # Send notification using Observer pattern
            from keyboard_smashers.models.user_model import User
            followee_user = User(
                username=followee['username'],
                email=followee['email'],
                userid=followee['userid'],
                password=followee['password'],
                reputation=followee['reputation'],
                creation_date=followee['creation_date'],
                is_admin=followee['is_admin'],
                is_suspended=followee.get('is_suspended', False),
                total_penalty_count=followee.get('total_penalty_count', 0),
                following=followee.get('following', []),
                followers=followee.get('followers', []),
                blocked_users=followee.get('blocked_users', [])
            )
            # Load existing notifications before adding new one
            followee_user.notifications = followee.get('notifications', [])

            # Create a dummy review object for notification
            class FollowNotification:
                review_id = "follow_notification"

            followee_user.update(
                FollowNotification(),
                'user_follow',
                {'message': f"{follower['username']} started following you!"}
            )
            # Update notifications in dict
            followee['notifications'] = followee_user.notifications

            self.save_users()
            logger.info(
                f"User {follower_id} now follows {followee_id}"
            )

    def unfollow_user(self, follower_id: str, followee_id: str) -> None:
        """Remove follow relationship between two users."""
        if follower_id not in self.users:
            raise KeyError(f"User with ID '{follower_id}' not found")
        if followee_id not in self.users:
            raise KeyError(f"User with ID '{followee_id}' not found")

        follower = self.users[follower_id]
        followee = self.users[followee_id]

        if 'following' not in follower:
            follower['following'] = []
        if 'followers' not in followee:
            followee['followers'] = []

        if followee_id in follower['following']:
            follower['following'].remove(followee_id)
        if follower_id in followee['followers']:
            followee['followers'].remove(follower_id)

        self.save_users()
        logger.info(
            f"User {follower_id} unfollowed {followee_id}"
        )

    def get_followers(self, userid: str) -> List[Dict[str, Any]]:
        """Get list of users who follow this user."""
        if userid not in self.users:
            raise KeyError(f"User with ID '{userid}' not found")

        user = self.users[userid]
        follower_ids = user.get('followers', [])

        followers = []
        for follower_id in follower_ids:
            if follower_id in self.users:
                followers.append(self.users[follower_id].copy())

        return followers

    def get_following(self, userid: str) -> List[Dict[str, Any]]:
        """Get list of users that this user follows."""
        if userid not in self.users:
            raise KeyError(f"User with ID '{userid}' not found")

        user = self.users[userid]
        following_ids = user.get('following', [])

        following = []
        for following_id in following_ids:
            if following_id in self.users:
                following.append(self.users[following_id].copy())

        return following

    def block_user(self, blocker_id: str, blocked_id: str):
        """
        Block a user. Bidirectional blocking - both users block each other.
        Automatically removes any existing follow relationships.
        """
        if blocker_id not in self.users:
            raise KeyError(f"User with ID '{blocker_id}' not found")
        if blocked_id not in self.users:
            raise KeyError(f"User with ID '{blocked_id}' not found")

        if blocker_id == blocked_id:
            raise ValueError("Cannot block yourself")

        blocker = self.users[blocker_id]
        blocked = self.users[blocked_id]

        # Initialize blocked_users lists if needed
        if 'blocked_users' not in blocker:
            blocker['blocked_users'] = []
        if 'blocked_users' not in blocked:
            blocked['blocked_users'] = []

        # Add bidirectional blocking (idempotent)
        if blocked_id not in blocker['blocked_users']:
            blocker['blocked_users'].append(blocked_id)
        if blocker_id not in blocked['blocked_users']:
            blocked['blocked_users'].append(blocker_id)

        # Remove any existing follow relationships
        if 'following' in blocker and blocked_id in blocker['following']:
            blocker['following'].remove(blocked_id)
        if 'followers' in blocker and blocked_id in blocker['followers']:
            blocker['followers'].remove(blocked_id)
        if 'following' in blocked and blocker_id in blocked['following']:
            blocked['following'].remove(blocker_id)
        if 'followers' in blocked and blocker_id in blocked['followers']:
            blocked['followers'].remove(blocker_id)

        self.save_users()
        logger.info(
            f"User {blocker_id} blocked {blocked_id}"
            f" (bidirectional block applied)"
        )

    def unblock_user(self, unblocker_id: str, blocked_id: str):
        """
        Unblock a user. Removes bidirectional block for both users.
        """
        if unblocker_id not in self.users:
            raise KeyError(f"User with ID '{unblocker_id}' not found")
        if blocked_id not in self.users:
            raise KeyError(f"User with ID '{blocked_id}' not found")

        unblocker = self.users[unblocker_id]
        blocked = self.users[blocked_id]

        # Initialize blocked_users lists if needed
        if 'blocked_users' not in unblocker:
            unblocker['blocked_users'] = []
        if 'blocked_users' not in blocked:
            blocked['blocked_users'] = []

        # Remove bidirectional block (idempotent)
        if blocked_id in unblocker['blocked_users']:
            unblocker['blocked_users'].remove(blocked_id)
        if unblocker_id in blocked['blocked_users']:
            blocked['blocked_users'].remove(unblocker_id)

        self.save_users()
        logger.info(
            f"User {unblocker_id} unblocked {blocked_id}"
            f" (bidirectional unblock applied)"
        )

    def is_blocked(self, user_id: str, other_user_id: str) -> bool:
        """
        Check if two users have blocked each other.
        Returns True if either user has blocked the other.
        """
        if user_id not in self.users or other_user_id not in self.users:
            return False

        user = self.users[user_id]
        other_user = self.users[other_user_id]

        user_blocked = other_user_id in user.get('blocked_users', [])
        other_blocked = user_id in other_user.get('blocked_users', [])

        return user_blocked or other_blocked
