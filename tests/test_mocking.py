"""Testing the module for mocking in mock-alchemy."""
from __future__ import annotations

from unittest import mock

import pytest
from sqlalchemy import or_
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.sql.expression import column

from mock_alchemy.comparison import ExpressionMatcher
from mock_alchemy.mocking import AlchemyMagicMock
from mock_alchemy.mocking import UnifiedAlchemyMagicMock
from mock_alchemy.mocking import UnorderedCall
from mock_alchemy.mocking import UnorderedTuple
from mock_alchemy.mocking import sqlalchemy_call
from mock_alchemy.sql_alchemy_imports import declarative_base

from .common import Concrete
from .common import Data
from .common import Model
from .common import SomeClass

Base = declarative_base()


def test_unorder_tuple() -> None:
    """Tests tuple in which, in comparison order does not matter."""
    assert UnorderedTuple((1, 2, 3)) == (3, 2, 1)
    assert UnorderedTuple((1, 3)) != (3,)
    assert UnorderedTuple((1, 2, 3)) == (1, 2, 3)
    assert UnorderedTuple((1, 2, 3)) == (2, 3, 1)
    assert not UnorderedTuple((7, 2, 3)).__eq__((1, 2, 5))


def test_unorder_call() -> None:
    """Tests call in which, in comparison order does not matter."""
    call = type(mock.call)
    assert UnorderedCall(((1, 2, 3), {"hello": "world"})) == call(
        ((3, 2, 1), {"hello": "world"})
    )


def test_alchemy_call() -> None:
    """Tests conversion of mock.call.

    Tests ``mock.call()`` being converted for wrapping in ExpressionMatcher
    for SQLAlchemy call.
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
    s = UnifiedAlchemyMagicMock()
    ret = s.query(None).filter(c == "one").filter(c == "two").all()
    assert ret == []
    ret = s.query(None).filter(c == "three").filter(c == "four").all()
    assert ret == []
    assert 2 == s.filter.call_count
    _ = s.filter.assert_any_call(c == "one", c == "two")
    _ = s.filter.assert_any_call(c == "three", c == "four")
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
    s = UnifiedAlchemyMagicMock()
    s.add_all([SomeClass(pk1=2, pk2=2)])
    s.add_all([Model(pk1=5, name="test")])
    ret = s.query(SomeClass).delete()
    assert ret == 1
    ret = s.query(SomeClass).delete()
    assert ret == 0
    s = UnifiedAlchemyMagicMock()
    assert s.all() == []
    s = UnifiedAlchemyMagicMock(
        data=[
            (
                [mock.call.query(Model), mock.call.filter(Model.pk1 < 1)],
                [Model(pk1=1, name="test1")],
            ),
            (
                [mock.call.query(Model)],
                [Model(pk1=2, name="test2")],
            ),
        ]
    )
    ret = s.query(Model).filter(Model.pk1 < 1).all()
    assert ret == [Model(pk1=1, name="test1")]
    ret = s.query(Model).filter(Model.pk1 < 1).delete()
    assert ret == 1
    ret = s.query(Model).all()
    assert ret == [Model(pk1=2, name="test2")]
    ret = s.query(Model).filter(Model.pk1 < 1).all()
    assert ret == []
    # test without equals
    ret = s.query(Model).get(2)
    assert ret == Model(pk1=2, name="test2")
    ret = s.query(Model).get({"pk1": 2})
    assert ret == Model(pk1=2, name="test2")
    s = UnifiedAlchemyMagicMock(
        data=[
            (
                [mock.call.query(Model), mock.call.filter(Model.pk1 < 1)],
                [Model(pk1=1, name="test1")],
            ),
            (
                [mock.call.query(Model)],
                [Model(pk1=2, name="test2")],
            ),
        ]
    )
    ret = s.query(Model).filter(Model.pk1 < 1).all()
    ret = [str(r) for r in ret]
    assert ret == ["1"]
    ret = s.query(Model).filter(Model.pk1 < 1).delete()
    assert ret == 1
    ret = s.query(Model).all()
    ret = [str(r) for r in ret]
    assert ret == ["2"]
    ret = s.query(Model).filter(Model.pk1 < 1).all()
    assert ret == []
    s = UnifiedAlchemyMagicMock()
    ret = s.query(Model).delete()
    assert ret == 0


def test_complex_session() -> None:
    """Tests mock for SQLAlchemy with more complex session."""
    s = UnifiedAlchemyMagicMock(
        data=[
            (
                [mock.call.query(Data), mock.call.filter(Data.data_p1 < 13)],
                [
                    Data(pk1=1, data_p1=11.4, data_p2=13.5, name="test1"),
                    Data(pk1=2, data_p1=9.4, data_p2=19.5, name="test2"),
                    Data(pk1=3, data_p1=4.7, data_p2=15.5, name="test3"),
                    Data(pk1=4, data_p1=3.4, data_p2=13.5, name="test4"),
                ],
            ),
            (
                [mock.call.query(Data), mock.call.filter(Data.data_p1 >= 13)],
                [
                    Data(pk1=5, data_p1=16.3, data_p2=3.5, name="test6"),
                    Data(pk1=6, data_p1=19.3, data_p2=10.5, name="test7"),
                    Data(pk1=7, data_p1=13.3, data_p2=33.7, name="test8"),
                ],
            ),
        ]
    )
    new_data = [
        Data(pk1=8, data_p1=16.3, data_p2=38.15, name="test9"),
        Data(pk1=9, data_p1=13.6, data_p2=33.5, name="test10"),
        Data(pk1=10, data_p1=10.1, data_p2=331.35, name="test11"),
        Data(pk1=1, data_p1=2.5, data_p2=67.1, name="test12"),
    ]
    s.add_all(new_data)
    s.add(Data(pk1=11, data_p1=31.5, data_p2=67.1, name="test13"))
    ret = s.query(Data).all()
    expected_data = [str(r) for r in ret]
    assert expected_data == ["8test9", "9test10", "10test11", "1test12", "11test13"]
    n_d = s.query(Data).filter(Data.data_p1 < 13).delete()
    assert n_d == 4
    # test arbitrary parameters to delete
    n_d = (
        s.query(Data)
        .filter(Data.data_p1 >= 13)
        .delete(synchronize_session=False, test1=1, test2=2)
    )
    assert n_d == 3
    ret = s.query(Data).filter(Data.data_p1 >= 13).all()
    assert ret == []
    ret = s.query(Data).all()
    expected_data = [str(r) for r in ret]
    assert expected_data == ["8test9", "9test10", "10test11", "1test12", "11test13"]
    ret = s.query(Data).filter(Data.data_p1 < 13).all()
    assert ret == []


def test_abstract_classes() -> None:
    """Tests mock for SQLAlchemy with inheritance and abstract classes."""
    objs = Concrete(id=1)
    session = UnifiedAlchemyMagicMock(
        data=[
            ([mock.call.query(Concrete)], [objs]),
        ]
    )
    ret = session.query(Concrete).get(1)
    assert ret == objs


def test_get_tuple() -> None:
    """Tests mock for SQLAlchemy with getting by a tuple."""
    mock_session = UnifiedAlchemyMagicMock()
    mock_session.add(Model(pk1="123", name="test"))
    user = mock_session.query(Model).get(("123",))
    assert user is not None


def test_get_singular() -> None:
    """Tests mock for SQLAlchemy with getting by a singular value."""
    mock_session = UnifiedAlchemyMagicMock()
    mock_session.add(Model(pk1="123", name="test"))
    user = mock_session.query(Model).get("123")
    assert user is not None


def test_scalar_singular() -> None:
    """Tests mock for SQLAlchemy with scalar when there is one row."""
    mock_session = UnifiedAlchemyMagicMock()
    expected_model = Model(pk1="123", name="test")
    mock_session.add(expected_model)
    actual_model = mock_session.query(Model).scalar()
    assert expected_model == actual_model


def test_scalar_none() -> None:
    """Tests mock for SQLAlchemy with scalar when rows are empty."""
    mock_session = UnifiedAlchemyMagicMock()
    data = mock_session.query(Model).scalar()
    assert data is None


def test_scalar_multiple() -> None:
    """Tests mock for SQLAlchemy with scalar when there are many rows."""
    mock_session = UnifiedAlchemyMagicMock()
    mock_session.add(Model(pk1="123", name="test"))
    mock_session.add(Model(pk1="1234", name="test"))
    with pytest.raises(MultipleResultsFound):
        mock_session.query(Model).scalar()


def test_scalar_attribute() -> None:
    """Tests mock for SQLAlchemy with scalar for getting an attribute."""
    expected_column_val = "test"
    mock_session = UnifiedAlchemyMagicMock(
        data=[
            (
                [
                    mock.call.query(Model.name),
                    mock.call.filter(Model.pk1 == 3),
                ],
                [(expected_column_val,)],
            )
        ]
    )
    data_column = mock_session.query(Model.name).filter(Model.pk1 == 3).scalar()
    assert expected_column_val == data_column


# TODO: Make all unknown terminating calls have no impact on mock sessions
def test_update_calls() -> None:
    """Tests that update calls have no impact on UnifiedAlchemyMagicMock sessions.

    This should eventually work the same for any unknown calls.
    """
    expected_row = [Model(pk1="1234", name="test")]
    mock_session = UnifiedAlchemyMagicMock(
        data=[
            (
                [
                    mock.call.query(Model),
                    mock.call.filter(Model.pk1 == 3),
                ],
                expected_row,
            )
        ]
    )
    # Test all()
    actual_row = mock_session.query(Model).filter(Model.pk1 == 3).all()
    assert expected_row == actual_row
    mock_session.query(Model).filter(Model.pk1 == 3).update({"pk1": 3})
    actual_row = mock_session.query(Model).filter(Model.pk1 == 3).all()
    assert expected_row == actual_row
    # Test delete()
    assert None is mock_session.query(Model).filter(Model.pk1 == 3).update(
        {"pk1": 3}, synchronize_session="evaluate"
    )
    deleted_count = mock_session.query(Model).filter(Model.pk1 == 3).delete()
    assert 1 == deleted_count
    actual_row = mock_session.query(Model).filter(Model.pk1 == 3).all()
    assert [] == actual_row
