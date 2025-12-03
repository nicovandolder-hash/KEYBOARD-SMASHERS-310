from fastapi import APIRouter, HTTPException, Response, Cookie, Path
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging
from keyboard_smashers.dao.user_dao import UserDAO
from keyboard_smashers.models.user_model import User

logger = logging.getLogger(__name__)


class UserAPISchema(BaseModel):

    userid: str = Field(None, description="Unique User ID", example="user_000")
    username: str = Field(..., description="User's display name", example=(
        "reviewer_bob"))
    email: str = Field(..., description="User's email address", example=(
        "bob@stu.ubc.ca"))
    reputation: int = Field(3, description="User reputation score")
    creation_date: datetime = Field(None, description=(
        "Date user account was created"))
    total_reviews: int = Field(0, description=(
        "Total number of reviews written"))
    is_admin: bool = Field(False, description=(
        "Whether the user is an administrator"))
    total_penalty_count: int = Field(0, description=(
        "Total number of penalties issued to the user"))
    favorites: List[str] = Field(default_factory=list, description=(
        "List of favorite movie IDs"))


class PublicUserSchema(BaseModel):
    """Minimal user information safe for public viewing"""
    userid: str = Field(..., description="Unique User ID")
    username: str = Field(..., description="User's display name")
    reputation: int = Field(..., description="User reputation score")
    total_reviews: int = Field(..., description="Total number of reviews written")
    favorites: List[str] = Field(..., description="List of favorite movie IDs")

    class Config:
        from_attributes = True


class UserCreateSchema(BaseModel):
    username: str = Field(..., description="User's display name")
    email: str = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    reputation: int = Field(3, description="User reputation score")
    is_admin: bool = Field(False, description=(
        "Whether the user is an administrator"))


class UpdateUserSchema(BaseModel):
    username: Optional[str] = Field(None, description="User's display name")
    email: Optional[str] = Field(None, description="User's email address")
    password: Optional[str] = Field(None, description="User's password")
    reputation: Optional[int] = Field(None,
                                      description="User reputation score")
    is_admin: Optional[bool] = Field(None, description=(
                                     "Whether the user is an administrator"))


class LoginSchema(BaseModel):
    email: str = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class UserController:

    user_dao = None

    def __init__(self, csv_path: str = ("data/users.csv")):
        if UserController.user_dao is None:
            UserController.user_dao = UserDAO(csv_path=csv_path)
        self.user_dao = UserController.user_dao
        logger.info(f"UserController initialized with"
                    f" {len(self.user_dao.users)} users")

    def dict_to_user_model(self, user_dict: dict) -> User:
        return User(
            userid=user_dict['userid'],
            username=user_dict['username'],
            email=user_dict['email'],
            password=user_dict['password'],
            reputation=user_dict['reputation'],
            creation_date=user_dict['creation_date'],
            is_admin=user_dict['is_admin'],
            total_penalty_count=user_dict.get('total_penalty_count', 0),
            is_suspended=user_dict.get('is_suspended', False)
        )

    def dict_to_schema(self, user_dict: dict) -> UserAPISchema:
        from keyboard_smashers.controllers.movie_controller import (
            movie_controller_instance
        )

        # Filter out deleted movies from favorites
        if 'favorites' in user_dict and user_dict['favorites']:
            valid_favorites = []
            for movie_id in user_dict['favorites']:
                try:
                    movie_controller_instance.movie_dao.get_movie(movie_id)
                    valid_favorites.append(movie_id)
                except KeyError:
                    pass
            user_dict['favorites'] = valid_favorites

        return UserAPISchema(**user_dict)

    def authenticate_user(self, email: str, password: str):
        # Validate inputs
        if not email or not email.strip():
            logger.warning("Authentication failed: Email cannot be empty")
            return None
        if not password:
            logger.warning("Authentication failed: Password cannot be empty")
            return None

        user_dict = self.user_dao.get_user_by_email(email)

        if not user_dict:
            logger.warning(
                f"Authentication failed: User not found for email {email}")
            return None

        user = self.dict_to_user_model(user_dict)

        if not user.check_password(password):
            logger.warning(
                f"Authentication failed: Invalid password for {email}")
            return None

        logger.info(
            f"User authenticated successfully:"
            f"{user.username} ({user.userid})")
        return user

    def create_user(self, user_data: UserCreateSchema) -> UserAPISchema:
        logger.info(f"Creating new user: {user_data.username}")

        temp_user = User(
            userid="temp",
            username=user_data.username,
            email=user_data.email,
            reputation=user_data.reputation,
            is_admin=user_data.is_admin,
        )

        temp_user.set_password(user_data.password)

        user_dict = {
            'username': user_data.username,
            'email': user_data.email,
            'password': temp_user.password,
            'reputation': user_data.reputation,
            'is_admin': user_data.is_admin,
            'creation_date': datetime.now()
        }

        try:
            created_user = self.user_dao.create_user(user_dict)
            logger.info(f"Created new user: {created_user['userid']}"
                        f" - {user_data.username}")
            return self.dict_to_schema(created_user)

        except ValueError as e:
            logger.error(f"Error creating user: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    def update_user_by_id(
        self,
        user_id: str,
            user_data: UpdateUserSchema) -> UserAPISchema:
        logger.info(f"Attempting to update user: {user_id}")
        try:
            existing_user_dict = self.user_dao.get_user(user_id)
        except KeyError:
            logger.error(f"User with ID '{user_id}' not found for update")
            raise HTTPException(
                status_code=404,
                detail=f"User with ID '{user_id}' not found"
            )

        update_dict = {}
        try:
            if user_data.username is not None:

                update_dict['username'] = user_data.username
            if user_data.email is not None:

                update_dict['email'] = user_data.email
            if user_data.password is not None:

                temp_user = User(
                    userid="temp",
                    username="temp",
                    email="temp@test.com"
                )
                temp_user.set_password(user_data.password)
                update_dict['password'] = temp_user.password
            if user_data.reputation is not None:
                update_dict['reputation'] = user_data.reputation
            if user_data.is_admin is not None:

                update_dict['is_admin'] = user_data.is_admin

            if not update_dict:
                logger.info(f"No updates provided for user: {user_id}")
                return self.dict_to_schema(existing_user_dict)

            updated_user = self.user_dao.update_user(user_id, update_dict)
            logger.info(f"Updated user: {user_id}")

            return self.dict_to_schema(updated_user)

        except ValueError as e:
            logger.error(f"Error updating user {user_id}: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    def delete_user_by_id(self, user_id: str) -> dict:
        logger.info(f"Attempting to delete user: {user_id}")
        try:
            # Cascade delete: Remove all user data before deleting user

            # 1. Delete user's reviews
            from keyboard_smashers.controllers.review_controller import (
                review_controller_instance
            )
            try:
                reviews = review_controller_instance.review_dao
                user_reviews = reviews.get_reviews_by_user(user_id)
                for review in user_reviews:
                    reviews.delete_review(review['review_id'])
                logger.info(
                    f"Deleted {len(user_reviews)} reviews "
                    f"for user {user_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Error deleting reviews for user {user_id}: {e}"
                )

            # 2. Delete user's penalties
            from keyboard_smashers.controllers.penalty_controller import (
                penalty_controller_instance
            )
            try:
                penalties = penalty_controller_instance.penalty_dao
                user_penalties = penalties.get_penalties_by_user(user_id)
                for penalty in user_penalties:
                    penalties.delete_penalty(penalty.penalty_id)
                logger.info(
                    f"Deleted {len(user_penalties)} penalties "
                    f"for user {user_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Error deleting penalties for user {user_id}: {e}"
                )

            # 3. Delete user's reports
            from keyboard_smashers.dao.report_dao import ReportDAO
            try:
                report_dao = ReportDAO()
                user_reports = report_dao.get_reports_by_user(user_id)
                for report in user_reports:
                    report_dao.delete_report(report['report_id'])
                logger.info(
                    f"Deleted {len(user_reports)} reports "
                    f"by user {user_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Error deleting reports for user {user_id}: {e}"
                )

            # 4. Invalidate user's sessions
            from keyboard_smashers.auth import SessionManager
            try:
                SessionManager.invalidate_user_sessions(user_id)
                logger.info(f"Invalidated sessions for user {user_id}")
            except Exception as e:
                logger.warning(
                    f"Error invalidating sessions for user {user_id}: {e}")

            # 5. Finally, delete the user
            self.user_dao.delete_user(user_id)
            logger.info(f"Deleted user: {user_id}")
            return {
                "message": (
                    f"User '{user_id}' and all associated data "
                    f"deleted successfully"
                )
            }
        except KeyError:
            logger.error(f"User with ID '{user_id}' not found for deletion")
            raise HTTPException(
                status_code=404,
                detail=f"User with ID '{user_id}' not found"
            )

    def get_all_users(self) -> List[UserAPISchema]:
        logger.debug("Retrieving all users")
        users = self.user_dao.get_all_users()
        return [self.dict_to_schema(user) for user in users]

    def get_user_by_id(self, user_id: str) -> Optional[UserAPISchema]:
        # Validate input
        if not user_id or not user_id.strip():
            raise HTTPException(
                status_code=400,
                detail="User ID cannot be empty"
            )

        logger.debug(f"Retrieving user by ID: {user_id}")
        try:
            user_dict = self.user_dao.get_user(user_id)
            logger.debug(f"User found: {user_id} - {user_dict['username']}")
            return self.dict_to_schema(user_dict)
        except KeyError:
            logger.warning(f"User with ID '{user_id}' not found")
            raise HTTPException(
                status_code=404,
                detail=f"User with ID '{user_id}' not found"
            )

    def get_user_model_by_id(self, user_id: str) -> User:
        try:
            user_dict = self.user_dao.get_user(user_id)
            return self.dict_to_user_model(user_dict)
        except KeyError:
            raise HTTPException(
                status_code=404,
                detail=f"User with ID '{user_id}' not found"
            )


user_controller_instance = UserController()

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.post("/register", response_model=UserAPISchema, status_code=201)
def register_user(user_data: UserCreateSchema):
    return user_controller_instance.create_user(user_data)


@router.post("/login")
def login(login_data: LoginSchema, response: Response):
    from keyboard_smashers.auth import SessionManager

    user = user_controller_instance.authenticate_user(
        login_data.email,
        login_data.password
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password")

    # Check if user is suspended
    if user.is_suspended:
        raise HTTPException(
            status_code=403,
            detail="Account is suspended. Please contact an administrator.")

    session_token = SessionManager.create_session(user.userid)

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7200
    )

    return {
        "message": "Login successful",
        "user": UserAPISchema(
            userid=user.userid,
            username=user.username,
            email=user.email,
            reputation=user.reputation,
            creation_date=user.creation_date,
            total_reviews=user.total_reviews,
            is_admin=user.is_admin
        )
    }


@router.post("/logout")
def logout(
    response: Response,
    session_token: Optional[str] = Cookie(
        default=None,
        alias="session_token")):
    from keyboard_smashers.auth import SessionManager

    if session_token:
        SessionManager.delete_session(session_token)

    response.delete_cookie(key="session_token")
    return {"message": "Logout successful"}


@router.get("/me", response_model=UserAPISchema)
def get_current_user_info(

    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    from keyboard_smashers.auth import SessionManager

    if not session_token:
        raise HTTPException(status_code=401,
                            detail="Not authenticated. Please login.")

    user_id = SessionManager.validate_session(session_token)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again.")

    return user_controller_instance.get_user_by_id(user_id)

# ---------------- PROTECTED ADMIN ONLY ENDPOINTS ----------------


@router.get("/", response_model=List[UserAPISchema])
def get_users(
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    from keyboard_smashers.auth import SessionManager

    if not session_token:
        raise HTTPException(status_code=401,
                            detail="Not authenticated. Please login.")

    user_id = SessionManager.validate_session(session_token)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again.")

    user = user_controller_instance.get_user_model_by_id(user_id)
    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required")

    return user_controller_instance.get_all_users()


@router.get("/{user_id}", response_model=UserAPISchema)
def get_user(
    user_id: str = Path(..., min_length=1, max_length=100),
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    from keyboard_smashers.auth import SessionManager

    if not session_token:
        raise HTTPException(status_code=401,
                            detail="Not authenticated. Please login.")

    current_user_id = SessionManager.validate_session(session_token)
    if not current_user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again.")

    current_user = (
        user_controller_instance.get_user_model_by_id(current_user_id)
    )

    if current_user_id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail=(
                "You can only view your own profile. "
                "Admin privileges required to view other profiles."
            )
        )

    return user_controller_instance.get_user_by_id(user_id)


@router.put("/{user_id}", response_model=UserAPISchema)
def update_user(
    user_id: str = Path(..., min_length=1, max_length=100),
    user_data: UpdateUserSchema = None,
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    from keyboard_smashers.auth import SessionManager

    if not session_token:
        raise HTTPException(status_code=401,
                            detail="Not authenticated. Please login.")

    current_user_id = SessionManager.validate_session(session_token)
    if not current_user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again.")

    current_user = (
        user_controller_instance.get_user_model_by_id(current_user_id)
    )
    if current_user_id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own profile"
        )

    return user_controller_instance.update_user_by_id(user_id, user_data)


@router.delete("/{user_id}")
def delete_user(
    user_id: str = Path(..., min_length=1, max_length=100),
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    from keyboard_smashers.auth import SessionManager

    if not session_token:
        raise HTTPException(status_code=401,
                            detail="Not authenticated. Please login.")

    current_user_id = SessionManager.validate_session(session_token)
    if not current_user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again.")

    user = user_controller_instance.get_user_model_by_id(current_user_id)
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required")

    return user_controller_instance.delete_user_by_id(user_id)


@router.post("/{user_id}/suspend")
def suspend_user(
    user_id: str = Path(..., min_length=1, max_length=100),
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    """
    Admin endpoint to suspend a user account.
    Suspended users cannot log in or create reviews.
    """
    from keyboard_smashers.auth import SessionManager

    if not session_token:
        raise HTTPException(status_code=401,
                            detail="Not authenticated. Please login.")

    current_user_id = SessionManager.validate_session(session_token)
    if not current_user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again.")

    user = user_controller_instance.get_user_model_by_id(current_user_id)
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required")

    try:
        user_controller_instance.user_dao.suspend_user(user_id)
        # Invalidate all active sessions for the suspended user
        SessionManager.invalidate_user_sessions(user_id)
        logger.info(
            f"Admin {current_user_id} suspended user {user_id} "
            f"and invalidated their sessions"
        )
        return {"message": f"User {user_id} has been suspended"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{user_id}/reactivate")
def reactivate_user(
    user_id: str = Path(..., min_length=1, max_length=100),
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    """
    Admin endpoint to reactivate a suspended user account.
    """
    from keyboard_smashers.auth import SessionManager

    if not session_token:
        raise HTTPException(status_code=401,
                            detail="Not authenticated. Please login.")

    current_user_id = SessionManager.validate_session(session_token)
    if not current_user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again.")

    user = user_controller_instance.get_user_model_by_id(current_user_id)
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required")

    try:
        user_controller_instance.user_dao.reactivate_user(user_id)
        return {"message": f"User {user_id} has been reactivated"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{user_id}/favorites/{movie_id}")
def toggle_favorite(
    user_id: str = Path(..., min_length=1, max_length=100),
    movie_id: str = Path(..., min_length=1, max_length=100),
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    """
    Toggle a movie in/out of user's favorites list.
    Returns whether the movie was added (true) or removed (false).
    """
    from keyboard_smashers.auth import SessionManager
    from keyboard_smashers.controllers.movie_controller import (
        movie_controller_instance
    )

    if not session_token:
        raise HTTPException(status_code=401,
                            detail="Not authenticated. Please login.")

    current_user_id = SessionManager.validate_session(session_token)
    if not current_user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again.")

    if current_user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Can only modify your own favorites")

    try:
        movie_controller_instance.movie_dao.get_movie(movie_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Movie with ID '{movie_id}' not found")

    try:
        added = user_controller_instance.user_dao.toggle_favorite(
            user_id, movie_id
        )
        action = "added to" if added else "removed from"
        return {
            "message": f"Movie {movie_id} {action} favorites",
            "added": added,
            "favorites": (
                user_controller_instance.user_dao.get_user(user_id)[
                    'favorites'
                ]
            )
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{user_id}/follow")
def follow_user(
    user_id: str = Path(..., min_length=1, max_length=100),
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    """
    Follow a user. Authenticated user follows the specified user_id.
    Returns a success message with updated follower counts.
    """
    from keyboard_smashers.auth import SessionManager

    if not session_token:
        raise HTTPException(status_code=401,
                            detail="Not authenticated. Please login.")

    current_user_id = SessionManager.validate_session(session_token)
    if not current_user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again.")

    try:
        user_controller_instance.user_dao.follow_user(
            current_user_id, user_id
        )
        followee = user_controller_instance.user_dao.get_user(user_id)
        return {
            "message": f"Successfully followed {followee['username']}",
            "following": user_id,
            "follower_count": len(followee.get('followers', []))
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{user_id}/follow")
def unfollow_user(
    user_id: str = Path(..., min_length=1, max_length=100),
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    """
    Unfollow a user. Authenticated user unfollows the specified user_id.
    Returns a success message with updated follower counts.
    """
    from keyboard_smashers.auth import SessionManager

    if not session_token:
        raise HTTPException(status_code=401,
                            detail="Not authenticated. Please login.")

    current_user_id = SessionManager.validate_session(session_token)
    if not current_user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again.")

    try:
        user_controller_instance.user_dao.unfollow_user(
            current_user_id, user_id
        )
        followee = user_controller_instance.user_dao.get_user(user_id)
        return {
            "message": f"Successfully unfollowed {followee['username']}",
            "unfollowed": user_id,
            "follower_count": len(followee.get('followers', []))
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{user_id}/followers")
def get_followers(
    user_id: str = Path(..., min_length=1, max_length=100),
    limit: int = 20,
    offset: int = 0
):
    """
    Get a paginated list of users who follow the specified user.
    No authentication required (public information).
    """
    try:
        all_followers = user_controller_instance.user_dao.get_followers(
            user_id
        )
        paginated = all_followers[offset:offset + limit]
        
        # Convert to public schema (hide sensitive info)
        public_followers = [
            PublicUserSchema(
                userid=follower['userid'],
                username=follower['username'],
                reputation=follower.get('reputation', 3),
                total_reviews=follower.get('total_reviews', 0),
                favorites=follower.get('favorites', [])
            )
            for follower in paginated
        ]
        
        return {
            "user_id": user_id,
            "total": len(all_followers),
            "limit": limit,
            "offset": offset,
            "followers": public_followers
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"User not found: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting followers for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/following")
def get_following(
    user_id: str = Path(..., min_length=1, max_length=100),
    limit: int = 20,
    offset: int = 0
):
    """
    Get a paginated list of users that the specified user follows.
    No authentication required (public information).
    """
    try:
        all_following = user_controller_instance.user_dao.get_following(
            user_id
        )
        paginated = all_following[offset:offset + limit]
        
        # Convert to public schema (hide sensitive info)
        public_following = [
            PublicUserSchema(
                userid=followee['userid'],
                username=followee['username'],
                reputation=followee.get('reputation', 3),
                total_reviews=followee.get('total_reviews', 0),
                favorites=followee.get('favorites', [])
            )
            for followee in paginated
        ]
        
        return {
            "user_id": user_id,
            "total": len(all_following),
            "limit": limit,
            "offset": offset,
            "following": public_following
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"User not found: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting following for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/block")
def block_user(
    user_id: str = Path(..., min_length=1, max_length=100),
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    """
    Block a user. Creates bidirectional block and removes follow relationships.
    Authenticated user blocks the specified user_id.
    """
    from keyboard_smashers.auth import SessionManager

    if not session_token:
        raise HTTPException(status_code=401,
                            detail="Not authenticated. Please login.")

    current_user_id = SessionManager.validate_session(session_token)
    if not current_user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again.")

    try:
        user_controller_instance.user_dao.block_user(
            current_user_id, user_id
        )
        blocked_user = user_controller_instance.user_dao.get_user(user_id)
        return {
            "message": f"Successfully blocked {blocked_user['username']}",
            "blocked": user_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{user_id}/block")
def unblock_user(
    user_id: str = Path(..., min_length=1, max_length=100),
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    """
    Unblock a user. Removes bidirectional block between users.
    Authenticated user unblocks the specified user_id.
    """
    from keyboard_smashers.auth import SessionManager

    if not session_token:
        raise HTTPException(status_code=401,
                            detail="Not authenticated. Please login.")

    current_user_id = SessionManager.validate_session(session_token)
    if not current_user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again.")

    try:
        user_controller_instance.user_dao.unblock_user(
            current_user_id, user_id
        )
        unblocked_user = user_controller_instance.user_dao.get_user(user_id)
        return {
            "message": f"Successfully unblocked {unblocked_user['username']}",
            "unblocked": user_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/search/users")
def search_users(
    q: str = "",
    limit: int = 20,
    offset: int = 0
):
    """
    Public endpoint to search for users by username.
    Allows users to discover and find each other.
    
    Args:
        q: Search query (username substring, case-insensitive)
        limit: Maximum number of results (default 20)
        offset: Number of results to skip for pagination
    """
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100"
        )
    
    # Get all users
    all_users = user_controller_instance.get_all_users()
    
    # Filter by search query if provided
    if q:
        query_lower = q.lower()
        filtered_users = [
            user for user in all_users
            if query_lower in user.username.lower()
        ]
    else:
        filtered_users = all_users
    
    # Sort by username for consistency
    filtered_users.sort(key=lambda u: u.username.lower())
    
    total = len(filtered_users)
    paginated = filtered_users[offset:offset + limit]
    
    # Convert to public schema (hide sensitive info)
    public_users = [
        PublicUserSchema(
            userid=user.userid,
            username=user.username,
            reputation=user.reputation,
            total_reviews=user.total_reviews,
            favorites=user.favorites
        )
        for user in paginated
    ]
    
    return {
        "users": public_users,
        "total": total,
        "limit": limit,
        "offset": offset,
        "query": q
    }


@router.get("/users/me/notifications")
def get_my_notifications(
    session: str = Cookie(None),
    limit: int = 50,
    offset: int = 0
):
    """
    Get the authenticated user's notifications (e.g., new followers).
    Returns most recent notifications first.
    """
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user_controller_instance.session_manager.get_user_id(session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    try:
        user = user_controller_instance.user_dao.get_user(user_id)
        notifications = user.get('notifications', [])
        
        # Sort by timestamp (most recent first)
        sorted_notifications = sorted(
            notifications,
            key=lambda n: n.get('timestamp', ''),
            reverse=True
        )
        
        total = len(sorted_notifications)
        paginated = sorted_notifications[offset:offset + limit]
        
        return {
            "notifications": paginated,
            "total": total,
            "unread": total,  # All notifications considered unread for now
            "limit": limit,
            "offset": offset
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error getting notifications for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
