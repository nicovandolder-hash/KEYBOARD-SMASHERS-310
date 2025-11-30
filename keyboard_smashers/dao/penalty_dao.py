import csv
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from keyboard_smashers.models.penalty_model import Penalty

logger = logging.getLogger(__name__)


class PenaltyDAO:

    def __init__(self, csv_path: str = "data/penalties.csv"):
        self.csv_path = csv_path
        self.penalties: Dict[str, Penalty] = {}
        self.user_penalties: Dict[str, List[str]] = {}
        self.penalty_counter = 1
        self.load_penalties()

    def load_penalties(self) -> None:
        csv_file = Path(self.csv_path)
        if not csv_file.exists():
            logger.warning(f"Penalty CSV file not found at: {self.csv_path}")
            return

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    penalty = Penalty(
                        penalty_id=row['penalty_id'],
                        user_id=row['user_id'],
                        reason=row['reason'],
                        severity=int(row['severity']),
                        start_date=datetime.fromisoformat(row['start_date']),
                        end_date=datetime.fromisoformat(row['end_date'])
                        if row.get('end_date') else None,
                        issued_by=row.get('issued_by'),
                        created_at=datetime.fromisoformat(row['created_at'])
                    )

                    self.penalties[penalty.penalty_id] = penalty

                    if penalty.user_id not in self.user_penalties:
                        self.user_penalties[penalty.user_id] = []
                    self.user_penalties[penalty.user_id].append(
                        penalty.penalty_id
                        )

                    if penalty.penalty_id.startswith("penalty_"):
                        try:
                            penalty_num = int(penalty.penalty_id.split("_")[1])
                            self.penalty_counter = max(
                                self.penalty_counter,
                                penalty_num + 1
                            )
                        except (IndexError, ValueError):
                            pass

            logger.info(
                f"Loaded {len(self.penalties)} penalties from {self.csv_path}"
            )
        except Exception as e:
            logger.error(f"Error loading penalties from {self.csv_path}: {e}")
            raise

    def save_penalties(self) -> None:
        try:
            csv_file = Path(self.csv_path)
            csv_file.parent.mkdir(parents=True, exist_ok=True)

            with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                fieldnames = [
                    'penalty_id',
                    'user_id',
                    'reason',
                    'severity',
                    'start_date',
                    'end_date',
                    'issued_by',
                    'created_at'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for penalty in self.penalties.values():
                    writer.writerow(penalty.to_dict())

            logger.info(
                f"Saved {len(self.penalties)} penalties to {self.csv_path}"
            )
        except Exception as e:
            logger.error(f"Error saving penalties to CSV: {e}")
            raise

    def create_penalty(self, penalty_data: Dict[str, Any]) -> Penalty:
        penalty_id = f"penalty_{self.penalty_counter:03d}"
        self.penalty_counter += 1

        penalty = Penalty(
            penalty_id=penalty_id,
            user_id=penalty_data['user_id'],
            reason=penalty_data['reason'],
            severity=penalty_data['severity'],
            start_date=penalty_data.get('start_date', datetime.now()),
            end_date=penalty_data.get('end_date'),
            issued_by=penalty_data.get('issued_by'),
            created_at=datetime.now()
        )

        self.penalties[penalty_id] = penalty

        if penalty.user_id not in self.user_penalties:
            self.user_penalties[penalty.user_id] = []
        self.user_penalties[penalty.user_id].append(penalty_id)

        self.save_penalties()
        logger.info(f"Created penalty: {penalty_id}"
                    f" for user {penalty.user_id}")
        return penalty

    def get_penalty(self, penalty_id: str) -> Penalty:
        if penalty_id not in self.penalties:
            raise KeyError(f"Penalty with ID '{penalty_id}' not found")
        return self.penalties[penalty_id]

    def get_penalties_by_user(self, user_id: str) -> List[Penalty]:
        penalty_ids = self.user_penalties.get(user_id, [])
        return [self.penalties[pid] for pid in penalty_ids]

    def get_active_penalties_by_user(self, user_id: str) -> List[Penalty]:
        penalties = self.get_penalties_by_user(user_id)
        return [p for p in penalties if p.is_active()]

    def get_all_penalties(self) -> List[Penalty]:
        return list(self.penalties.values())

    def update_penalty(
        self,
        penalty_id: str,
        data: Dict[str, Any]
    ) -> Penalty:
        if penalty_id not in self.penalties:
            raise KeyError(f"Penalty with ID '{penalty_id}' not found")

        penalty = self.penalties[penalty_id]

        if 'reason' in data:
            penalty.reason = data['reason']
        if 'severity' in data:
            penalty.severity = penalty._validate_severity(data['severity'])
        if 'start_date' in data:
            penalty.start_date = data['start_date']
            start_date = data['start_date']
            penalty.start_date = (
               start_date.replace(tzinfo=None) if start_date.tzinfo
               else start_date
            )
        if 'end_date' in data:
            penalty.end_date = data['end_date']
            end_date = data['end_date']
            penalty.end_date = (
              end_date.replace(tzinfo=None) if end_date and end_date.tzinfo
              else end_date
            )

        self.save_penalties()
        logger.info(f"Updated penalty: {penalty_id}")
        return penalty

    def delete_penalty(self, penalty_id: str) -> None:
        if penalty_id not in self.penalties:
            raise KeyError(f"Penalty with ID '{penalty_id}' not found")

        penalty = self.penalties[penalty_id]

        if penalty.user_id in self.user_penalties:
            self.user_penalties[penalty.user_id].remove(penalty_id)
            if not self.user_penalties[penalty.user_id]:
                del self.user_penalties[penalty.user_id]

        del self.penalties[penalty_id]
        self.save_penalties()
        logger.info(f"Deleted penalty: {penalty_id}")

    def get_penalty_count_by_user(self, user_id: str) -> int:
        return len(self.user_penalties.get(user_id, []))
