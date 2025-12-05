from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Penalty:

    def __init__(
        self,
        penalty_id: str,
        user_id: str,
        reason: str,
        severity: int,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        issued_by: str = None,
        created_at: datetime = None
    ):
        self.penalty_id = penalty_id
        self.user_id = user_id
        self.reason = reason
        self.severity = self._validate_severity(severity)

        self.start_date = (
            start_date.replace(tzinfo=None) if start_date.tzinfo
            else start_date
        )
        self.end_date = (
            end_date.replace(tzinfo=None) if end_date and end_date.tzinfo
            else end_date
        )

        self.issued_by = issued_by
        self.created_at = created_at if created_at else datetime.now()

        logger.info(
            f"Penalty created: {penalty_id} for user {user_id} "
            f"(Severity: {severity})"
        )

    def _validate_severity(self, severity: int) -> int:
        if not isinstance(severity, int) or severity < 1 or severity > 5:
            logger.warning(
                f"Invalid severity {severity}, defaulting to 1"
            )
            return 1
        return severity

    def is_active(self) -> bool:
        now = datetime.now()

        if now < self.start_date:
            return False

        if self.end_date and now > self.end_date:
            return False

        return True

    def to_dict(self) -> dict:
        return {
            'penalty_id': self.penalty_id,
            'user_id': self.user_id,
            'reason': self.reason,
            'severity': self.severity,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'issued_by': self.issued_by,
            'created_at': self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Penalty':
        return cls(
            penalty_id=data['penalty_id'],
            user_id=data['user_id'],
            reason=data['reason'],
            severity=int(data['severity']),
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date'])
            if data.get('end_date') else None,
            issued_by=data.get('issued_by'),
            created_at=datetime.fromisoformat(data['created_at'])
        )
