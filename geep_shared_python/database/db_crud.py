"""
This module serves as Data Access Layer handling CRUD operations on databases
- Base class for Data Access Layer
- Concrete implementations for SQLAlchemy Core
"""

from typing import Any, Callable, Generator, Generic, List, Optional, Type, TypeVar

from fastapi import Depends
from sqlalchemy import DateTime, UniqueConstraint, asc, desc, exc, func, inspect
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column

from geep_shared_python.database.database import SessionLocal
from geep_shared_python.logging import log_config


class Base(DeclarativeBase):
    __abstract__ = True
    type_annotation_map = {dict[str, Any]: JSONB}
    created_at = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )


T = TypeVar("T", bound=Base)


class DatabaseRepository(Generic[T]):
    """
    A generic class for performing CRUD operations on a database. This is typed
    using the repository pattern.

    Args:
        model (type[Base]): The SQLAlchemy model to perform CRUD operations on.
        session (Session): The SQLAlchemy session to use for database operations.


    Methods:
        select: Selects records from the database.
        select_one: Selects a single record from the database.
        insert: Inserts new records into the database.
        update: Updates records in the database.
        upsert: Inserts a new record or updates an existing one based on unique constraints.
        delete: Deletes records from the database. USE WITH CARE! As a rule we should not be deleting data.
    """

    def __init__(self, model: Type[T], session: Session):
        self.model = model
        self.session = session

        # if the logging has been initialised, the service name at the time of initialisation
        # will be used instead of `geep-shared-python`
        self.logger = log_config.get_logger_and_add_handler(
            "geep_shared_python", "app.db_crud"
        )

    def select(
        self,
        filter_conditions: Optional[dict[str, Any]] = None,
        order_by: Optional[List[str]] = None,
        descending: bool = False,
    ) -> list[T]:
        """
        Selects records from the database

        Args:
            filter_conditions (dict): Filter conditions to apply to the select operation.
                                      This can be a single key-value pair or a key with a list of values.
            order_by (str, optional): Column to sort by. Defaults to None.
            descending (bool, optional): Whether to sort in descending order. Defaults to False.

        Returns:
            Any: The selected records.
        """
        try:
            query = self.session.query(self.model)
            if filter_conditions is not None:
                for key, value in filter_conditions.items():
                    if isinstance(value, list):
                        query = query.filter(getattr(self.model, key).in_(value))
                    else:
                        query = query.filter(getattr(self.model, key) == value)

            if order_by:
                order_func = desc if descending else asc
                for column in order_by:
                    query = query.order_by(order_func(getattr(self.model, column)))

            return query.all()
        except exc.SQLAlchemyError as e:
            self.logger.error("Error occurred during select operation: %s", e)
            raise

    def select_one(
        self,
        filter_conditions: Optional[dict[str, Any]] = None,
        less_than: Optional[bool] = False,
        greater_than: Optional[bool] = False,
        lt_gt_columns: Optional[List[str]] = None,
    ) -> T:
        """
        Selects a single record from the database

        Args:
            filter_conditions (dict): Filter conditions to apply to the select operation
            order_by (str, optional): Column to sort by. Defaults to None.
            less_than (bool, optional): Whether to select using < a value. Defaults to False.
            greater_than (bool, optional): Whether to select using a value>. Defaults to False.
            lt_gt_columns (List[str], optional): Columns to apply < or > to. Defaults to None.
                                                 Columns not named here use == operator.
        Returns:
            Any: The selected records.
        """
        try:
            query = self.session.query(self.model)
            if filter_conditions is not None:
                for key, value in filter_conditions.items():
                    if less_than and lt_gt_columns is not None and key in lt_gt_columns:
                        query = query.filter(getattr(self.model, key) < value)
                    elif (
                        greater_than
                        and lt_gt_columns is not None
                        and key in lt_gt_columns
                    ):
                        query = query.filter(getattr(self.model, key) > value)
                    else:
                        query = query.filter(getattr(self.model, key) == value)

                if less_than and lt_gt_columns is not None:
                    query = query.order_by(desc("id"))  # type: ignore
                else:
                    query = query.order_by(asc("id"))  # type: ignore

                query = query.limit(1)

            return query.one()
        except exc.SQLAlchemyError as e:
            self.logger.error("Error occurred during select one operation: %s", e)
            raise

    def insert(self, data: dict[str, Any], do_commit: bool = True) -> T:
        """
        Inserts new records into the database
        Args:
            model (tye[Base]): SQLAlchemy model used in select operation
            data (dict): The data for the new record
            do_commit (bool, optional): Whether to commit the transaction. Defaults to True.
            Used when multiple inserts must be atomic.
        Returns:
            Any: The inserted record.
        """
        try:
            new_record = self.model(**data)
            self.session.add(new_record)
            if do_commit:
                self.session.commit()
                self.session.refresh(new_record)
            else:
                self.session.flush()
            return new_record
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error(f"Error occurred during insert operation: {e}")
            raise

    def update(
        self,
        filter_conditions: dict[str, Any],
        data: dict[Any, Any],
        do_commit: bool = True,
    ) -> int:
        """
        Updates records in the database.

        Args:
            model (type[Base]): The SQLAlchemy model to update.
            filter_conditions (dict): The conditions to filter the records by.
            data (dict): The new data for the records.

        Returns:
            int: The number of records updated.
        """
        try:
            result = (
                self.session.query(self.model)
                .filter_by(**filter_conditions)
                .update(data)
            )
            if do_commit:
                self.session.commit()
            return result
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error(f"Error occurred during update operation: {e}")
            raise

    def upsert(self, data: dict[str, Any], do_commit: bool = True) -> T:
        """
        Inserts a new record into the database or updates an existing one based on unique constraints.
        Args:
            data (dict): The data for the new or existing record.
        Returns:
            T: The inserted or updated record.
        """

        unique_columns = [
            col.name
            for col in inspect(self.model).columns
            if col.primary_key or col.unique
        ] + [
            col.name
            for arg in getattr(self.model, "__table_args__", [])
            if isinstance(arg, UniqueConstraint)
            for col in arg.columns
        ]

        new_record = self.model(**data)
        try:
            self.session.add(new_record)
            if do_commit:
                self.session.commit()
                self.session.refresh(new_record)
            return new_record
        except exc.IntegrityError:
            self.logger.info("Record already exists, updating instead")
            self.session.rollback()
            # update based on unique columns as filters
            filter_conditions = {
                col: data[col] for col in unique_columns if col in data
            }
            # update data non-unique or primary key columns
            update_data = {
                key: value for key, value in data.items() if key not in unique_columns
            }
            self.update(filter_conditions, update_data)
            return new_record
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error(f"SQLAlchemy error during upsert operation: {e}")
            raise

    def delete(self, filter_conditions: dict[str, Any], do_commit: bool = True) -> int:
        """
        Deletes records from the database. USE WITH CARE! As a rule we should not be deleting data.

        Args:
            filter_conditions (dict): The conditions to filter the records by.

        Returns:
            int: The number of records deleted.
        """
        try:
            result = (
                self.session.query(self.model).filter_by(**filter_conditions).delete()
            )
            if do_commit:
                self.session.commit()
            return result
        except exc.SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error(f"Error occurred during delete operation: {e}")
            raise


def get_db_session() -> Generator[Session, None, None]:
    """Creates a new SQLAlchemy SessionLocal instance and closes after request is finished
    Yields:
        Session: SQLAlchemy SessionLocal instance
    """
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


def get_repository(
    model: Type[Base],
) -> Callable[[Session], DatabaseRepository[Base]]:
    """Provides Repository instance with the database session
    Args:
        db (Session, optional): SQLAlchemy Session instance. Defaults to Depends(get_db_session).

    Returns:
        DatabaseRespository: A database repository of type Model
    """

    def func(session: Session = Depends(get_db_session)):
        return DatabaseRepository(model, session)

    return func
