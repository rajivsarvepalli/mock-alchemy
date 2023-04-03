"""Common data models for testing."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String

from mock_alchemy.sql_alchemy_imports import declarative_base

Base = declarative_base()


class SomeClass(Base):
    """SQLAlchemy object for testing."""

    __tablename__ = "some_table"
    pk1 = Column(Integer, primary_key=True)
    pk2 = Column(Integer, primary_key=True)
    name = Column(String(50))

    def __repr__(self) -> str:
        """Get string of object."""
        return str(self.pk1)

    def __eq__(self, other: SomeClass) -> bool:
        """Object equality checker."""
        if isinstance(other, SomeClass):
            return (
                self.pk1 == other.pk1
                and self.pk2 == other.pk2
                and self.name == other.name
            )


class Model(Base):
    """SQLAlchemy object for testing."""

    __tablename__ = "model_table"
    pk1 = Column(Integer, primary_key=True)
    name = Column(String)

    def __eq__(self, other: Model) -> bool:
        """Object equality checker."""
        if isinstance(other, Model):
            return self.pk1 == other.pk1 and self.name == other.name
        return NotImplemented

    def __repr__(self) -> str:
        """Get string of object."""
        return str(self.pk1)


class Data(Base):
    """SQLAlchemy object for testing."""

    __tablename__ = "data_table"
    pk1 = Column(Integer, primary_key=True)
    data_p1 = Column(Float)
    data_p2 = Column(Float)
    name = Column(String)

    def __repr__(self) -> str:
        """Get string of object."""
        return str(self.pk1) + self.name


class BaseModel(Base):
    """Abstract data model to test."""

    __abstract__ = True
    created = Column(Integer, nullable=False, default=3)
    createdby = Column(Integer, nullable=False, default={})
    updated = Column(Integer, nullable=False, default=1)
    updatedby = Column(Integer, nullable=False, default={})
    disabled = Column(Integer, nullable=True)


class Concrete(BaseModel):
    """A testing SQLAlchemy object."""

    __tablename__ = "concrete"
    id = Column(Integer, primary_key=True)

    def __init__(self, **kwargs: Any) -> None:
        """Creates a Concrete object."""
        self.id = kwargs.pop("id")
        super(Concrete, self).__init__(**kwargs)

    def __eq__(self, other: Concrete) -> bool:
        """Equality override."""
        return self.id == other.id
