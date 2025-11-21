from keyboard_smashers.dao.penalty_dao import PenaltyDAO
import pytest
import csv
import tempfile
import os
from datetime import datetime, timedelta
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../..')))


@pytest.fixture
def temp_csv_file():
    temp_file = tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.csv', newline='')
    temp_file.close()
    yield temp_file.name
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


@pytest.fixture
def sample_penalty_data():
    return {
        'penalty_id': 'penalty_001',
        'user_id': 'user_001',
        'reason': 'Violated community guidelines',
        'severity': 3,
        'start_date': datetime.now().replace(microsecond=0),
        'end_date': (datetime.now() + timedelta(days=7)).replace(
            microsecond=0),
        'issued_by': 'admin_001',
        'created_at': datetime.now().replace(microsecond=0)
    }


@pytest.fixture
def populated_csv_file(temp_csv_file, sample_penalty_data):
    with open(temp_csv_file, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['penalty_id', 'user_id', 'reason', 'severity',
                      'start_date', 'end_date', 'issued_by', 'created_at']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        writer.writerow({
            'penalty_id': sample_penalty_data['penalty_id'],
            'user_id': sample_penalty_data['user_id'],
            'reason': sample_penalty_data['reason'],
            'severity': sample_penalty_data['severity'],
            'start_date': sample_penalty_data['start_date'].isoformat(),
            'end_date': sample_penalty_data['end_date'].isoformat(),
            'issued_by': sample_penalty_data['issued_by'],
            'created_at': sample_penalty_data['created_at'].isoformat()
        })

        writer.writerow({
            'penalty_id': 'penalty_002',
            'user_id': 'user_001',
            'reason': 'Spam posting',
            'severity': 2,
            'start_date': (datetime.now() - timedelta(days=14)).isoformat(),
            'end_date': (datetime.now() - timedelta(days=7)).isoformat(),
            'issued_by': 'admin_002',
            'created_at': (datetime.now() - timedelta(days=14)).isoformat()
        })

        writer.writerow({
            'penalty_id': 'penalty_003',
            'user_id': 'user_002',
            'reason': 'Harassment',
            'severity': 5,
            'start_date': (datetime.now() - timedelta(days=1)).isoformat(),
            'end_date': (datetime.now() + timedelta(days=30)).isoformat(),
            'issued_by': 'admin_001',
            'created_at': (datetime.now() - timedelta(days=1)).isoformat()
        })

    return temp_csv_file


class TestPenaltyDAOInitialization:

    def test_initialization_with_existing_file(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        assert len(dao.penalties) == 3
        assert 'penalty_001' in dao.penalties
        assert 'penalty_002' in dao.penalties
        assert 'penalty_003' in dao.penalties
        assert dao.penalty_counter == 4

    def test_initialization_with_nonexistent_file(self, temp_csv_file):
        os.unlink(temp_csv_file)

        dao = PenaltyDAO(csv_path=temp_csv_file)

        assert len(dao.penalties) == 0
        assert dao.penalty_counter == 1
        assert dao.penalties == {}
        assert dao.user_penalties == {}

    def test_user_penalties_index_created(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        assert 'user_001' in dao.user_penalties
        assert 'user_002' in dao.user_penalties
        assert len(dao.user_penalties['user_001']) == 2
        assert len(dao.user_penalties['user_002']) == 1
        assert 'penalty_001' in dao.user_penalties['user_001']
        assert 'penalty_002' in dao.user_penalties['user_001']
        assert 'penalty_003' in dao.user_penalties['user_002']


class TestPenaltyDAOCreate:

    def test_create_penalty_basic(self, temp_csv_file):
        dao = PenaltyDAO(csv_path=temp_csv_file)

        penalty_data = {
            'user_id': 'user_001',
            'reason': 'Test violation',
            'severity': 3,
            'start_date': datetime.now(),
            'end_date': datetime.now() + timedelta(days=7),
            'issued_by': 'admin_001'
        }

        penalty = dao.create_penalty(penalty_data)

        assert penalty.penalty_id == 'penalty_001'
        assert penalty.user_id == 'user_001'
        assert penalty.reason == 'Test violation'
        assert penalty.severity == 3
        assert penalty.issued_by == 'admin_001'
        assert 'penalty_001' in dao.penalties
        assert 'user_001' in dao.user_penalties
        assert 'penalty_001' in dao.user_penalties['user_001']

    def test_create_penalty_increments_counter(self, temp_csv_file):
        dao = PenaltyDAO(csv_path=temp_csv_file)

        penalty_data = {
            'user_id': 'user_001',
            'reason': 'First violation',
            'severity': 2
        }

        penalty1 = dao.create_penalty(penalty_data)
        assert penalty1.penalty_id == 'penalty_001'
        assert dao.penalty_counter == 2

        penalty2 = dao.create_penalty(penalty_data)
        assert penalty2.penalty_id == 'penalty_002'
        assert dao.penalty_counter == 3

    def test_create_penalty_defaults(self, temp_csv_file):
        dao = PenaltyDAO(csv_path=temp_csv_file)

        penalty_data = {
            'user_id': 'user_001',
            'reason': 'Test violation',
            'severity': 3
        }

        penalty = dao.create_penalty(penalty_data)

        assert penalty.start_date is not None
        assert penalty.end_date is None
        assert penalty.issued_by is None
        assert penalty.created_at is not None

    def test_create_penalty_saves_to_csv(self, temp_csv_file):
        dao = PenaltyDAO(csv_path=temp_csv_file)

        penalty_data = {
            'user_id': 'user_001',
            'reason': 'Test violation',
            'severity': 3
        }

        dao.create_penalty(penalty_data)

        assert os.path.exists(temp_csv_file)

        with open(temp_csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]['penalty_id'] == 'penalty_001'
            assert rows[0]['user_id'] == 'user_001'

    def test_create_multiple_penalties_same_user(self, temp_csv_file):
        dao = PenaltyDAO(csv_path=temp_csv_file)

        penalty_data1 = {
            'user_id': 'user_001',
            'reason': 'First violation',
            'severity': 2
        }
        penalty_data2 = {
            'user_id': 'user_001',
            'reason': 'Second violation',
            'severity': 3
        }

        penalty1 = dao.create_penalty(penalty_data1)
        penalty2 = dao.create_penalty(penalty_data2)

        assert len(dao.user_penalties['user_001']) == 2
        assert penalty1.penalty_id in dao.user_penalties['user_001']
        assert penalty2.penalty_id in dao.user_penalties['user_001']


class TestPenaltyDAORead:

    def test_get_penalty_success(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        penalty = dao.get_penalty('penalty_001')

        assert penalty.penalty_id == 'penalty_001'
        assert penalty.user_id == 'user_001'
        assert penalty.reason == 'Violated community guidelines'

    def test_get_penalty_not_found(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        with pytest.raises(KeyError) as exc_info:
            dao.get_penalty('penalty_999')

        assert 'penalty_999' in str(exc_info.value)

    def test_get_penalties_by_user(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        penalties = dao.get_penalties_by_user('user_001')

        assert len(penalties) == 2
        penalty_ids = [p.penalty_id for p in penalties]
        assert 'penalty_001' in penalty_ids
        assert 'penalty_002' in penalty_ids

    def test_get_penalties_by_user_no_penalties(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        penalties = dao.get_penalties_by_user('user_999')

        assert penalties == []

    def test_get_active_penalties_by_user(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        active_penalties = dao.get_active_penalties_by_user('user_001')

        # penalty_001 should be active, penalty_002 should be inactive
        assert len(active_penalties) == 1
        assert active_penalties[0].penalty_id == 'penalty_001'
        assert active_penalties[0].is_active() is True

    def test_get_all_penalties(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        penalties = dao.get_all_penalties()

        assert len(penalties) == 3
        penalty_ids = [p.penalty_id for p in penalties]
        assert 'penalty_001' in penalty_ids
        assert 'penalty_002' in penalty_ids
        assert 'penalty_003' in penalty_ids

    def test_get_penalty_count_by_user(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        count_user1 = dao.get_penalty_count_by_user('user_001')
        count_user2 = dao.get_penalty_count_by_user('user_002')
        count_user3 = dao.get_penalty_count_by_user('user_999')

        assert count_user1 == 2
        assert count_user2 == 1
        assert count_user3 == 0


class TestPenaltyDAOUpdate:

    def test_update_penalty_reason(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        update_data = {'reason': 'Updated violation reason'}
        penalty = dao.update_penalty('penalty_001', update_data)

        assert penalty.reason == 'Updated violation reason'
        assert dao.penalties['penalty_001'].reason == (
            'Updated violation reason'
        )

    def test_update_penalty_severity(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        update_data = {'severity': 5}
        penalty = dao.update_penalty('penalty_001', update_data)

        assert penalty.severity == 5
        assert dao.penalties['penalty_001'].severity == 5

    def test_update_penalty_dates(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        new_start = datetime.now() + timedelta(days=1)
        new_end = datetime.now() + timedelta(days=14)

        update_data = {
            'start_date': new_start,
            'end_date': new_end
        }
        penalty = dao.update_penalty('penalty_001', update_data)

        assert penalty.start_date == new_start
        assert penalty.end_date == new_end

    def test_update_penalty_multiple_fields(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        update_data = {
            'reason': 'Updated reason',
            'severity': 4,
            'end_date': datetime.now() + timedelta(days=30)
        }
        penalty = dao.update_penalty('penalty_001', update_data)

        assert penalty.reason == 'Updated reason'
        assert penalty.severity == 4
        assert penalty.end_date == update_data['end_date']

    def test_update_penalty_not_found(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        with pytest.raises(KeyError) as exc_info:
            dao.update_penalty('penalty_999', {'severity': 5})

        assert 'penalty_999' in str(exc_info.value)

    def test_update_penalty_saves_to_csv(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        update_data = {'reason': 'Updated reason for testing'}
        dao.update_penalty('penalty_001', update_data)

        dao_reloaded = PenaltyDAO(csv_path=populated_csv_file)
        penalty = dao_reloaded.get_penalty('penalty_001')

        assert penalty.reason == 'Updated reason for testing'


class TestPenaltyDAODelete:

    def test_delete_penalty_success(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        assert 'penalty_001' in dao.penalties
        assert len(dao.penalties) == 3

        dao.delete_penalty('penalty_001')

        assert 'penalty_001' not in dao.penalties
        assert len(dao.penalties) == 2

    def test_delete_penalty_not_found(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        with pytest.raises(KeyError) as exc_info:
            dao.delete_penalty('penalty_999')

        assert 'penalty_999' in str(exc_info.value)

    def test_delete_penalty_removes_from_user_index(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        assert 'penalty_001' in dao.user_penalties['user_001']

        dao.delete_penalty('penalty_001')

        assert 'penalty_001' not in dao.user_penalties['user_001']

        assert len(dao.user_penalties['user_001']) == 1

    def test_delete_penalty_removes_empty_user_index(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        dao.delete_penalty('penalty_003')

        assert 'user_002' not in dao.user_penalties

    def test_delete_penalty_saves_to_csv(self, populated_csv_file):
        dao = PenaltyDAO(csv_path=populated_csv_file)

        dao.delete_penalty('penalty_001')

        dao_reloaded = PenaltyDAO(csv_path=populated_csv_file)

        assert len(dao_reloaded.penalties) == 2
        assert 'penalty_001' not in dao_reloaded.penalties

        with pytest.raises(KeyError):
            dao_reloaded.get_penalty('penalty_001')


class TestPenaltyDAOPersistence:

    def test_save_penalties_creates_directory(self):
        temp_dir = tempfile.mkdtemp()
        csv_path = os.path.join(temp_dir, 'subdir', 'penalties.csv')

        try:
            dao = PenaltyDAO(csv_path=csv_path)
            penalty_data = {
                'user_id': 'user_001',
                'reason': 'Test violation',
                'severity': 3
            }
            dao.create_penalty(penalty_data)

            assert os.path.exists(csv_path)
        finally:
            import shutil
            shutil.rmtree(temp_dir)

    def test_load_and_save_maintains_data_integrity(self, populated_csv_file):
        dao1 = PenaltyDAO(csv_path=populated_csv_file)
        original_penalties = dao1.get_all_penalties()

        dao2 = PenaltyDAO(csv_path=populated_csv_file)
        reloaded_penalties = dao2.get_all_penalties()

        assert len(original_penalties) == len(reloaded_penalties)

        for orig, reloaded in zip(
            sorted(original_penalties, key=lambda p: p.penalty_id),
            sorted(reloaded_penalties, key=lambda p: p.penalty_id)
        ):
            assert orig.penalty_id == reloaded.penalty_id
            assert orig.user_id == reloaded.user_id
            assert orig.reason == reloaded.reason
            assert orig.severity == reloaded.severity


class TestPenaltyDAOEdgeCases:

    def test_invalid_penalty_id_format_doesnt_affect_counter(
            self, temp_csv_file):
        with open(temp_csv_file, 'w', encoding='utf-8', newline='') as f:
            fieldnames = ['penalty_id', 'user_id', 'reason', 'severity',
                          'start_date', 'end_date', 'issued_by', 'created_at']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                'penalty_id': 'custom_penalty_id',
                'user_id': 'user_001',
                'reason': 'Test',
                'severity': 3,
                'start_date': datetime.now().isoformat(),
                'end_date': None,
                'issued_by': 'admin_001',
                'created_at': datetime.now().isoformat()
            })

        dao = PenaltyDAO(csv_path=temp_csv_file)

        assert dao.penalty_counter == 1

    def test_empty_csv_file(self, temp_csv_file):
        with open(temp_csv_file, 'w', encoding='utf-8', newline='') as f:
            fieldnames = ['penalty_id', 'user_id', 'reason', 'severity',
                          'start_date', 'end_date', 'issued_by', 'created_at']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

        dao = PenaltyDAO(csv_path=temp_csv_file)

        assert len(dao.penalties) == 0
        assert dao.penalty_counter == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
