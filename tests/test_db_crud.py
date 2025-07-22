import uuid
from typing import Any, Optional, Union
from unittest.mock import MagicMock, create_autospec

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Mapped, Session, mapped_column

from geep_shared_python.database.db_crud import Base, DatabaseRepository
from geep_shared_python.logging.log_config import GeepOtelLoggerProvider


class MockModel(Base):
    __tablename__ = "mock_table"
    dialogue_id: Mapped[str] = mapped_column(primary_key=True)
    feedback_prompt_id: Mapped[str]
    feedback_text = Mapped[str]
    score = Mapped[Optional[int]]


dialogue_id = str(uuid.uuid4())


@pytest.fixture
def record_data() -> dict[str, Union[str, int]]:
    return {
        "dialogue_id": dialogue_id,
        "feedback_prompt_id": str(uuid.uuid4()),
        "feedback_text": "Sample feedback text",
        "score": 5,
    }


@pytest.fixture
def mock_session() -> Session:
    session = create_autospec(Session, instance=True)
    return session


def test_insert_calls_session_add_commit_and_refresh(
    mock_session: Any, record_data: dict[str, Union[str, int]]
):
    # Arrange
    repository = DatabaseRepository(MockModel, mock_session)

    # Act
    repository.insert(record_data)

    # Assert
    mock_session.add.assert_called()  # Assert that add was called
    added_model_instance = mock_session.add.call_args[0][0]
    assert isinstance(added_model_instance, MockModel)
    mock_session.commit.assert_called()  # Assert commit was called
    mock_session.refresh.assert_called_with(added_model_instance)


def test_database_error_triggers_rollback(
    mock_session: Any, record_data: dict[str, Union[str, int]]
):
    # Arrange
    mock_logger = create_autospec(GeepOtelLoggerProvider)
    mock_session.add.side_effect = SQLAlchemyError("Simulate database error")
    repository = DatabaseRepository(MockModel, mock_session)
    repository.logger = mock_logger  # type: ignore

    # Act
    with pytest.raises(Exception):
        repository.insert(record_data)

    # Assert
    mock_session.add.assert_called()  # Assert that add was called
    mock_session.rollback.assert_called()  # Assert rollback was called
    mock_session.commit.assert_not_called()  # Assert that commit was not called


def test_select_calls_session_query(
    mock_session: Any, record_data: dict[str, Union[str, int]]
):
    # Arrange
    repository = DatabaseRepository(MockModel, mock_session)
    expected_records = [MockModel(**record_data)]  # Setting expected return value
    mock_session.query().filter().all.return_value = expected_records

    filter_conditions = {"dialogue_id": dialogue_id}

    # Act
    result = repository.select(filter_conditions)

    # Assert
    mock_session.query.assert_called_with(MockModel)
    assert result == expected_records  # Asserting the return value is as expected


def test_select_one_calls_session_query_with_filter_and_order_by(
    mock_session: Any, record_data: dict[str, Union[str, int]]
):
    # Arrange
    repository = DatabaseRepository(MockModel, mock_session)
    expected_record = MockModel(**record_data)  # Setting expected return value
    mock_session.query().filter().order_by().limit().one.return_value = expected_record

    filter_conditions = {"dialogue_id": dialogue_id}

    # Act
    result = repository.select_one(filter_conditions)

    # Assert
    mock_session.query.assert_called_with(MockModel)
    mock_session.query().filter.assert_called()
    assert result == expected_record  # Asserting the return value is as expected


def test_update_calls_session_query_with_filter_and_commits(mock_session: Any):
    # Arrange
    repository = DatabaseRepository(MockModel, mock_session)
    update_data: dict[str, Any] = {
        "feedback_text": "Updated feedback text",
        "score": 10,
    }
    filter_conditions = {"dialogue_id": dialogue_id}
    mock_session.query().filter_by().update.return_value = 1

    # Act
    result = repository.update(filter_conditions, update_data)

    # Assert
    assert result == 1
    mock_session.query.assert_called_with(MockModel)
    mock_session.query().filter_by.assert_called_with(**filter_conditions)
    mock_session.query().filter_by().update.assert_called_with(update_data)
    mock_session.commit.assert_called()


def test_delete_calls_session_query_with_filter_and_commits(mock_session: Any):
    # Arrange
    repository = DatabaseRepository(MockModel, mock_session)
    filter_conditions = {"dialogue_id": dialogue_id}
    mock_session.query().filter_by().delete.return_value = 1

    # Act
    result = repository.delete(filter_conditions)

    # Assert
    assert result == 1
    mock_session.query.assert_called_with(MockModel)
    mock_session.query().filter_by.assert_called_with(**filter_conditions)
    mock_session.query().filter_by().delete.assert_called()
    mock_session.commit.assert_called()


def test_upsert_inserts_when_not_exists(
    mock_session: Any, record_data: dict[str, Union[str, int]]
):
    # Arrange
    repository = DatabaseRepository(MockModel, mock_session)
    # Simulate successful insert (no IntegrityError)
    mock_session.add.side_effect = None
    mock_session.commit.side_effect = None
    mock_session.refresh.side_effect = None
    mock_session.rollback.side_effect = None

    # Act
    result = repository.upsert(record_data)

    # Assert
    mock_session.add.assert_called()
    mock_session.commit.assert_called()
    mock_session.refresh.assert_called()
    mock_session.rollback.assert_not_called()
    assert isinstance(result, MockModel)


def test_upsert_updates_when_exists(
    mock_session: Any, record_data: dict[str, Union[str, int]]
):
    # Arrange
    repository = DatabaseRepository(MockModel, mock_session)
    mock_session.add.side_effect = IntegrityError("Duplicate", None, Exception())
    mock_session.rollback.side_effect = None

    # Patch update as a MagicMock
    repository.update = MagicMock(return_value=1)

    # Act
    result = repository.upsert(record_data)

    # Assert
    mock_session.add.assert_called()
    mock_session.rollback.assert_called()
    repository.update.assert_called()
    assert isinstance(result, MockModel)
