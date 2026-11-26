"""Testing the module for mocking in mock-alchemy."""

from __future__ import annotations

from unittest import mock

import pytest
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy import update
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound
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


def test_session_execute_select() -> None:
    """Tests session.execute with a select statement and dynamic data."""
    session = UnifiedAlchemyMagicMock()
    session.add(Model(pk1=1, name="one"))
    session.add(Model(pk1=2, name="two"))

    assert session.execute(select(Model)).all() == [
        Model(pk1=1, name="one"),
        Model(pk1=2, name="two"),
    ]
    assert session.execute(select(Model)).scalars().all() == [
        Model(pk1=1, name="one"),
        Model(pk1=2, name="two"),
    ]
    assert session.execute(select(Model.name)).all() == [("one",), ("two",)]
    assert session.execute(select(Model.name)).scalars().all() == ["one", "two"]


def test_session_execute_stubbed_data() -> None:
    """Tests session.execute with explicitly stubbed data."""
    expected = Model(pk1=1, name="one")
    session = UnifiedAlchemyMagicMock(
        data=[([mock.call.execute(select(Model))], [expected])]
    )

    assert session.execute(select(Model)).all() == [expected]
    assert session.execute(select(Model)).one_or_none() == expected
    assert session.execute(select(Model)).first() == expected
    assert session.execute(select(Model)).fetchall() == [expected]


def test_session_execute_text_with_params() -> None:
    """Tests session.execute with raw SQL and parameters."""
    statement = text("select * from model_table where pk1 = :pk1")
    session = UnifiedAlchemyMagicMock(
        data=[
            (
                [mock.call.execute(mock.ANY, {"pk1": 1})],
                [{"pk1": 1, "name": "one"}],
            )
        ]
    )

    result = session.execute(statement, {"pk1": 1})
    assert result.fetchall() == [{"pk1": 1, "name": "one"}]
    assert session.execute(statement, {"pk1": 1}).mappings().all() == [
        {"pk1": 1, "name": "one"}
    ]


def test_session_scalar_methods() -> None:
    """Tests the session-level scalar methods."""
    session = UnifiedAlchemyMagicMock()
    session.add(Model(pk1=1, name="one"))

    assert session.scalar(select(Model)) == Model(pk1=1, name="one")
    assert session.scalars(select(Model)).all() == [Model(pk1=1, name="one")]
    assert session.scalar_one(select(Model)) == Model(pk1=1, name="one")
    assert session.scalar_one_or_none(select(Model)) == Model(pk1=1, name="one")

    session.add(Model(pk1=2, name="two"))
    with pytest.raises(MultipleResultsFound):
        session.scalar(select(Model))
    with pytest.raises(MultipleResultsFound):
        session.scalar_one(select(Model))


def test_session_scalar_no_result() -> None:
    """Tests session-level scalar methods with no matching data."""
    session = UnifiedAlchemyMagicMock()

    assert session.scalar(select(Model)) is None
    assert session.scalar_one_or_none(select(Model)) is None
    with pytest.raises(NoResultFound):
        session.scalar_one(select(Model))


def test_session_scalar_count() -> None:
    """Tests scalar methods with an aggregate statement."""
    session = UnifiedAlchemyMagicMock(
        data=[([mock.call.execute(select(func.count(Model.pk1)))], [(2,)])]
    )

    assert session.scalar(select(func.count(Model.pk1))) == 2
    assert session.execute(select(func.count(Model.pk1))).scalar() == 2


def test_query_specific_columns() -> None:
    """Tests querying specific columns of dynamically added data."""
    session = UnifiedAlchemyMagicMock()
    session.add(Model(pk1=1, name="one"))
    session.add(Model(pk1=2, name="two"))

    assert session.query(Model.name).all() == [("one",), ("two",)]
    assert session.query(Model.pk1, Model.name).all() == [(1, "one"), (2, "two")]


def test_query_with_multiple_models() -> None:
    """Tests querying multiple models with select_from and join."""

    class Ist(Base):
        """First model for testing multi-model queries."""

        __tablename__ = "ist_test_models"
        id = Column(Integer, primary_key=True)
        strasse = Column(String)
        kn_ident = Column(Integer)

    class Soll(Base):
        """Second model for testing multi-model queries."""

        __tablename__ = "soll_test_models"
        id = Column(Integer, primary_key=True)
        kn_ident = Column(Integer)
        querschnitt = Column(Integer)

    ist = Ist(id=1, strasse="1", kn_ident=11)
    soll = Soll(id=7, kn_ident=11, querschnitt=10)
    session = UnifiedAlchemyMagicMock(
        data=[
            (
                [
                    mock.call.query(Ist, Soll),
                    mock.call.select_from(Ist),
                    mock.call.join(Soll, Soll.kn_ident == Ist.kn_ident),
                    mock.call.filter(Ist.strasse == "1"),
                ],
                [(ist, soll)],
            )
        ]
    )

    result = (
        session.query(Ist, Soll)
        .select_from(Ist)
        .join(Soll, Soll.kn_ident == Ist.kn_ident)
        .filter(Ist.strasse == "1")
        .all()
    )
    assert result == [(ist, soll)]
    session.select_from.assert_called_once_with(Ist)


def test_session_close() -> None:
    """Tests that closing a mocked session is a no-op."""
    session = UnifiedAlchemyMagicMock()
    assert session.close() is None


def test_with_for_update_unifies() -> None:
    """Tests that with_for_update participates in a unified query."""
    session = UnifiedAlchemyMagicMock()
    assert session.query(Model).filter(Model.pk1 == 1).with_for_update().all() == []
    session.with_for_update.assert_called_once_with()


def test_execute_insert_update_delete() -> None:
    """Tests that execute applies INSERT, UPDATE, and DELETE mutations."""
    session = UnifiedAlchemyMagicMock()

    result = session.execute(
        insert(Model).values([{"pk1": 1, "name": "one"}, {"pk1": 2, "name": "two"}])
    )
    assert result.rowcount == 2
    assert session.execute(select(Model)).scalars().all() == [
        Model(pk1=1, name="one"),
        Model(pk1=2, name="two"),
    ]

    result = session.execute(update(Model).where(Model.pk1 == 1).values(name="updated"))
    assert result.rowcount == 1

    result = session.execute(delete(Model).where(Model.pk1 == 2))
    assert result.rowcount == 1

    assert session.execute(select(Model)).scalars().all() == [
        Model(pk1=1, name="updated")
    ]
    assert session.query(Model).all() == [Model(pk1=1, name="updated")]


def test_query_len_after_filter_and_pagination() -> None:
    """Tests len() on a unified query with filters and pagination."""
    session = UnifiedAlchemyMagicMock()
    session.add(SomeClass(pk1="123", name="test"))

    assert len(session.query(SomeClass).all()) == 1
    assert len(session.query(SomeClass).filter(SomeClass.pk1 == "123")) == 1
    assert len(session.query(SomeClass).limit(10)) == 1
    assert len(session.query(SomeClass).offset(0)) == 1


def test_session_execute_mappings_for_orm_statements() -> None:
    """Tests mapping results for ORM select statements."""
    session = UnifiedAlchemyMagicMock()
    session.add(Model(pk1=1, name="one"))

    entity_mapping = session.execute(select(Model)).mappings().all()
    assert len(entity_mapping) == 1
    assert entity_mapping[0]["Model"] == Model(pk1=1, name="one")
    assert session.execute(select(Model.name)).mappings().all() == [{"name": "one"}]
    assert session.execute(select(Model.pk1, Model.name)).mappings().all() == [
        {"pk1": 1, "name": "one"}
    ]
