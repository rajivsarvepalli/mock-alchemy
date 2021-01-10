"""Testing the module for mocking in mock-alchemy."""
from __future__ import annotations

from unittest import mock

import pytest
from sqlalchemy import Column, Integer, String, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import column

from mock_alchemy.comparison import ExpressionMatcher
from mock_alchemy.mocking import (
    AlchemyMagicMock,
    UnifiedAlchemyMagicMock,
    UnorderedCall,
    UnorderedTuple,
    sqlalchemy_call,
)


def test_unorder_tuple() -> None:
    """Tests tuple in which, in comparison order does not matter."""
    assert UnorderedTuple((1, 2, 3)) == (3, 2, 1)
    assert UnorderedTuple((1, 3)) != (3,)
    assert UnorderedTuple((1, 2, 3)) == (1, 2, 3)
    assert UnorderedTuple((1, 2, 3)) == (2, 3, 1)
    assert not UnorderedTuple((7, 2, 3)).__eq__((1, 2, 5))


def test_unorder_call() -> None:
    """Tests call in which, in comparison order does not matter."""
    Call = type(mock.call)
    assert UnorderedCall(((1, 2, 3), {"hello": "world"})) == Call(
        ((3, 2, 1), {"hello": "world"})
    )


def test_alchemy_call() -> None:
    """
    Tests mock.call() being converted for wrapping in ExpressionMatcher
    for SqlAlchemy call.
    """
    args, kwargs = sqlalchemy_call(mock.call(5, foo="bar"))
    assert isinstance(args[0], ExpressionMatcher)
    assert isinstance(kwargs["foo"], ExpressionMatcher)


def test_alchemy_magic_mock() -> None:
    """Tests mock for SQLAlchemy that compares alchemys expressions in assertions."""
    c = column("column")
    s = AlchemyMagicMock()
    _ = s.filter(or_(c == 5, c == 10))
    _ = s.filter.assert_called_once_with(or_(c == 5, c == 10))
    _ = s.filter.assert_any_call(or_(c == 5, c == 10))
    _ = s.filter.assert_has_calls([mock.call(or_(c == 5, c == 10))])
    s.reset_mock()
    _ = s.filter(c == 5)
    with pytest.raises(AssertionError):
        _ = s.filter.assert_called_once_with(c == 10)


def test_unified_magic_mock() -> None:
    """Tests mock for SQLAlchemy that unifies session functions for simple asserts."""
    c = column("column")
    """s = UnifiedAlchemyMagicMock()
    ret = s.query(None).filter(c == "one").filter(c == "two").all()
    assert ret == []
    ret = s.query(None).filter(c == "three").filter(c == "four").all()
    assert ret == []
    assert 2 == s.filter.call_count
    _ = s.filter.assert_any_call(c == "one", c == "two")
    _ = s.filter.assert_any_call(c == "three", c == "four")"""
    Base = declarative_base()

    class SomeClass(Base):
        """SqlAlchemy object for testing."""

        __tablename__ = "some_table"
        pk1 = Column(Integer, primary_key=True)
        pk2 = Column(Integer, primary_key=True)
        name = Column(String(50))

        def __repr__(self) -> str:
            """Get strin of object."""
            return str(self.pk1)

        def __eq__(self, other: SomeClass) -> bool:
            """Object equality checker."""
            if isinstance(other, SomeClass):
                return (
                    self.pk1 == other.pk1
                    and self.pk2 == other.pk2
                    and self.name == other.name
                )
            return NotImplemented

    s = UnifiedAlchemyMagicMock(
        data=[
            (
                [mock.call.query("foo"), mock.call.filter(c == "one", c == "two")],
                [SomeClass(pk1=1, pk2=1), SomeClass(pk1=2, pk2=2)],
            ),
            (
                [
                    mock.call.query("foo"),
                    mock.call.filter(c == "one", c == "two"),
                    mock.call.order_by(c),
                ],
                [SomeClass(pk1=2, pk2=2), SomeClass(pk1=1, pk2=1)],
            ),
            ([mock.call.filter(c == "three")], [SomeClass(pk1=3, pk2=3)]),
        ]
    )
    ret = s.query("foo").filter(c == "one").filter(c == "three").order_by(c).all()
    assert [] == ret
    ret = s.query("foo").filter(c == "one").filter(c == "two").all()
    expected_ret = [SomeClass(pk1=1, pk2=1), SomeClass(pk1=2, pk2=2)]
    assert expected_ret == ret
    ret = list(s.query("foo").filter(c == "two").filter(c == "one"))
    assert expected_ret == ret
    ret = s.query("bar").filter(c == "one").filter(c == "two").all()
    assert ret == []
    ret = s.query("foo").filter(c == "one").filter(c == "two").order_by(c).all()
    expected_ret = [SomeClass(pk1=2, pk2=2), SomeClass(pk1=1, pk2=1)]
    assert expected_ret == ret
    ret = list(s.query("foo").filter(c == "two").filter(c == "one"))
    ret = s.query("foo").filter(c == "two").filter(c == "one").count()
    assert ret == 2
    ret = s.query("foo").filter(c == "one").filter(c == "two").first()
    assert ret == SomeClass(pk1=1, pk2=1)
    ret = s.query("foo").filter(c == "three").one()
    assert ret == SomeClass(pk1=3, pk2=3)
    ret = s.query("foo").get((1, 1))
    assert ret == SomeClass(pk1=1, pk2=1)
    ret = s.query("foo").filter(c == "two").filter(c == "one").get((1, 1))
    assert ret == SomeClass(pk1=1, pk2=1)
    ret = s.query("foo").filter(c == "three").delete()
    assert ret == 1
    ret = s.query("foo").filter(c == "three").all()
    assert ret == []
    s = UnifiedAlchemyMagicMock()
    s.add(SomeClass(pk1=1, pk2=1))
    s.add_all([SomeClass(pk1=2, pk2=2)])
    ret = s.query(SomeClass).all()
    expected_ret = [SomeClass(pk1=1, pk2=1), SomeClass(pk1=2, pk2=2)]
    assert ret == expected_ret
    ret = s.query(SomeClass).delete()
    assert ret == 2
    ret = s.query(SomeClass).delete()
    assert ret == 0

    class Model(Base):
        """SqlAlchemy object for testing."""

        __tablename__ = "model_table"
        pk1 = Column(Integer, primary_key=True)
        name = Column(String)

    s = UnifiedAlchemyMagicMock()
    s.add_all([SomeClass(pk1=2, pk2=2)])
    s.add_all([Model(pk1=5, name="test")])
    ret = s.query(SomeClass).delete()
    assert ret == 1
    ret = s.query(SomeClass).delete()
    assert ret == 0
    s = UnifiedAlchemyMagicMock()
    assert s.all() == []
