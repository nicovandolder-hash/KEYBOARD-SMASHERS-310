from datetime import datetime
import re
from keyboard_smashers.interfaces.observer_interface import Observer


class User(Observer):
    def __init__(self, username, email, userid, password=None, reputation=3,
                 creation_date=None, is_admin=False):
        self.username = username
        self.email = email
        self.userid = userid
        self.password = None
        self.reputation = reputation
        self.creation_date = creation_date if creation_date else datetime.now()
        self.reviews = []
        self.total_reviews = 0
        self.is_admin = is_admin
        self.notifications = []
        if password:
            self.set_password(password)

    def set_password(self, password):
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not any(char.isdigit() for char in password):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError(
                "Password must contain at least one special character."
            )
        if not re.search(r'[A-Z]', password):
            raise ValueError(
                "Password must contain at least one uppercase letter."
            )
        if not re.search(r'[a-z]', password):
            raise ValueError(
                "Password must contain at least one lowercase letter."
            )

        self.password = password
        return "Password set successfully"

    def check_password(self, password):
        return self.password == password

    def add_review(self, review):
        self.reviews.append(review)
        self.total_reviews += 1

    def update(self, review, event_type, event_data):
        notification = {
            'timestamp': datetime.now(),
            'review_id': review.review_id,
            'event_type': event_type,
            'data': event_data
        }
        self.notifications.append(notification)
        msg = event_data.get('message', '')
        print(f"[NOTIFICATION] {self.username}: {event_type} - {msg}")

    def get_notifications(self):
        """Get user notifications"""
        return self.notifications
