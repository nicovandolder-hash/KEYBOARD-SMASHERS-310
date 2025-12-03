from fastapi import APIRouter, HTTPException, Depends, Query, Path, Cookie
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
import logging
from pathlib import Path as FilePath
from keyboard_smashers.dao.review_dao import review_dao_instance
from keyboard_smashers.dao.report_dao import ReportDAO
from keyboard_smashers.auth import get_current_user, get_current_admin_user

logger = logging.getLogger(__name__)

# Setup admin actions logger
admin_logger = logging.getLogger('admin_actions')
admin_logger.setLevel(logging.INFO)
if not admin_logger.handlers:
    log_dir = FilePath('logs')
    log_dir.mkdir(exist_ok=True)
    admin_handler = logging.FileHandler('logs/admin_actions.log')
    admin_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    )
    admin_logger.addHandler(admin_handler)


class ReviewSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    review_id: str = Field(..., description="Unique review ID")
    movie_id: str = Field(..., description="Movie ID being reviewed")
    user_id: Optional[str] = Field(
        None, description="User ID (null for IMDB reviews)")
    imdb_username: Optional[str] = Field(
        None, description="IMDB username for legacy reviews")
    rating: float = Field(..., description="Rating from 1-5", ge=1, le=5)
    review_text: str = Field(..., description="Review text content")
    review_date: str = Field(..., description="Review date")


class ReviewCreateSchema(BaseModel):
    movie_id: str = Field(..., description="Movie ID to review", min_length=1)
    rating: float = Field(..., description="Rating from 1-5", ge=1, le=5)
    review_text: str = Field(...,
                             description="Review text",
                             max_length=250,
                             min_length=1)


class ReviewUpdateSchema(BaseModel):
    rating: Optional[float] = Field(
        None, description="Rating from 1-5", ge=1, le=5)
    review_text: Optional[str] = Field(
        None, description="Review text", max_length=250)


class PaginatedReviewResponse(BaseModel):
    """Response model for paginated reviews"""
    reviews: List[ReviewSchema] = Field(
        ..., description="List of reviews for current page"
    )
    total: int = Field(..., description="Total reviews available")
    skip: int = Field(..., description="Number of reviews skipped")
    limit: int = Field(..., description="Maximum reviews per page")
    has_more: bool = Field(
        ..., description="Whether more reviews are available"
    )


class ReportedReviewSchema(BaseModel):
    """Schema combining report and review data"""
    report_id: str = Field(..., description="Report ID")
    review_id: str = Field(..., description="Reported review ID")
    reporting_user_id: str = Field(..., description="User who reported")
    reason: str = Field(..., description="Reason for report")
    admin_viewed: bool = Field(
        ..., description="Whether admin has viewed this report"
    )
    timestamp: str = Field(..., description="When report was created")
    # Review details
    review_text: str = Field(..., description="Review content")
    rating: float = Field(..., description="Review rating")
    movie_id: str = Field(..., description="Movie being reviewed")
    reviewer_user_id: Optional[str] = Field(
        None, description="User who wrote review (null for IMDB)"
    )
    imdb_username: Optional[str] = Field(
        None, description="IMDB username if legacy review"
    )


class PaginatedReportedReviewsResponse(BaseModel):
    """Response model for paginated reported reviews"""
    reports: List[ReportedReviewSchema] = Field(
        ..., description="List of reported reviews"
    )
    total: int = Field(..., description="Total reported reviews")
    skip: int = Field(..., description="Number of reports skipped")
    limit: int = Field(..., description="Maximum reports per page")
    has_more: bool = Field(
        ..., description="Whether more reports are available"
    )


class ReviewController:
    def __init__(
        self,
        imdb_csv_path: str = "data/imdb_reviews.csv",
        new_reviews_csv_path: str = "data/reviews_new.csv"
    ):
        self.review_dao = review_dao_instance
        self.report_dao = ReportDAO()
        logger.info(
            f"ReviewController initialized with "
            f"{len(self.review_dao.reviews)} reviews"
        )

    def _dict_to_schema(self, review_dict: dict) -> ReviewSchema:
        return ReviewSchema(**review_dict)

    def _filter_blocked_user_reviews(
        self,
        reviews: List[dict],
        current_user_id: str,
        user_dao=None
    ) -> List[dict]:
        """
        Filter out reviews from users who have blocked current user
        or whom current user has blocked.
        IMDB reviews (user_id is None) are always included.

        Args:
            reviews: List of review dictionaries
            current_user_id: ID of the current viewing user
            user_dao: Optional UserDAO instance for testing
        """
        if user_dao is None:
            from keyboard_smashers.controllers.user_controller import (
                user_controller_instance
            )
            user_dao = user_controller_instance.user_dao

        filtered_reviews = []
        for review in reviews:
            review_user_id = review.get('user_id')

            # Include IMDB reviews (no user_id)
            if review_user_id is None:
                filtered_reviews.append(review)
                continue

            # Check if blocked
            try:
                if not user_dao.is_blocked(current_user_id, review_user_id):
                    filtered_reviews.append(review)
                else:
                    logger.debug(
                        f"Filtered review {review.get('review_id')} "
                        f"from blocked user {review_user_id}"
                    )
            except (KeyError, ValueError, AttributeError):
                # If any error checking block status, include review
                filtered_reviews.append(review)

        return filtered_reviews

    def _filter_suspended_user_reviews(
        self,
        reviews: List[dict],
        user_dao=None
    ) -> List[dict]:
        """
        Filter out reviews from suspended users.
        IMDB reviews (user_id is None) are always included.

        Args:
            reviews: List of review dictionaries
            user_dao: Optional UserDAO instance for testing
        """
        if user_dao is None:
            from keyboard_smashers.controllers.user_controller import (
                user_controller_instance
            )
            user_dao = user_controller_instance.user_dao

        filtered_reviews = []
        for review in reviews:
            user_id = review.get('user_id')

            # Include IMDB reviews (no user_id)
            if user_id is None:
                filtered_reviews.append(review)
                continue

            # Check if user is suspended
            try:
                user_dict = user_dao.get_user(user_id)
                if not user_dict.get('is_suspended', False):
                    filtered_reviews.append(review)
                else:
                    logger.debug(
                        f"Filtered review {review.get('review_id')} "
                        f"from suspended user {user_id}"
                    )
            except (KeyError, ValueError, AttributeError):
                # User doesn't exist - include review anyway
                # (unit tests may not have user setup)
                filtered_reviews.append(review)

        return filtered_reviews

    def get_review_by_id(self, review_id: str) -> ReviewSchema:
        # Validate input
        if not review_id or not review_id.strip():
            raise HTTPException(
                status_code=400,
                detail="Review ID cannot be empty"
            )

        logger.info(f"Fetching review: {review_id}")
        try:
            review_dict = self.review_dao.get_review(review_id)
            return self._dict_to_schema(review_dict)
        except KeyError:
            logger.error(f"Review not found: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )

    def get_reviews_for_movie(
        self,
        movie_id: str,
        skip: int = 0,
        limit: int = 10,
        include_suspended: bool = False,
        current_user_id: Optional[str] = None
    ) -> PaginatedReviewResponse:
        # Validate inputs
        if not movie_id or not movie_id.strip():
            raise HTTPException(
                status_code=400,
                detail="Movie ID cannot be empty"
            )
        if skip < 0:
            raise HTTPException(
                status_code=400,
                detail="Skip must be non-negative"
            )
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 100"
            )

        logger.info(
            f"Fetching reviews for movie: {movie_id} "
            f"(skip={skip}, limit={limit}, "
            f"include_suspended={include_suspended})"
        )
        all_reviews = self.review_dao.get_reviews_for_movie(movie_id)

        # Filter suspended users' reviews unless explicitly included
        if not include_suspended:
            all_reviews = self._filter_suspended_user_reviews(all_reviews)

        # Filter blocked users if current user is authenticated
        if current_user_id:
            all_reviews = self._filter_blocked_user_reviews(
                all_reviews, current_user_id
            )

        total = len(all_reviews)

        # Apply pagination
        paginated_reviews = all_reviews[skip:skip + limit]

        logger.info(
            f"Found {total} total reviews (after filtering), returning "
            f"{len(paginated_reviews)} for movie: {movie_id}"
        )

        return PaginatedReviewResponse(
            reviews=[
                self._dict_to_schema(review) for review in paginated_reviews],
            total=total,
            skip=skip,
            limit=limit,
            has_more=(
                skip +
                limit) < total)

    def get_reviews_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 10,
        include_suspended: bool = False,
        current_user_id: Optional[str] = None
    ) -> PaginatedReviewResponse:
        # Validate inputs
        if not user_id or not user_id.strip():
            raise HTTPException(
                status_code=400,
                detail="User ID cannot be empty"
            )
        if skip < 0:
            raise HTTPException(
                status_code=400,
                detail="Skip must be non-negative"
            )
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 100"
            )

        logger.info(
            f"Fetching reviews by user: {user_id} "
            f"(skip={skip}, limit={limit}, "
            f"include_suspended={include_suspended})"
        )
        all_reviews = self.review_dao.get_reviews_by_user(user_id)

        # Filter if user is suspended (unless explicitly included)
        if not include_suspended:
            all_reviews = self._filter_suspended_user_reviews(all_reviews)

        # Filter blocked users if current user is authenticated
        if current_user_id:
            all_reviews = self._filter_blocked_user_reviews(
                all_reviews, current_user_id
            )

        total = len(all_reviews)

        # Apply pagination
        paginated_reviews = all_reviews[skip:skip + limit]

        logger.info(
            f"Found {total} total reviews (after filtering), returning "
            f"{len(paginated_reviews)} by user: {user_id}"
        )

        return PaginatedReviewResponse(
            reviews=[
                self._dict_to_schema(review) for review in paginated_reviews],
            total=total,
            skip=skip,
            limit=limit,
            has_more=(
                skip +
                limit) < total)

    def create_review(
        self,
        review_data: ReviewCreateSchema,
        user_id: str
    ) -> ReviewSchema:
        logger.info(
            f"Creating review for movie {review_data.movie_id} "
            f"by user {user_id}"
        )

        # Verify movie exists
        from keyboard_smashers.controllers.movie_controller import (
            movie_controller_instance
        )
        try:
            movie_controller_instance.get_movie_by_id(review_data.movie_id)
        except HTTPException:
            logger.error(f"Movie not found: {review_data.movie_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Movie with ID '{review_data.movie_id}' not found"
            )

        # Create review (DAO handles duplicate check)
        try:
            review_dict = review_data.model_dump()
            review_dict['user_id'] = user_id
            created_review = self.review_dao.create_review(review_dict)
            logger.info(
                f"Review created successfully: {created_review['review_id']}"
            )
            return self._dict_to_schema(created_review)
        except ValueError as e:
            # Duplicate review for this user/movie
            logger.warning(f"Duplicate review attempt: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )

    def update_review(
        self,
        review_id: str,
        review_data: ReviewUpdateSchema,
        current_user_id: str
    ) -> ReviewSchema:
        logger.info(f"Updating review: {review_id}")

        # Get existing review
        try:
            existing_review = self.review_dao.get_review(review_id)
        except KeyError:
            logger.error(f"Review not found for update: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )

        # Authorization check - only owner can update
        if existing_review.get('user_id') != current_user_id:
            logger.warning(
                f"Unauthorized update attempt on review {review_id} "
                f"by user {current_user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="You can only update your own reviews"
            )

        # Check if IMDB review (cannot be updated)
        if not existing_review.get('user_id'):
            logger.warning(
                f"Attempted to update IMDB review: {review_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Cannot update legacy IMDB reviews"
            )

        update_dict = review_data.model_dump(exclude_none=True)

        if not update_dict:
            raise HTTPException(
                status_code=400,
                detail="No fields to update"
            )

        try:
            updated_review = self.review_dao.update_review(
                review_id, update_dict)
            logger.info(f"Review updated successfully: {review_id}")
            return self._dict_to_schema(updated_review)
        except KeyError:
            logger.error(f"Review not found during update: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )

    def delete_review(self, review_id: str, current_user_id: str) -> dict:
        logger.info(f"Deleting review: {review_id}")

        # Get existing review
        try:
            existing_review = self.review_dao.get_review(review_id)
        except KeyError:
            logger.error(f"Review not found for deletion: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )

        # Authorization check - only owner can delete
        if existing_review.get('user_id') != current_user_id:
            logger.warning(
                f"Unauthorized delete attempt on review {review_id} "
                f"by user {current_user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own reviews"
            )

        # Check if IMDB review (cannot be deleted)
        if not existing_review.get('user_id'):
            logger.warning(
                f"Attempted to delete IMDB review: {review_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Cannot delete legacy IMDB reviews"
            )

        try:
            self.review_dao.delete_review(review_id)
            logger.info(f"Review deleted successfully: {review_id}")
            return {"message": f"Review '{review_id}' deleted successfully"}
        except KeyError:
            logger.error(f"Review not found during deletion: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )

    def admin_delete_review(self, review_id: str) -> dict:
        """Admin can delete any review (for moderation)"""
        logger.info(f"Admin deleting review: {review_id}")

        try:
            existing_review = self.review_dao.get_review(review_id)
        except KeyError:
            logger.error(f"Review not found for admin deletion: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )

        # Check if IMDB review (cannot be deleted)
        if not existing_review.get('user_id'):
            logger.warning(
                f"Admin attempted to delete IMDB review: {review_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Cannot delete legacy IMDB reviews"
            )

        try:
            # Delete the review
            self.review_dao.delete_review(review_id)

            # Cascade delete: remove all reports for this review
            deleted_reports = self.report_dao.delete_reports_by_review(
                review_id
            )

            # Log to admin actions
            admin_logger.info(
                f"ADMIN_DELETE_REVIEW - review_id={review_id}, "
                f"deleted_reports={deleted_reports}"
            )

            logger.info(
                f"Review {review_id} deleted by admin. "
                f"Removed {deleted_reports} associated reports."
            )
            return {
                "message": f"Review '{review_id}' deleted by admin",
                "deleted_reports": deleted_reports
            }
        except KeyError:
            logger.error(
                f"Review not found during admin deletion: {review_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Review with ID '{review_id}' not found"
            )

    def get_reported_reviews_for_admin(
        self,
        skip: int = 0,
        limit: int = 50,
        admin_viewed: Optional[bool] = None
    ) -> dict:
        """Get paginated list of reported reviews with review details"""
        # Validate inputs
        if skip < 0:
            raise HTTPException(
                status_code=400,
                detail="Skip must be non-negative"
            )
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 100"
            )

        logger.info(
            f"Admin fetching reported reviews (skip={skip}, limit={limit}, "
            f"admin_viewed={admin_viewed})"
        )

        # Get all reports
        all_reports = self.report_dao.get_all_reports()

        # Filter by admin_viewed status if specified
        if admin_viewed is not None:
            all_reports = [
                r for r in all_reports
                if r.get('admin_viewed', False) == admin_viewed
            ]

        # Sort by timestamp (newest first)
        all_reports.sort(
            key=lambda r: r['timestamp'],
            reverse=True
        )

        total = len(all_reports)

        # Apply pagination
        paginated_reports = all_reports[skip:skip + limit]

        # Enrich reports with review details
        enriched_reports = []
        for report in paginated_reports:
            try:
                review = self.review_dao.get_review(report['review_id'])
                enriched_reports.append({
                    'report_id': report['report_id'],
                    'review_id': report['review_id'],
                    'reporting_user_id': report['reporting_user_id'],
                    'reason': report.get('reason', ''),
                    'admin_viewed': report.get('admin_viewed', False),
                    'timestamp': report['timestamp'].isoformat(),
                    'review_text': review.get('review_text', ''),
                    'rating': review.get('rating', 0),
                    'movie_id': review.get('movie_id', ''),
                    'reviewer_user_id': review.get('user_id'),
                    'imdb_username': review.get('imdb_username')
                })
            except KeyError:
                # Review was deleted, skip this report
                logger.warning(
                    f"Review {report['review_id']} not found for "
                    f"report {report['report_id']}"
                )
                continue

        logger.info(
            f"Returning {len(enriched_reports)} reported reviews "
            f"out of {total} total"
        )

        return {
            'reports': enriched_reports,
            'total': total,
            'skip': skip,
            'limit': limit,
            'has_more': (skip + limit) < total
        }

    def mark_report_as_viewed(self, report_id: str) -> dict:
        """Mark a report as viewed by admin"""
        logger.info(f"Admin marking report as viewed: {report_id}")

        # Check if report exists
        report = self.report_dao.get_report(report_id)
        if not report:
            logger.error(f"Report not found: {report_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Report with ID '{report_id}' not found"
            )

        # Mark as viewed
        success = self.report_dao.mark_as_viewed(report_id)

        if success:
            # Log to admin actions
            admin_logger.info(
                f"ADMIN_VIEW_REPORT - report_id={report_id}, "
                f"review_id={report['review_id']}"
            )

            logger.info(f"Report {report_id} marked as viewed by admin")
            return {
                "message": f"Report '{report_id}' marked as viewed",
                "report_id": report_id,
                "admin_viewed": True
            }
        else:
            logger.error(f"Failed to mark report as viewed: {report_id}")
            raise HTTPException(
                status_code=500,
                detail="Failed to update report"
            )

    def admin_delete_report(self, report_id: str) -> dict:
        """Admin can delete a specific report"""
        logger.info(f"Admin deleting report: {report_id}")

        # Check if report exists
        report = self.report_dao.get_report(report_id)
        if not report:
            logger.error(f"Report not found for admin deletion: {report_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Report with ID '{report_id}' not found"
            )

        # Delete the report
        success = self.report_dao.delete_report(report_id)

        if success:
            # Log to admin actions
            admin_logger.info(
                f"ADMIN_DELETE_REPORT - report_id={report_id}, "
                f"review_id={report['review_id']}"
            )

            logger.info(f"Report {report_id} deleted by admin")
            return {
                "message": f"Report '{report_id}' deleted by admin",
                "review_id": report['review_id']
            }
        else:
            logger.error(f"Failed to delete report: {report_id}")
            raise HTTPException(
                status_code=500,
                detail="Failed to delete report"
            )


# Global instance
review_controller_instance = ReviewController()

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)


# PUBLIC ENDPOINTS

@router.get("/movie/{movie_id}", response_model=PaginatedReviewResponse)
def get_reviews_for_movie(
    movie_id: str = Path(..., min_length=1, max_length=100),
    skip: int = Query(0, ge=0, description="Number of reviews to skip"),
    limit: int = Query(
        10, ge=1, le=100, description="Maximum reviews to return"
    ),
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    """
    Get paginated reviews for a specific movie.
    If authenticated, filters out reviews from blocked users.

    - **skip**: Number of reviews to skip (default: 0)
    - **limit**: Maximum reviews to return (default: 10, max: 100)
    """
    from keyboard_smashers.auth import SessionManager

    # Validate session if token exists
    current_user_id = None
    if session_token:
        current_user_id = SessionManager.validate_session(session_token)

    return review_controller_instance.get_reviews_for_movie(
        movie_id, skip, limit, current_user_id=current_user_id
    )


@router.get("/user/{user_id}", response_model=PaginatedReviewResponse)
def get_reviews_by_user(
    user_id: str = Path(..., min_length=1, max_length=100),
    skip: int = Query(0, ge=0, description="Number of reviews to skip"),
    limit: int = Query(
        10, ge=1, le=100, description="Maximum reviews to return"
    ),
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    """
    Get paginated reviews by a specific user.
    If authenticated, filters out reviews from blocked users.

    - **skip**: Number of reviews to skip (default: 0)
    - **limit**: Maximum reviews to return (default: 10, max: 100)
    """
    from keyboard_smashers.auth import SessionManager

    # Validate session if token exists
    current_user_id = None
    if session_token:
        current_user_id = SessionManager.validate_session(session_token)

    return review_controller_instance.get_reviews_by_user(
        user_id, skip, limit, current_user_id=current_user_id
    )


@router.get("/{review_id}", response_model=ReviewSchema)
def get_review(review_id: str = Path(..., min_length=1, max_length=100)):
    """Get a specific review by ID"""
    return review_controller_instance.get_review_by_id(review_id)


# AUTHENTICATED ENDPOINTS (LOGGED-IN USERS)

@router.post("/", response_model=ReviewSchema, status_code=201)
def create_review(
    review_data: ReviewCreateSchema,
    current_user_id: str = Depends(get_current_user)
):
    """Create a new review (requires authentication)"""
    # Check if user is suspended
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )
    user = user_controller_instance.get_user_model_by_id(current_user_id)
    if user.is_suspended:
        raise HTTPException(
            status_code=403,
            detail="Cannot create review. Account is suspended."
        )

    return review_controller_instance.create_review(
        review_data, current_user_id)


@router.put("/{review_id}", response_model=ReviewSchema)
def update_review(
    review_id: str = Path(..., min_length=1, max_length=100),
    review_data: ReviewUpdateSchema = None,
    current_user_id: str = Depends(get_current_user)
):
    """Update your own review (requires authentication)"""
    return review_controller_instance.update_review(
        review_id, review_data, current_user_id
    )


@router.delete("/{review_id}")
def delete_review(
    review_id: str = Path(..., min_length=1, max_length=100),
    current_user_id: str = Depends(get_current_user)
):
    """Delete your own review (requires authentication)"""
    return review_controller_instance.delete_review(review_id, current_user_id)


@router.post("/{review_id}/report", status_code=201)
def report_review(
    review_id: str = Path(..., min_length=1, max_length=100),
    reason: str = Query(
        "", max_length=500, description="Reason for reporting"
    ),
    current_user_id: str = Depends(get_current_user)
):
    """Report a review for moderation (requires authentication)"""
    logger.info(f"User {current_user_id} reporting review {review_id}")

    # Check if review exists
    try:
        review_controller_instance.review_dao.get_review(review_id)
    except KeyError:
        logger.error(f"Review not found: {review_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Review with ID '{review_id}' not found"
        )

    # Check if user already reported this review
    if review_controller_instance.report_dao.has_user_reported_review(
        review_id, current_user_id
    ):
        logger.warning(
            f"User {current_user_id} already reported review {review_id}"
        )
        raise HTTPException(
            status_code=400,
            detail="You have already reported this review"
        )

    # Create the report
    report = review_controller_instance.report_dao.create_report(
        review_id=review_id,
        reporting_user_id=current_user_id,
        reason=reason
    )

    logger.info(f"Report created: {report['report_id']}")
    return {
        "message": "Review reported successfully",
        "report_id": report['report_id']
    }


# ADMIN-ONLY ENDPOINTS

@router.get(
    "/reports/admin",
    response_model=PaginatedReportedReviewsResponse
)
def admin_get_reported_reviews(
    skip: int = Query(
        0, ge=0, description="Number of reports to skip"
    ),
    limit: int = Query(
        50, ge=1, le=100, description="Maximum reports per page"
    ),
    admin_viewed: Optional[bool] = Query(
        None, description="Filter by viewed status"
    ),
    admin_user_id: str = Depends(get_current_admin_user)
):
    """Get paginated list of reported reviews (admin only)

    Args:
        skip: Number of reports to skip (pagination)
        limit: Maximum reports per page
        admin_viewed: Filter by viewed status
            (None=all, False=unviewed, True=viewed)
    """
    return review_controller_instance.get_reported_reviews_for_admin(
        skip=skip,
        limit=limit,
        admin_viewed=admin_viewed
    )


@router.patch("/reports/{report_id}/admin/view")
def admin_mark_report_viewed(
    report_id: str = Path(..., min_length=1, max_length=100),
    admin_user_id: str = Depends(get_current_admin_user)
):
    """Mark a report as viewed by admin (admin only)"""
    return review_controller_instance.mark_report_as_viewed(report_id)


@router.delete("/{review_id}/admin")
def admin_delete_review(
    review_id: str = Path(..., min_length=1, max_length=100),
    admin_user_id: str = Depends(get_current_admin_user)
):
    """Admin delete any review for moderation (requires admin privileges)"""
    return review_controller_instance.admin_delete_review(review_id)


@router.delete("/reports/{report_id}/admin")
def admin_delete_report(
    report_id: str = Path(..., min_length=1, max_length=100),
    admin_user_id: str = Depends(get_current_admin_user)
):
    """Admin delete a specific report (requires admin privileges)"""
    return review_controller_instance.admin_delete_report(report_id)


@router.get("/feed/following")
def get_following_feed(
    skip: int = 0,
    limit: int = 20,
    session_token: Optional[str] = Cookie(default=None, alias="session_token")
):
    """
    Get a feed of reviews from users you follow.
    Efficiently retrieves all reviews from followed users in one call.
    Returns reviews sorted by most recent first.
    
    Args:
        skip: Number of reviews to skip (pagination)
        limit: Maximum reviews to return (1-100)
        session_token: Authentication cookie
    """
    from keyboard_smashers.auth import SessionManager
    from keyboard_smashers.controllers.user_controller import (
        user_controller_instance
    )
    
    # Require authentication
    if not session_token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please login."
        )
    
    current_user_id = SessionManager.validate_session(session_token)
    if not current_user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session. Please login again."
        )
    
    # Validate pagination params
    if skip < 0:
        raise HTTPException(
            status_code=400,
            detail="Skip must be non-negative"
        )
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100"
        )
    
    # Get list of users current user follows
    try:
        following_users = user_controller_instance.user_dao.get_following(
            current_user_id
        )
        following_ids = [user['userid'] for user in following_users]
    except KeyError:
        following_ids = []
    
    if not following_ids:
        return {
            "reviews": [],
            "total": 0,
            "skip": skip,
            "limit": limit,
            "following_count": 0
        }
    
    # Get all reviews from followed users
    all_reviews = []
    for user_id in following_ids:
        user_reviews = review_controller_instance.review_dao.get_reviews_by_user(
            user_id
        )
        all_reviews.extend(user_reviews)
    
    # Filter suspended users
    all_reviews = review_controller_instance._filter_suspended_user_reviews(
        all_reviews
    )
    
    # Sort by creation date (newest first)
    # Assuming reviews have a timestamp field
    try:
        all_reviews.sort(
            key=lambda r: r.get('timestamp', ''),
            reverse=True
        )
    except (KeyError, TypeError):
        # If no timestamp, keep original order
        pass
    
    total = len(all_reviews)
    paginated = all_reviews[skip:skip + limit]
    
    return {
        "reviews": [
            review_controller_instance._dict_to_schema(review)
            for review in paginated
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
        "following_count": len(following_ids)
    }
