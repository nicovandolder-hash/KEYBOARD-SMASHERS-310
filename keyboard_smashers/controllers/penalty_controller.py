from fastapi import APIRouter, HTTPException, Cookie
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging
from keyboard_smashers.dao.user_dao import UserDAO
from keyboard_smashers.dao.penalty_dao import PenaltyDAO
from keyboard_smashers.models.penalty_model import Penalty

logger = logging.getLogger(__name__)


class PenaltyAPISchema(BaseModel):
    penalty_id: str = Field(..., description="Unique Penalty ID")
    user_id: str = Field(..., description="User ID this penalty applies to")
    reason: str = Field(..., description="Reason for the penalty")
    severity: int = Field(..., description="Severity level (1-5)", ge=1, le=5)
    start_date: datetime = Field(..., description="When penalty starts")
    end_date: Optional[datetime] = Field(None, description=(
        "When penalty ends (None = permanent)")
    )
    issued_by: Optional[str] = Field(None, description=(
        "Admin user ID who issued penalty")
    )
    created_at: datetime = Field(..., description="When penalty was created")
    is_active: bool = Field(..., description=(
        "Whether penalty is currently active")
    )

    class Config:
        from_attributes = True


class CreatePenaltySchema(BaseModel):
    user_id: str = Field(..., description="User ID to penalize")
    reason: str = Field(..., description="Reason for penalty", min_length=10)
    severity: int = Field(..., description="Severity level (1-5)", ge=1, le=5)
    start_date: Optional[datetime] = Field(None, description=(
        "When penalty starts (default: now)")
    )
    end_date: Optional[datetime] = Field(None, description=(
        "When penalty ends (None = permanent)")
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_000",
                "reason": "Post does not follow community guidelines",
                "severity": 3,
                "start_date": datetime.now().replace(
                    hour=12, minute=0, second=0, microsecond=0).isoformat(),
                "end_date": (datetime.now() + timedelta(days=7)).replace(
                    hour=12, minute=0, second=0, microsecond=0).isoformat()
            }
        }


class UpdatePenaltySchema(BaseModel):
    reason: Optional[str] = Field(None, description=(
        "Updated reason"), min_length=10)
    severity: Optional[int] = Field(None, description=(
        "Updated severity (1-5)"), ge=1, le=5)
    start_date: Optional[datetime] = Field(None, description=(
        "Updated start date")
    )
    end_date: Optional[datetime] = Field(None, description="Updated end date")


class PenaltySummarySchema(BaseModel):
    """Response model for user penalty summary"""
    user_id: str = Field(..., description="User ID")
    active_penalties: List[PenaltyAPISchema] = Field(
        ..., description="Currently active penalties"
    )
    historical_penalties: List[PenaltyAPISchema] = Field(
        ..., description="Past/inactive penalties"
    )
    total_active: int = Field(..., description="Count of active penalties")
    total_historical: int = Field(
        ..., description="Count of historical penalties"
    )


class PaginatedPenaltyResponse(BaseModel):
    """Response model for paginated penalties"""
    penalties: List[PenaltyAPISchema] = Field(
        ..., description="List of penalties for current page"
    )
    total: int = Field(..., description="Total penalties available")
    skip: int = Field(..., description="Number of penalties skipped")
    limit: int = Field(..., description="Maximum penalties per page")
    has_more: bool = Field(
        ..., description="Whether more penalties are available"
    )


class PenaltyController:

    penalty_dao = None
    user_dao = None

    def __init__(
        self,
        penalty_csv_path: str = "data/penalties.csv",
        user_csv_path: str = "data/users.csv"
    ):
        if PenaltyController.penalty_dao is None:
            PenaltyController.penalty_dao = (
                PenaltyDAO(csv_path=penalty_csv_path)
            )
        if PenaltyController.user_dao is None:
            PenaltyController.user_dao = UserDAO(csv_path=user_csv_path)
        else:
            PenaltyController.user_dao = UserDAO(csv_path=user_csv_path)
        self.penalty_dao = PenaltyController.penalty_dao
        self.user_dao = PenaltyController.user_dao
        logger.info(
            f"PenaltyController initialized with "
            f"{len(self.penalty_dao.penalties)} penalties"
        )

    def penalty_to_schema(self, penalty: Penalty) -> PenaltyAPISchema:
        return PenaltyAPISchema(
            penalty_id=penalty.penalty_id,
            user_id=penalty.user_id,
            reason=penalty.reason,
            severity=penalty.severity,
            start_date=penalty.start_date,
            end_date=penalty.end_date,
            issued_by=penalty.issued_by,
            created_at=penalty.created_at,
            is_active=penalty.is_active()
        )

    def create_penalty(
        self,
        penalty_data: CreatePenaltySchema,
        admin_id: str
    ) -> PenaltyAPISchema:
        logger.info(
            f"Admin {admin_id} creating penalty for user"
            f" {penalty_data.user_id}"
        )

        self.user_dao.load_users()

        try:
            self.user_dao.get_user(penalty_data.user_id)
        except KeyError:
            logger.error(f"User {penalty_data.user_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"User '{penalty_data.user_id}' not found"
            )

        penalty_dict = {
            'user_id': penalty_data.user_id,
            'reason': penalty_data.reason,
            'severity': penalty_data.severity,
            'start_date': penalty_data.start_date if (
                penalty_data.start_date) else datetime.now(),
            'end_date': penalty_data.end_date if penalty_data.end_date else (
                datetime.now() + timedelta(days=7)),
            'issued_by': admin_id
        }

        try:
            penalty = self.penalty_dao.create_penalty(penalty_dict)

            self.user_dao.increment_penalty_count(penalty_data.user_id)

            logger.info(
                f"Penalty {penalty.penalty_id} created for user "
                f"{penalty_data.user_id}"
            )
            return self.penalty_to_schema(penalty)

        except Exception as e:
            logger.error(f"Error creating penalty: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    def get_penalty_by_id(self, penalty_id: str) -> PenaltyAPISchema:
        logger.debug(f"Retrieving penalty: {penalty_id}")

        try:
            self.user_dao.load_users()
            penalty = self.penalty_dao.get_penalty(penalty_id)
            return self.penalty_to_schema(penalty)
        except KeyError:
            logger.error(f"Penalty {penalty_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Penalty '{penalty_id}' not found"
            )

    def get_all_penalties(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> PaginatedPenaltyResponse:
        logger.debug(
            f"Retrieving penalties (status={status}, user_id={user_id}, "
            f"skip={skip}, limit={limit})"
        )

        penalties = self.penalty_dao.get_all_penalties()

        if user_id:
            try:
                self.user_dao.load_users()
                self.user_dao.get_user(user_id)
                penalties = self.penalty_dao.get_penalties_by_user(user_id)
            except KeyError:
                raise HTTPException(
                    status_code=404,
                    detail=f"User '{user_id}' not found"
                )

        if status == "active":
            penalties = [p for p in penalties if p.is_active()]
        elif status == "inactive":
            penalties = [p for p in penalties if not p.is_active()]
        elif status is not None:
            raise HTTPException(
                status_code=400,
                detail="Invalid status. Must be 'active' or 'inactive'"
            )

        total = len(penalties)
        paginated_penalties = penalties[skip:skip + limit]

        logger.info(
            f"Found {total} total penalties, returning "
            f"{len(paginated_penalties)}"
        )

        return PaginatedPenaltyResponse(
            penalties=[self.penalty_to_schema(p) for p in paginated_penalties],
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + limit) < total
        )

    def update_penalty(
        self,
        penalty_id: str,
        penalty_data: UpdatePenaltySchema
    ) -> PenaltyAPISchema:
        logger.info(f"Updating penalty: {penalty_id}")

        try:
            self.user_dao.load_users()
            update_dict = {}

            if penalty_data.reason is not None:
                update_dict['reason'] = penalty_data.reason
            if penalty_data.severity is not None:
                update_dict['severity'] = penalty_data.severity
            if penalty_data.start_date is not None:
                update_dict['start_date'] = penalty_data.start_date
            if penalty_data.end_date is not None:
                update_dict['end_date'] = penalty_data.end_date

            if not update_dict:
                penalty = self.penalty_dao.get_penalty(penalty_id)
                return self.penalty_to_schema(penalty)

            penalty = self.penalty_dao.update_penalty(penalty_id, update_dict)
            logger.info(f"Updated penalty: {penalty_id}")
            return self.penalty_to_schema(penalty)

        except KeyError:
            logger.error(f"Penalty {penalty_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Penalty '{penalty_id}' not found"
            )
        except Exception as e:
            logger.error(f"Error updating penalty: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    def delete_penalty(self, penalty_id: str) -> dict:
        logger.info(f"Deleting penalty: {penalty_id}")

        try:
            self.penalty_dao.delete_penalty(penalty_id)
            logger.info(f"Deleted penalty: {penalty_id}")
            return {"message": f"Penalty '{penalty_id}' deleted successfully"}
        except KeyError:
            logger.error(f"Penalty {penalty_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Penalty '{penalty_id}' not found"
            )

    def get_user_penalty_summary(self, user_id: str) -> PenaltySummarySchema:
        """Get summary of active and historical penalties for a user"""
        logger.info(f"Fetching penalty summary for user: {user_id}")

        try:
            self.user_dao.load_users()
            self.user_dao.get_user(user_id)
        except KeyError:
            raise HTTPException(
                status_code=404,
                detail=f"User '{user_id}' not found"
            )

        all_penalties = self.penalty_dao.get_penalties_by_user(user_id)
        active = [p for p in all_penalties if p.is_active()]
        historical = [p for p in all_penalties if not p.is_active()]

        logger.info(
            f"User {user_id} has {len(active)} active "
            f"and {len(historical)} historical penalties"
        )

        return PenaltySummarySchema(
            user_id=user_id,
            active_penalties=[self.penalty_to_schema(p) for p in active],
            historical_penalties=[
                self.penalty_to_schema(p) for p in historical
            ],
            total_active=len(active),
            total_historical=len(historical)
        )


penalty_controller_instance = PenaltyController()

router = APIRouter(
    prefix="/penalties",
    tags=["penalties"],
)


@router.get("/my-penalties", response_model=PaginatedPenaltyResponse)
def get_my_penalties(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    """Get paginated list of current user's penalties

    - **status**: Filter by 'active' or 'inactive' (optional)
    - **skip**: Number of penalties to skip (default: 0)
    - **limit**: Maximum penalties to return (default: 50, max: 100)
    """
    from keyboard_smashers.auth import SessionManager

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = SessionManager.validate_session(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Enforce max limit
    limit = min(limit, 100)

    return penalty_controller_instance.get_all_penalties(
        status=status,
        user_id=user_id,
        skip=skip,
        limit=limit
    )


@router.get("/user/{user_id}/summary", response_model=PenaltySummarySchema)
def get_user_penalty_summary(
    user_id: str,
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    """Get summary of active and historical penalties for a user

    Returns both active and historical penalties separately with counts.
    Accessible by admins or the user themselves.
    """
    from keyboard_smashers.auth import SessionManager
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    requester_id = SessionManager.validate_session(session_token)
    if not requester_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    requester = user_controller_instance.get_user_model_by_id(requester_id)

    # Allow access if requester is admin OR requesting their own penalties
    if not requester.is_admin and requester_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only view your own penalty summary"
        )

    return penalty_controller_instance.get_user_penalty_summary(user_id)


# ---------------- PROTECTED ADMIN ONLY ENDPOINTS ----------------

@router.post("/", response_model=PenaltyAPISchema, status_code=201)
def create_penalty(
    penalty_data: CreatePenaltySchema,
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):

    from keyboard_smashers.auth import SessionManager
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    admin_id = SessionManager.validate_session(session_token)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    admin = user_controller_instance.get_user_model_by_id(admin_id)
    if not admin.is_admin:
        raise HTTPException(status_code=403, detail=(
            "Admin privileges required")
        )

    return penalty_controller_instance.create_penalty(penalty_data, admin_id)


@router.get("/", response_model=PaginatedPenaltyResponse)
def get_all_penalties(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    """Get paginated list of all penalties (admin only)

    - **status**: Filter by 'active' or 'inactive' (optional)
    - **user_id**: Filter by specific user (optional)
    - **skip**: Number of penalties to skip (default: 0)
    - **limit**: Maximum penalties to return (default: 50, max: 100)
    """
    from keyboard_smashers.auth import SessionManager
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    admin_id = SessionManager.validate_session(session_token)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    admin = user_controller_instance.get_user_model_by_id(admin_id)
    if not admin.is_admin:
        raise HTTPException(status_code=403, detail=(
            "Admin privileges required")
        )

    # Enforce max limit
    limit = min(limit, 100)

    return penalty_controller_instance.get_all_penalties(
        status=status, user_id=user_id, skip=skip, limit=limit)


@router.get("/{penalty_id}", response_model=PenaltyAPISchema)
def get_penalty(
    penalty_id: str,
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    from keyboard_smashers.auth import SessionManager
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    admin_id = SessionManager.validate_session(session_token)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    admin = user_controller_instance.get_user_model_by_id(admin_id)
    if not admin.is_admin:
        raise HTTPException(status_code=403, detail=(
            "Admin privileges required")
        )

    return penalty_controller_instance.get_penalty_by_id(penalty_id)


@router.put("/{penalty_id}", response_model=PenaltyAPISchema)
def update_penalty(
    penalty_id: str,
    penalty_data: UpdatePenaltySchema,
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    from keyboard_smashers.auth import SessionManager
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    admin_id = SessionManager.validate_session(session_token)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    admin = user_controller_instance.get_user_model_by_id(admin_id)
    if not admin.is_admin:
        raise HTTPException(status_code=403, detail=(
            "Admin privileges required")
        )

    return penalty_controller_instance.update_penalty(penalty_id, penalty_data)


@router.delete("/{penalty_id}")
def delete_penalty(
    penalty_id: str,
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    from keyboard_smashers.auth import SessionManager
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    admin_id = SessionManager.validate_session(session_token)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    admin = user_controller_instance.get_user_model_by_id(admin_id)
    if not admin.is_admin:
        raise HTTPException(status_code=403, detail=(
            "Admin privileges required")
        )

    return penalty_controller_instance.delete_penalty(penalty_id)
