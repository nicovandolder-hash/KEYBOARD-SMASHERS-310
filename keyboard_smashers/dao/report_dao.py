import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportDAO:

    def __init__(self, csv_path: str = "data/reports.csv"):
        self.csv_path = csv_path
        self.reports: Dict[str, Dict[str, Any]] = {}
        # Index for fast lookups by review_id
        self.reports_by_review: Dict[str, List[str]] = {}
        # Index for fast lookups by reporting user
        self.reports_by_user: Dict[str, List[str]] = {}
        self.report_counter = 1
        self.load_reports()

    def load_reports(self) -> None:
        csv_file = Path(self.csv_path)
        if not csv_file.exists():
            logger.warning(f"Report CSV file not found at: {self.csv_path}")
            return

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    report = {
                        'report_id': row['report_id'],
                        'review_id': row['review_id'],
                        'reporting_user_id': row['reporting_user_id'],
                        'reason': row.get('reason', ''),
                        'admin_viewed': row.get(
                            'admin_viewed', 'False'
                        ) == 'True',
                        'timestamp': datetime.fromisoformat(row['timestamp'])
                    }

                    self.reports[report['report_id']] = report

                    # Index by review_id
                    review_id = report['review_id']
                    if review_id not in self.reports_by_review:
                        self.reports_by_review[review_id] = []
                    self.reports_by_review[review_id].append(
                        report['report_id']
                    )

                    # Index by reporting_user_id
                    user_id = report['reporting_user_id']
                    if user_id not in self.reports_by_user:
                        self.reports_by_user[user_id] = []
                    self.reports_by_user[user_id].append(report['report_id'])

                    # Update counter for ID generation
                    if report['report_id'].startswith("report_"):
                        try:
                            report_num = int(report['report_id'].split("_")[1])
                            self.report_counter = max(
                                self.report_counter,
                                report_num + 1
                            )
                        except (IndexError, ValueError):
                            pass

            logger.info(
                f"Loaded {len(self.reports)} reports from {self.csv_path}"
            )
        except Exception as e:
            logger.error(f"Error loading reports from {self.csv_path}: {e}")
            raise

    def save_reports(self) -> None:
        try:
            csv_file = Path(self.csv_path)
            csv_file.parent.mkdir(parents=True, exist_ok=True)

            with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                fieldnames = [
                    'report_id',
                    'review_id',
                    'reporting_user_id',
                    'reason',
                    'admin_viewed',
                    'timestamp'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for report in self.reports.values():
                    writer.writerow({
                        'report_id': report['report_id'],
                        'review_id': report['review_id'],
                        'reporting_user_id': report['reporting_user_id'],
                        'reason': report.get('reason', ''),
                        'admin_viewed': report.get('admin_viewed', False),
                        'timestamp': report['timestamp'].isoformat()
                    })

            logger.info(
                f"Saved {len(self.reports)} reports to {self.csv_path}"
            )
        except Exception as e:
            logger.error(f"Error saving reports to {self.csv_path}: {e}")
            raise

    def create_report(
        self,
        review_id: str,
        reporting_user_id: str,
        reason: str = ""
    ) -> Dict[str, Any]:
        """Create a new report for a review"""
        report_id = f"report_{str(self.report_counter).zfill(6)}"
        self.report_counter += 1

        report = {
            'report_id': report_id,
            'review_id': review_id,
            'reporting_user_id': reporting_user_id,
            'reason': reason,
            'admin_viewed': False,
            'timestamp': datetime.now()
        }

        self.reports[report_id] = report

        # Update indexes
        if review_id not in self.reports_by_review:
            self.reports_by_review[review_id] = []
        self.reports_by_review[review_id].append(report_id)

        if reporting_user_id not in self.reports_by_user:
            self.reports_by_user[reporting_user_id] = []
        self.reports_by_user[reporting_user_id].append(report_id)

        self.save_reports()
        logger.info(
            f"Created report {report_id} for review {review_id} "
            f"by user {reporting_user_id}"
        )

        return report.copy()

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific report by ID"""
        if report_id not in self.reports:
            return None
        return self.reports[report_id].copy()

    def get_all_reports(self) -> List[Dict[str, Any]]:
        """Get all reports"""
        return [report.copy() for report in self.reports.values()]

    def get_reports_by_review(self, review_id: str) -> List[Dict[str, Any]]:
        """Get all reports for a specific review"""
        report_ids = self.reports_by_review.get(review_id, [])
        return [
            self.reports[report_id].copy()
            for report_id in report_ids
        ]

    def get_reports_by_user(
        self,
        reporting_user_id: str
    ) -> List[Dict[str, Any]]:
        """Get all reports submitted by a specific user"""
        report_ids = self.reports_by_user.get(reporting_user_id, [])
        return [
            self.reports[report_id].copy()
            for report_id in report_ids
        ]

    def has_user_reported_review(
        self,
        review_id: str,
        reporting_user_id: str
    ) -> bool:
        """Check if a user has already reported a specific review"""
        reports = self.get_reports_by_review(review_id)
        return any(
            report['reporting_user_id'] == reporting_user_id
            for report in reports
        )

    def delete_reports_by_review(self, review_id: str) -> int:
        """Delete all reports for a specific review (cascade delete)"""
        report_ids = self.reports_by_review.get(review_id, [])
        count = len(report_ids)

        for report_id in report_ids:
            report = self.reports.get(report_id)
            if report:
                # Remove from user index
                user_id = report['reporting_user_id']
                if user_id in self.reports_by_user:
                    if report_id in self.reports_by_user[user_id]:
                        self.reports_by_user[user_id].remove(report_id)

                # Remove from reports dict
                del self.reports[report_id]

        # Remove review from index
        if review_id in self.reports_by_review:
            del self.reports_by_review[review_id]

        if count > 0:
            self.save_reports()
            logger.info(
                f"Deleted {count} reports for review {review_id}"
            )

        return count

    def mark_as_viewed(self, report_id: str) -> bool:
        """Mark a report as viewed by an admin"""
        if report_id not in self.reports:
            logger.warning(f"Report {report_id} not found")
            return False

        self.reports[report_id]['admin_viewed'] = True
        self.save_reports()
        logger.info(f"Report {report_id} marked as viewed")
        return True

    def delete_report(self, report_id: str) -> bool:
        """Delete a specific report by ID"""
        if report_id not in self.reports:
            logger.warning(f"Report {report_id} not found")
            return False

        report = self.reports[report_id]
        review_id = report['review_id']
        user_id = report['reporting_user_id']

        # Remove from review index
        if review_id in self.reports_by_review:
            if report_id in self.reports_by_review[review_id]:
                self.reports_by_review[review_id].remove(report_id)
            # Clean up empty lists
            if not self.reports_by_review[review_id]:
                del self.reports_by_review[review_id]

        # Remove from user index
        if user_id in self.reports_by_user:
            if report_id in self.reports_by_user[user_id]:
                self.reports_by_user[user_id].remove(report_id)
            # Clean up empty lists
            if not self.reports_by_user[user_id]:
                del self.reports_by_user[user_id]

        # Remove from reports dict
        del self.reports[report_id]

        self.save_reports()
        logger.info(f"Deleted report {report_id}")
        return True
