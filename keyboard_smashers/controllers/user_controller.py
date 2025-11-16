from fastapi import APIRouter, HTTPException, Response, Cookie
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import csv
from pathlib import Path

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
    def __init__(self):

        self.users: List = []
        self.user_map = {}
        self._user_counter = 1
        self.csv_path: Optional[str] = None
        self.email_map = {}

    def load_users(self, csv_path: str):
        try:
            from keyboard_smashers.models.user_model import User
            self.csv_path = csv_path
            csv_file = Path(csv_path)
            if not csv_file.exists():
                logger.warning(f"User CSV file not found at: {csv_path}")
                return

            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    creation_date = (
                        datetime.fromisoformat(row['creation_date'])
                        if row.get('creation_date')
                        else datetime.now()
                    )
                    is_admin = row.get('is_admin', 'false').lower() == 'true'

                    user = User(
                        userid=row['userid'],
                        username=row['username'],
                        email=row['email'],
                        password=row.get('password'),
                        reputation=int(row.get('reputation', 3)),
                        creation_date=creation_date,
                        is_admin=is_admin
                    )
                    user.total_reviews = int(row.get('total_reviews', 0))

                    self.users.append(user)
                    self.user_map[user.userid] = user
                    self.email_map[user.email.lower()] = user
                    if user.userid.startswith("user_"):
                        try:
                            user_num = int(user.userid.split("_")[1])
                            self._user_counter = max(
                                self._user_counter, user_num + 1)
                        except (IndexError, ValueError):
                            pass

                logger.info(f"Loaded {len(self.users)} users from {csv_path}")
        except ImportError:
            logger.error("Could not import User model. User loading skipped.")
        except Exception as e:
            logger.error(f"Error loading users from {csv_path}: {e}")

    def save_users_to_csv(self, csv_path: str):
        try:
            logger.info(f"Saving users to CSV at: {csv_path}")
            csv_file = Path(csv_path)
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
                    'total_reviews']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for user in self.users:
                    writer.writerow({
                        'userid': user.userid,
                        'username': user.username,
                        'email': user.email,
                        'password': user.password or '',
                        'reputation': user.reputation,
                        'creation_date': user.creation_date.isoformat(),
                        'is_admin': str(user.is_admin).lower(),
                        'total_reviews': user.total_reviews
                    })

            logger.info(f"Saved {len(self.users)} users to {csv_path}")

        except Exception as e:
            logger.error(f"Error saving users to CSV: {e}")
            raise

    def authenticate_user(self, email: str, password: str):
        user = self.email_map.get(email.lower())

        if not user:
            logger.warning(
                f"Authentication failed: User not found for email {email}")
            return None

        if not user.check_password(password):
            logger.warning(
                f"Authentication failed: Invalid password for {email}")
            return None

        logger.info(
            f"User authenticated successfully: {
                user.username} ({
                user.userid})")
        return user

    def create_user(self, user_data: UserCreateSchema) -> UserAPISchema:
        try:
            logger.info(f"Creating new user: {user_data.username}")
            from keyboard_smashers.models.user_model import User

            if any(u.email == user_data.email for u in self.users):
                raise HTTPException(
                    status_code=400,
                    detail="Email already registered")

            user_id = self._generate_user_id()

            new_user = User(
                userid=user_id,
                username=user_data.username,
                email=user_data.email,
                password=user_data.password,
                reputation=user_data.reputation,
                creation_date=datetime.now(),
                is_admin=user_data.is_admin
            )

            self.users.append(new_user)
            self.user_map[user_id] = new_user
            self.email_map[new_user.email.lower()] = new_user

            if (self.csv_path):
                self.save_users_to_csv(self.csv_path)

            logger.info(f"Created new user: {user_id} - {user_data.username}")

            return UserAPISchema.model_validate(new_user)

        except ImportError:
            logger.error("Could not import User model. User creation failed.")
            raise HTTPException(
                status_code=500,
                detail="User model not available")
        except ValueError as e:
            logger.error("Error creating user: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    def update_user_by_id(
            self,
            user_id: str,
            user_data: UpdateUserSchema) -> UserAPISchema:
        logger.info(f"Attempting to update user: {user_id}")
        user = self.user_map.get(user_id)
        if not user:
            logger.error(f"User with ID '{user_id}' not found for update")
            raise HTTPException(status_code=404,
                                detail=f"User with ID '{user_id}' not found")

        logger.debug("Updating user fields")
        try:
            if user_data.username is not None:
                logger.debug(
                    f"Updating username from: {user.username}"
                    f"  --> {user_data.username}")
                user.username = user_data.username
            if user_data.email is not None:
                new_email_lower = user_data.email.lower()
                if any(u.email.lower() == new_email_lower and u.userid !=
                       user_id for u in self.users):
                    logger.warning(
                       "Email update failed for user {user_id}: "
                       "Email already registered"
                    )
                    raise HTTPException(
                        status_code=400, detail="Email already registered")

                old_email_lower = user.email.lower()
                if old_email_lower in self.email_map:
                    del self.email_map[old_email_lower]

                logger.debug(
                    f"Updating email from: {user.email} --> {user_data.email}")
                user.email = user_data.email
                self.email_map[new_email_lower] = user
            if user_data.password is not None:
                logger.debug(f"Updating password for user: {user.username}")
                user.set_password(user_data.password)
            if user_data.reputation is not None:
                logger.debug(
                    f"Updating reputation from: {user.reputation}"
                    f" --> {user_data.reputation}")
                user.reputation = user_data.reputation
            if user_data.is_admin is not None:
                logger.debug(
                    f"Updating is_admin from: {user.is_admin}"
                    f" --> {user_data.is_admin}")
                user.is_admin = user_data.is_admin

            if (self.csv_path):
                self.save_users_to_csv(self.csv_path)

            logger.info(f"Updated user: {user_id} - {user.username}")

            return UserAPISchema.model_validate(user)

        except ValueError as e:
            logger.error(f"Error updating user {user_id}: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    def delete_user_by_id(self, user_id: str) -> dict:
        logger.info(f"Attempting to delete user: {user_id}")
        user = self.user_map.get(user_id)
        if not user:
            logger.error(f"User with ID '{user_id}' not found for deletion")
            raise HTTPException(status_code=404,
                                detail=f"User with ID '{user_id}' not found")

        email_lower = user.email.lower()
        if email_lower in self.email_map:
            del self.email_map[email_lower]

        self.users.remove(user)
        del self.user_map[user_id]

        if (self.csv_path):
            self.save_users_to_csv(self.csv_path)

        logger.info(f"Deleted user: {user_id} - {user.username}")

        return {"message": f"User '{user_id}' deleted successfully"}

    def _generate_user_id(self) -> str:
        user_id = f"user_{self._user_counter:03d}"
        self._user_counter += 1
        return user_id

    def get_all_users(self) -> List[UserAPISchema]:
        logger.debug("Retrieving all users")
        return [UserAPISchema.model_validate(u) for u in self.users]

    def get_user_by_id(self, user_id: str) -> Optional[UserAPISchema]:
        logger.debug(f"Retrieving user by ID: {user_id}")
        user = self.user_map.get(user_id)
        if user:
            logger.debug(f"User found: {user_id} - {user.username}")
            return UserAPISchema.model_validate(user)
        else:
            logger.debug(f"User not found: {user_id}")
        return None


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
        "user": UserAPISchema.model_validate(user)
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

    user = user_controller_instance.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

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

    user = user_controller_instance.user_map.get(user_id)
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required")

    return user_controller_instance.get_all_users()


@router.get("/{user_id}", response_model=UserAPISchema)
def get_user(
    user_id: str,
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

    current_user = user_controller_instance.user_map.get(current_user_id)

    if current_user_id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail=(
                "You can only view your own profile. "
                "Admin privileges required to view other profiles."
            )
        )

    user = user_controller_instance.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404,
                            detail=f"User with ID '{user_id}' not found")
    return user


@router.put("/{user_id}", response_model=UserAPISchema)
def update_user(
    user_id: str,
    user_data: UpdateUserSchema,
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

    current_user = user_controller_instance.user_map.get(current_user_id)

    if current_user_id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own profile"
        )

    return user_controller_instance.update_user_by_id(user_id, user_data)


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
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

    user = user_controller_instance.user_map.get(current_user_id)
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required")

    return user_controller_instance.delete_user_by_id(user_id)
