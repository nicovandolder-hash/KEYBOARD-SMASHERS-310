from datetime import datetime
from keyboard_smashers.models.review_subject_model import ReviewSubject


class Review(ReviewSubject):
    def __init__(
            self,
            review_id,
            user_id,
            movie_id,
            movie_title,
            rating,
            comment,
            review_date,
            creation_date=None,
            helpful_votes=0):
        self.review_id = review_id
        self.user_id = user_id
        self.movie_id = movie_id
        self.movie_title = movie_title
        self.rating = rating
        self.comment = comment
        self.review_date = review_date
        self.creation_date = creation_date if creation_date else datetime.now()
        self.helpful_votes = helpful_votes
        self.is_spotlighted = False
        self.is_removed = False
        self.voted_users = set()

    def add_helpful_vote(self, user_id):
        if user_id in self.voted_users:
            return "User has already voted on this review."
        self.helpful_votes += 1
        self.voted_users.add(user_id)
        self.notify(
            event_type="helpful_vote_added",
            event_data={
                "user_id": user_id,
                "message": (
                   "Your review received a helpful vote from user {user_id}."
                )
            }
        )
        return "Helpful vote added."

    def remove_by_admin(self, admin_id, reason):
        if self.is_removed:
            return "Review already removed"

        self.is_removed = True

        self.notify('ADMIN_REMOVAL', {
            'message': 'Your review was removed by an administrator',
            'message': 'Your review was removed by an administrator',
            'admin_id': admin_id,
            'reason': reason,
            'removed_at': datetime.now()
        })

    def set_spotlight(self, status, featured_by=None):
        self.is_spotlighted = status

        if status:
            self.notify('SPOTLIGHTED', {
                'message': 'Congratulations! Your review is spotlighted!',
                'featured_by': featured_by,
                'spotlighted_at': datetime.now()
            })
        else:
            self.notify('SPOTLIGHT_REMOVED', {
                'message': 'Your review spotlight status was removed',
                'message': 'Your review spotlight status was removed',
                'removed_by': featured_by
            })

        return f"Review spotlight status set to {status}"
