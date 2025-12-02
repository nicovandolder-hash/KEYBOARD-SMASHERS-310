from keyboard_smashers.models.penalty_model import Penalty
from keyboard_smashers.controllers.penalty_controller import (
    PenaltyController,
    CreatePenaltySchema,
    UpdatePenaltySchema,
    PenaltyAPISchema
)
import pytest
from fastapi import HTTPException
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                '../..')))


@pytest.fixture
def mock_penalty_dao():
    with patch(
              'keyboard_smashers.controllers.penalty_controller.PenaltyDAO'
              ) as mock:
        dao_instance = Mock()
        mock.return_value = dao_instance
        dao_instance.penalties = {}
        yield dao_instance


@pytest.fixture
def mock_user_dao():
    with patch(
              'keyboard_smashers.controllers.penalty_controller.UserDAO'
              ) as mock:
        dao_instance = Mock()
        mock.return_value = dao_instance
        yield dao_instance


@pytest.fixture
def penalty_controller(mock_penalty_dao, mock_user_dao):
    PenaltyController.penalty_dao = None
    PenaltyController.user_dao = None

    controller = PenaltyController(
        penalty_csv_path="test_penalties.csv",
        user_csv_path="test_users.csv"
    )
    return controller


@pytest.fixture
def sample_penalty():
    return Penalty(
        penalty_id="penalty_001",
        user_id="user_001",
        reason="Test violation of community guidelines",
        severity=3,
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=7),
        issued_by="admin_001",
        created_at=datetime.now()
    )


class TestPenaltyControllerCreate:

    def test_create_penalty_success(
            self, penalty_controller, mock_penalty_dao, mock_user_dao):
        penalty_data = CreatePenaltySchema(
            user_id="user_001",
            reason="Violated community guidelines repeatedly",
            severity=3
        )

        mock_user_dao.get_user.return_value = {"userid": "user_001"}
        mock_penalty_dao.create_penalty.return_value = Penalty(
            penalty_id="penalty_001",
            user_id="user_001",
            reason="Violated community guidelines repeatedly",
            severity=3,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7),
            issued_by="admin_001",
            created_at=datetime.now()
        )

        result = penalty_controller.create_penalty(penalty_data, "admin_001")

        assert isinstance(result, PenaltyAPISchema)
        assert result.user_id == "user_001"
        assert result.severity == 3
        assert result.issued_by == "admin_001"
        mock_user_dao.load_users.assert_called_once()
        mock_user_dao.increment_penalty_count.assert_called_once_with(
            "user_001")

    def test_create_penalty_user_not_found(
            self, penalty_controller, mock_user_dao):
        penalty_data = CreatePenaltySchema(
            user_id="nonexistent_user",
            reason="Test reason that is long enough",
            severity=2
        )

        mock_user_dao.get_user.side_effect = KeyError("User not found")

        with pytest.raises(HTTPException) as exc_info:
            penalty_controller.create_penalty(penalty_data, "admin_001")

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    def test_create_penalty_dao_error(self, penalty_controller,
                                      mock_penalty_dao, mock_user_dao):
        penalty_data = CreatePenaltySchema(
            user_id="user_001",
            reason="Test reason that is long enough",
            severity=2
        )

        mock_user_dao.get_user.return_value = {"userid": "user_001"}
        mock_penalty_dao.create_penalty.side_effect = Exception(
            "Database error")

        with pytest.raises(HTTPException) as exc_info:
            penalty_controller.create_penalty(penalty_data, "admin_001")

        assert exc_info.value.status_code == 400

    def test_create_penalty_increments_user_penalty_count(
            self, penalty_controller, mock_penalty_dao, mock_user_dao):
        penalty_data = CreatePenaltySchema(
            user_id="user_001",
            reason="Violation of terms of service",
            severity=4
        )

        mock_user_dao.get_user.return_value = {"userid": "user_001"}
        mock_penalty_dao.create_penalty.return_value = Penalty(
            penalty_id="penalty_001",
            user_id="user_001",
            reason="Violation of terms of service",
            severity=4,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7),
            issued_by="admin_001",
            created_at=datetime.now()
        )

        penalty_controller.create_penalty(penalty_data, "admin_001")

        mock_user_dao.increment_penalty_count.assert_called_once_with(
            "user_001")


class TestPenaltyControllerRead:

    def test_get_penalty_by_id_success(
            self, penalty_controller, mock_penalty_dao, sample_penalty):
        mock_penalty_dao.get_penalty.return_value = sample_penalty

        result = penalty_controller.get_penalty_by_id("penalty_001")

        assert isinstance(result, PenaltyAPISchema)
        assert result.penalty_id == "penalty_001"
        mock_penalty_dao.get_penalty.assert_called_once_with("penalty_001")

    def test_get_penalty_by_id_not_found(
            self, penalty_controller, mock_penalty_dao):
        mock_penalty_dao.get_penalty.side_effect = KeyError(
            "Penalty not found")

        with pytest.raises(HTTPException) as exc_info:
            penalty_controller.get_penalty_by_id("penalty_999")

        assert exc_info.value.status_code == 404
        assert "penalty_999" in str(exc_info.value.detail).lower()

    def test_get_all_penalties_no_filters(
            self, penalty_controller, mock_penalty_dao, sample_penalty):
        mock_penalty_dao.get_all_penalties.return_value = [sample_penalty]

        result = penalty_controller.get_all_penalties()

        assert len(result.penalties) == 1
        assert isinstance(result.penalties[0], PenaltyAPISchema)
        mock_penalty_dao.get_all_penalties.assert_called_once()

    def test_get_all_penalties_by_user(
            self, penalty_controller, mock_penalty_dao,
            mock_user_dao, sample_penalty):
        mock_user_dao.get_user.return_value = {"userid": "user_001"}
        mock_penalty_dao.get_penalties_by_user.return_value = [sample_penalty]

        result = penalty_controller.get_all_penalties(user_id="user_001")

        assert len(result.penalties) == 1
        assert result.penalties[0].user_id == "user_001"
        mock_penalty_dao.get_penalties_by_user.assert_called_once_with(
            "user_001")

    def test_get_all_penalties_user_not_found(
            self, penalty_controller, mock_user_dao):
        mock_user_dao.get_user.side_effect = KeyError("User not found")

        with pytest.raises(HTTPException) as exc_info:
            penalty_controller.get_all_penalties(user_id="nonexistent_user")

        assert exc_info.value.status_code == 404

    def test_get_all_penalties_active_filter(
            self, penalty_controller, mock_penalty_dao):
        active_penalty = Penalty(
            penalty_id="penalty_001",
            user_id="user_001",
            reason="Active violation",
            severity=2,
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now() + timedelta(days=7),
            created_at=datetime.now()
        )

        inactive_penalty = Penalty(
            penalty_id="penalty_002",
            user_id="user_002",
            reason="Past violation",
            severity=1,
            start_date=datetime.now() - timedelta(days=14),
            end_date=datetime.now() - timedelta(days=7),
            created_at=datetime.now() - timedelta(days=14)
        )

        mock_penalty_dao.get_all_penalties.return_value = [active_penalty,
                                                           inactive_penalty]

        result = penalty_controller.get_all_penalties(status="active")

        assert len(result.penalties) == 1
        assert result.penalties[0].penalty_id == "penalty_001"
        assert result.penalties[0].is_active is True

    def test_get_all_penalties_inactive_filter(self, penalty_controller,
                                               mock_penalty_dao):
        active_penalty = Penalty(
            penalty_id="penalty_001",
            user_id="user_001",
            reason="Active violation",
            severity=2,
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now() + timedelta(days=7),
            created_at=datetime.now()
        )

        inactive_penalty = Penalty(
            penalty_id="penalty_002",
            user_id="user_002",
            reason="Past violation",
            severity=1,
            start_date=datetime.now() - timedelta(days=14),
            end_date=datetime.now() - timedelta(days=7),
            created_at=datetime.now() - timedelta(days=14)
        )

        mock_penalty_dao.get_all_penalties.return_value = [active_penalty,
                                                           inactive_penalty]

        result = penalty_controller.get_all_penalties(status="inactive")

        assert len(result.penalties) == 1
        assert result.penalties[0].penalty_id == "penalty_002"

    def test_get_all_penalties_invalid_status(self, penalty_controller):
        with pytest.raises(HTTPException) as exc_info:
            penalty_controller.get_all_penalties(status="invalid")

        assert exc_info.value.status_code == 400
        assert "invalid status" in str(exc_info.value.detail).lower()


class TestPenaltyControllerUpdate:

    def test_update_penalty_success(
            self, penalty_controller, mock_penalty_dao, sample_penalty):
        update_data = UpdatePenaltySchema(
            reason="Updated reason for penalty",
            severity=4
        )

        updated_penalty = Penalty(
            penalty_id=sample_penalty.penalty_id,
            user_id=sample_penalty.user_id,
            reason="Updated reason for penalty",
            severity=4,
            start_date=sample_penalty.start_date,
            end_date=sample_penalty.end_date,
            issued_by=sample_penalty.issued_by,
            created_at=sample_penalty.created_at
        )

        mock_penalty_dao.update_penalty.return_value = updated_penalty

        result = penalty_controller.update_penalty("penalty_001", update_data)

        assert result.reason == "Updated reason for penalty"
        assert result.severity == 4
        mock_penalty_dao.update_penalty.assert_called_once()

    def test_update_penalty_partial_update(
            self, penalty_controller, mock_penalty_dao, sample_penalty):
        update_data = UpdatePenaltySchema(severity=5)

        updated_penalty = Penalty(
            penalty_id=sample_penalty.penalty_id,
            user_id=sample_penalty.user_id,
            reason=sample_penalty.reason,
            severity=5,
            start_date=sample_penalty.start_date,
            end_date=sample_penalty.end_date,
            issued_by=sample_penalty.issued_by,
            created_at=sample_penalty.created_at
        )

        mock_penalty_dao.update_penalty.return_value = updated_penalty

        result = penalty_controller.update_penalty("penalty_001", update_data)

        assert result.severity == 5

    def test_update_penalty_no_changes(
            self, penalty_controller, mock_penalty_dao, sample_penalty):
        update_data = UpdatePenaltySchema()

        mock_penalty_dao.get_penalty.return_value = sample_penalty

        result = penalty_controller.update_penalty("penalty_001", update_data)

        assert result.penalty_id == sample_penalty.penalty_id
        mock_penalty_dao.update_penalty.assert_not_called()

    def test_update_penalty_not_found(
            self, penalty_controller, mock_penalty_dao):
        update_data = UpdatePenaltySchema(severity=5)

        mock_penalty_dao.update_penalty.side_effect = KeyError(
            "Penalty not found")

        with pytest.raises(HTTPException) as exc_info:
            penalty_controller.update_penalty("penalty_999", update_data)

        assert exc_info.value.status_code == 404

    def test_update_penalty_dates(
            self, penalty_controller, mock_penalty_dao, sample_penalty):
        new_start = datetime.now() + timedelta(days=1)
        new_end = datetime.now() + timedelta(days=14)

        update_data = UpdatePenaltySchema(
            start_date=new_start,
            end_date=new_end
        )

        updated_penalty = Penalty(
            penalty_id=sample_penalty.penalty_id,
            user_id=sample_penalty.user_id,
            reason=sample_penalty.reason,
            severity=sample_penalty.severity,
            start_date=new_start,
            end_date=new_end,
            issued_by=sample_penalty.issued_by,
            created_at=sample_penalty.created_at
        )

        mock_penalty_dao.update_penalty.return_value = updated_penalty

        result = penalty_controller.update_penalty("penalty_001", update_data)

        assert result.start_date == new_start
        assert result.end_date == new_end


class TestPenaltyControllerDelete:

    def test_delete_penalty_success(
            self, penalty_controller, mock_penalty_dao):
        result = penalty_controller.delete_penalty("penalty_001")

        assert "deleted successfully" in result["message"].lower()
        assert "penalty_001" in result["message"]
        mock_penalty_dao.delete_penalty.assert_called_once_with("penalty_001")

    def test_delete_penalty_not_found(
            self, penalty_controller, mock_penalty_dao):
        mock_penalty_dao.delete_penalty.side_effect = KeyError(
            "Penalty not found")

        with pytest.raises(HTTPException) as exc_info:
            penalty_controller.delete_penalty("penalty_999")

        assert exc_info.value.status_code == 404
        assert "penalty_999" in str(exc_info.value.detail).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
