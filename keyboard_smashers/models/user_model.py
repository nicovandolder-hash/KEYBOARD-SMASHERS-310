from datetime import datetime
import re
import logging
from keyboard_smashers.interfaces.observer_interface import Observer

logger = logging.getLogger(__name__)


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

        logger.info(
            f"User created: {
                self.username} (ID: {userid}, Admin: {
                self.is_admin})")

        if password:
            self.set_password(password)

    def set_password(self, password):

        logger.debug(f"Setting password for user: {self.username}")
        try:
            if len(password) < 8:
                logger.warning(
                    f"Password validation failed for {
                        self.username}: Too short")
                raise ValueError("Password must be at least 8 characters long")
            if not any(char.isdigit() for char in password):
                logger.warning(
                    f"Password validation failed for {
                        self.username}: No digit")
                raise ValueError("Password must contain at least one digit.")
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                logger.warning(
                    f"Password validation failed for {
                        self.username}: No special character")
                raise ValueError(
                    "Password must contain at least one special character.")
            if not re.search(r'[A-Z]', password):
                logger.warning(
                    f"Password validation failed for {
                        self.username}: No uppercase letter")
                raise ValueError(
                    "Password must contain at least one uppercase letter.")
            if not re.search(r'[a-z]', password):
                logger.warning(
                    f"Password validation failed for {
                        self.username}: No lowercase letter")
                raise ValueError(
                    "Password must contain at least one lowercase letter.")

            self.password = password
            logger.info(f"Password set successfully for user: {self.username}")
            return "Password set successfully"

        except ValueError as e:
            logger.error(
                f"Error setting password for user {
                    self.username}: {e}")
            raise

    def check_password(self, password):
        is_correct = self.password == password
        if is_correct:
            logger.debug(f"Password check passed for user: {self.username}")
        else:
            logger.debug(f"Password check failed for user: {self.username}")

        return is_correct

    def add_review(self, review):
        logger.debug(
            f"User {
                self.username} adding review ID: {
                review.review_id}")
        self.reviews.append(review)
        self.total_reviews += 1

        logger.info(f"Review ID: {review.review_id} added by user: "
                    f"{self.username}. Total reviews: {self.total_reviews}")

    def update(self, review, event_type, event_data):
        notification = {
            'timestamp': datetime.now(),
            'review_id': review.review_id,
            'event_type': event_type,
            'data': event_data
        }
        self.notifications.append(notification)

        logger.info(
            f"User {self.username} notified of event: {event_type} "
        )
        print(
            f"[NOTIFICATION] {self.username}: {event_type} - "
            f"{event_data.get('message', '')}"
        )

    def get_notifications(self):
        logger.debug(f"Fetching notifications for user: {self.username}")
        return self.notifications
