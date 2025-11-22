import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from keyboard_smashers.dao.report_dao import ReportDAO


@pytest.fixture
def temp_reports_csv():
    """Create a temporary reports CSV file for testing."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline=''
    )
    temp_path = temp_file.name
    temp_file.write("report_id,review_id,reporting_user_id,timestamp\n")
    temp_file.close()

    yield temp_path

    # Cleanup
    try:
        Path(temp_path).unlink()
    except Exception:
        pass


@pytest.fixture
def report_dao(temp_reports_csv):
    """Create a ReportDAO instance with temporary CSV."""
    return ReportDAO(csv_path=temp_reports_csv)


class TestReportDAO:

    def test_initialization(self, report_dao):
        """Test ReportDAO initializes correctly."""
        assert report_dao.reports == {}
        assert report_dao.reports_by_review == {}
        assert report_dao.reports_by_user == {}
        assert report_dao.report_counter == 1

    def test_create_report(self, report_dao):
        """Test creating a new report."""
        report = report_dao.create_report(
            review_id="review_000001",
            reporting_user_id="user_001"
        )

        assert report['report_id'] == "report_000001"
        assert report['review_id'] == "review_000001"
        assert report['reporting_user_id'] == "user_001"
        assert isinstance(report['timestamp'], datetime)
        assert report_dao.report_counter == 2

    def test_create_multiple_reports(self, report_dao):
        """Test creating multiple reports increments counter."""
        report1 = report_dao.create_report("review_001", "user_001")
        report2 = report_dao.create_report("review_002", "user_002")
        report3 = report_dao.create_report("review_001", "user_003")

        assert report1['report_id'] == "report_000001"
        assert report2['report_id'] == "report_000002"
        assert report3['report_id'] == "report_000003"
        assert report_dao.report_counter == 4

    def test_get_report(self, report_dao):
        """Test retrieving a specific report."""
        created = report_dao.create_report("review_001", "user_001")
        retrieved = report_dao.get_report("report_000001")

        assert retrieved is not None
        assert retrieved['report_id'] == created['report_id']
        assert retrieved['review_id'] == created['review_id']
        assert retrieved['reporting_user_id'] == created['reporting_user_id']

    def test_get_nonexistent_report(self, report_dao):
        """Test retrieving a report that doesn't exist."""
        result = report_dao.get_report("report_999999")
        assert result is None

    def test_get_all_reports(self, report_dao):
        """Test retrieving all reports."""
        report_dao.create_report("review_001", "user_001")
        report_dao.create_report("review_002", "user_002")
        report_dao.create_report("review_003", "user_003")

        all_reports = report_dao.get_all_reports()
        assert len(all_reports) == 3

    def test_get_reports_by_review(self, report_dao):
        """Test retrieving all reports for a specific review."""
        report_dao.create_report("review_001", "user_001")
        report_dao.create_report("review_001", "user_002")
        report_dao.create_report("review_002", "user_003")

        reports = report_dao.get_reports_by_review("review_001")
        assert len(reports) == 2
        assert all(r['review_id'] == "review_001" for r in reports)

    def test_get_reports_by_user(self, report_dao):
        """Test retrieving all reports by a specific user."""
        report_dao.create_report("review_001", "user_001")
        report_dao.create_report("review_002", "user_001")
        report_dao.create_report("review_003", "user_002")

        reports = report_dao.get_reports_by_user("user_001")
        assert len(reports) == 2
        assert all(r['reporting_user_id'] == "user_001" for r in reports)

    def test_has_user_reported_review(self, report_dao):
        """Test checking if user has already reported a review."""
        assert not report_dao.has_user_reported_review(
            "review_001", "user_001"
        )

        report_dao.create_report("review_001", "user_001")
        assert report_dao.has_user_reported_review(
            "review_001", "user_001"
        )
        assert not report_dao.has_user_reported_review(
            "review_001", "user_002"
        )

    def test_delete_reports_by_review(self, report_dao):
        """Test cascade deletion of reports when review is deleted."""
        report_dao.create_report("review_001", "user_001")
        report_dao.create_report("review_001", "user_002")
        report_dao.create_report("review_002", "user_003")

        count = report_dao.delete_reports_by_review("review_001")
        assert count == 2
        assert len(report_dao.get_reports_by_review("review_001")) == 0
        assert len(report_dao.get_all_reports()) == 1

    def test_persistence(self, temp_reports_csv):
        """Test that reports are persisted to CSV."""
        dao1 = ReportDAO(csv_path=temp_reports_csv)
        dao1.create_report("review_001", "user_001")
        dao1.create_report("review_002", "user_002")

        # Create new DAO instance to load from CSV
        dao2 = ReportDAO(csv_path=temp_reports_csv)
        assert len(dao2.reports) == 2
        assert dao2.report_counter == 3

    def test_indexing_maintained(self, report_dao):
        """Test that indexes are properly maintained."""
        report_dao.create_report("review_001", "user_001")
        report_dao.create_report("review_001", "user_002")
        report_dao.create_report("review_002", "user_001")

        assert "review_001" in report_dao.reports_by_review
        assert len(report_dao.reports_by_review["review_001"]) == 2
        assert "user_001" in report_dao.reports_by_user
        assert len(report_dao.reports_by_user["user_001"]) == 2

    def test_delete_report_by_id(self, report_dao):
        """Test deleting a specific report by ID."""
        report_dao.create_report("review_001", "user_001")
        report_dao.create_report("review_001", "user_002")
        report_dao.create_report("review_002", "user_003")

        # Delete one report
        success = report_dao.delete_report("report_000001")
        assert success is True
        assert len(report_dao.get_all_reports()) == 2
        assert report_dao.get_report("report_000001") is None
        
        # Verify indexes are updated
        assert len(report_dao.get_reports_by_review("review_001")) == 1
        assert len(report_dao.get_reports_by_user("user_001")) == 0

    def test_delete_nonexistent_report(self, report_dao):
        """Test deleting a report that doesn't exist."""
        success = report_dao.delete_report("report_999999")
        assert success is False

    def test_delete_report_cleans_up_empty_indexes(self, report_dao):
        """Test that deleting reports cleans up empty index lists."""
        report_dao.create_report("review_001", "user_001")
        
        # Delete the only report for this review/user
        report_dao.delete_report("report_000001")
        
        # Verify empty lists are removed from indexes
        assert "review_001" not in report_dao.reports_by_review
        assert "user_001" not in report_dao.reports_by_user

