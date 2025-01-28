"""Testing the module for mocking in mock-alchemy."""
from __future__ import annotations

from unittest import mock

import pytest
from packaging import version
from sqlalchemy import __version__ as sqlalchemy_version
from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy import update
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.sql.expression import column

from mock_alchemy.mocking import AlchemyMagicMock
from mock_alchemy.mocking import UnifiedAlchemyMagicMock
from mock_alchemy.sql_alchemy_imports import declarative_base

from .common import Concrete
from .common import Data
from .common import Model
from .common import SomeClass

Base = declarative_base()


@pytest.mark.skipif(
    version.parse(sqlalchemy_version) < version.parse("1.4.0"),
    reason="requires sqlalchemy 1.4.0 or higher to run",
)
def test_alchemy_magic_mock() -> None:
    """Tests mock for SQLAlchemy that compares alchemys expressions in assertions."""
    c = column("column")
    s = AlchemyMagicMock()
    _ = s.where(or_(c == 5, c == 10))
    _ = s.where.assert_called_once_with(or_(c == 5, c == 10))
    _ = s.where.assert_any_call(or_(c == 5, c == 10))
    _ = s.where.assert_has_calls([mock.call(or_(c == 5, c == 10))])
    s.reset_mock()
    _ = s.filter(c == 5)
    with pytest.raises(AssertionError):
        _ = s.filter.assert_called_once_with(c == 10)


@pytest.mark.skipif(
    version.parse(sqlalchemy_version) < version.parse("1.4.0"),
    reason="requires sqlalchemy 1.4.0 or higher to run",
)
def test_unified_magic_mock() -> None:
    """Tests mock for SQLAlchemy that unifies session functions for simple asserts."""
    c = column("column")
    s = UnifiedAlchemyMagicMock()
    ret = s.execute(select(None).where(c == "one").where(c == "two")).all()
    assert ret == []
    ret = s.execute(select(None).where(c == "three").where(c == "four")).all()
    assert ret == []
    assert 2 == s.execute.call_count
    _ = s.execute.assert_any_call(select(None).where(c == "one", c == "two"))
    _ = s.execute.assert_any_call(select(None).where(c == "three", c == "four"))
    s = UnifiedAlchemyMagicMock(
        data=[
            (
                [mock.call.execute(select(text("foo")).where(c == "one", c == "two"))],
                [SomeClass(pk1=1, pk2=1), SomeClass(pk1=2, pk2=2)],
            ),
            (
                [
                    mock.call.execute(
                        select(text("foo")).where(c == "one", c == "two").order_by(c)
                    ),
                ],
                [SomeClass(pk1=2, pk2=2), SomeClass(pk1=1, pk2=1)],
            ),
            (
                [mock.call.execute(select(text("foo")).where(c == "three"))],
                [SomeClass(pk1=3, pk2=3)],
            ),
        ]
    )
    ret = s.execute(
        select(text("foo")).where(c == "one").where(c == "three").order_by(c)
    ).all()
    assert [] == ret
    ret = s.execute(select(text("foo")).where(c == "one").where(c == "two")).all()
    expected_ret = [SomeClass(pk1=1, pk2=1), SomeClass(pk1=2, pk2=2)]
    assert expected_ret == ret
    ret = list(s.execute(select(text("foo")).where(c == "one").where(c == "two")))
    assert expected_ret == ret
    ret = s.execute(select(text("bar")).where(c == "one").where(c == "two")).all()
    assert ret == []
    ret = s.execute(
        select(text("foo")).where(c == "one").where(c == "two").order_by(c)
    ).all()
    expected_ret = [SomeClass(pk1=2, pk2=2), SomeClass(pk1=1, pk2=1)]
    assert expected_ret == ret
    ret = list(s.execute(select(text("foo")).where(c == "two").where(c == "one")))
    ret = s.execute(select(text("foo")).where(c == "one").where(c == "two")).first()
    assert ret == SomeClass(pk1=1, pk2=1)
    ret = s.execute(select(text("foo")).where(c == "three")).one()
    assert ret == SomeClass(pk1=3, pk2=3)
    s = UnifiedAlchemyMagicMock()
    ret = s.execute(
        insert(SomeClass).returning(SomeClass), [{"pk1": 1, "pk2": 1}]
    ).scalar()
    expected_ret = SomeClass(pk1=1, pk2=1)
    assert ret == expected_ret
    s.execute(insert(SomeClass), [{"pk1": 2, "pk2": 2}])
    ret = s.execute(select(SomeClass)).all()
    expected_ret = [SomeClass(pk1=1, pk2=1), SomeClass(pk1=2, pk2=2)]
    assert ret == expected_ret
    ret = s.execute(delete(SomeClass))
    assert ret.rowcount == 2
    ret = s.execute(delete(SomeClass))
    assert ret.rowcount == 0
    s = UnifiedAlchemyMagicMock()
    s.execute(insert(SomeClass), [{"pk1": 1, "pk2": 2}])
    s.execute(insert(Model), [{"pk1": 1, "name": "test"}])
    s.execute(insert(Model), [{"pk1": 5, "name": "test"}])
    ret = s.execute(delete(SomeClass))
    assert ret.rowcount == 1
    ret = s.execute(delete(SomeClass))
    assert ret.rowcount == 0
    s = UnifiedAlchemyMagicMock()
    assert s.all() == []
    s = UnifiedAlchemyMagicMock(
        data=[
            (
                [mock.call.execute(select(Model).where(Model.pk1 < 1))],
                [Model(pk1=1, name="test1")],
            ),
            (
                [mock.call.execute(select(Model))],
                [Model(pk1=2, name="test2")],
            ),
        ]
    )
    ret = s.execute(select(Model).where(Model.pk1 < 1)).all()
    assert ret == [Model(pk1=1, name="test1")]
    ret = s.execute(delete(Model).where(Model.pk1 < 1))
    assert ret.rowcount == 1
    ret = s.execute(select(Model)).all()
    assert ret == [Model(pk1=2, name="test2")]
    ret = s.execute(select(Model).where(Model.pk1 < 1)).all()
    assert ret == []
    # todo: implement session.get(). For example s.get(Model, 2) should return
    # Model(pk1=2, name="test2")
    s = UnifiedAlchemyMagicMock(
        data=[
            (
                [mock.call.execute(select(Model).where(Model.pk1 < 1))],
                [Model(pk1=1, name="test1")],
            ),
            (
                [mock.call.execute(select(Model))],
                [Model(pk1=2, name="test2")],
            ),
        ]
    )
    ret = s.execute(select(Model).where(Model.pk1 < 1)).all()
    ret = [str(r) for r in ret]
    assert ret == ["1"]
    ret = s.execute(delete(Model).where(Model.pk1 < 1))
    assert ret.rowcount == 1
    ret = s.execute(select(Model)).all()
    ret = [str(r) for r in ret]
    assert ret == ["2"]
    ret = s.execute(select(Model).where(Model.pk1 < 1)).all()
    assert ret == []
    s = UnifiedAlchemyMagicMock()
    ret = s.execute(delete(Model))
    assert ret.rowcount == 0


@pytest.mark.skipif(
    version.parse(sqlalchemy_version) < version.parse("1.4.0"),
    reason="requires sqlalchemy 1.4.0 or higher to run",
)
def test_complex_session() -> None:
    """Tests mock for SQLAlchemy with more complex session."""
    s = UnifiedAlchemyMagicMock(
        data=[
            (
                [mock.call.execute(select(Data).where(Data.data_p1 < 13))],
                [
                    Data(pk1=1, data_p1=11.4, data_p2=13.5, name="test1"),
                    Data(pk1=2, data_p1=9.4, data_p2=19.5, name="test2"),
                    Data(pk1=3, data_p1=4.7, data_p2=15.5, name="test3"),
                    Data(pk1=4, data_p1=3.4, data_p2=13.5, name="test4"),
                ],
            ),
            (
                [mock.call.execute(select(Data).where(Data.data_p1 >= 13))],
                [
                    Data(pk1=5, data_p1=16.3, data_p2=3.5, name="test6"),
                    Data(pk1=6, data_p1=19.3, data_p2=10.5, name="test7"),
                    Data(pk1=7, data_p1=13.3, data_p2=33.7, name="test8"),
                ],
            ),
        ]
    )
    new_data = [
        {"pk1": 8, "data_p1": 16.3, "data_p2": 38.15, "name": "test9"},
        {"pk1": 9, "data_p1": 13.6, "data_p2": 33.5, "name": "test10"},
        {"pk1": 10, "data_p1": 10.1, "data_p2": 331.35, "name": "test11"},
        {"pk1": 1, "data_p1": 2.5, "data_p2": 67.1, "name": "test12"},
    ]
    s.execute(insert(Data), new_data)
    s.execute(
        insert(Data), [{"pk1": 11, "data_p1": 31.5, "data_p2": 67.1, "name": "test13"}]
    )
    ret = s.execute(select(Data)).all()
    expected_data = [str(r) for r in ret]
    assert expected_data == ["8test9", "9test10", "10test11", "1test12", "11test13"]
    n_d = s.execute(delete(Data).where(Data.data_p1 < 13))
    assert n_d.rowcount == 4
    n_d = s.execute(delete(Data).where(Data.data_p1 >= 13))
    assert n_d.rowcount == 3
    ret = s.execute(select(Data).where(Data.data_p1 >= 13)).all()
    assert ret == []
    ret = s.execute(select(Data)).all()
    expected_data = [str(r) for r in ret]
    assert expected_data == ["8test9", "9test10", "10test11", "1test12", "11test13"]
    ret = s.execute(select(Data).where(Data.data_p1 < 13)).all()
    assert ret == []


@pytest.mark.skipif(
    version.parse(sqlalchemy_version) < version.parse("1.4.0"),
    reason="requires sqlalchemy 1.4.0 or higher to run",
)
def test_abstract_classes() -> None:
    """Tests mock for SQLAlchemy with inheritance and abstract classes."""
    objs = Concrete(id=1)
    session = UnifiedAlchemyMagicMock(
        data=[
            ([mock.call.execute(select(Concrete))], [objs]),
        ]
    )
    ret = session.execute(select(Concrete)).first()
    assert ret == objs


@pytest.mark.skipif(
    version.parse(sqlalchemy_version) < version.parse("2.0.0"),
    reason="requires sqlalchemy 2.0.0 or higher to insert using .values()",
)
def test_scalar_singular() -> None:
    """Tests mock for SQLAlchemy with scalar when there is one row."""
    mock_session = UnifiedAlchemyMagicMock()
    expected_model = Model(pk1="123", name="test")
    mock_session.execute(insert(Model).values([{"pk1": "123", "name": "test"}]))
    actual_model = mock_session.execute(select(Model)).scalar()
    assert expected_model == actual_model


@pytest.mark.skipif(
    version.parse(sqlalchemy_version) < version.parse("1.4.0"),
    reason="requires sqlalchemy 1.4.0 or higher to run",
)
def test_scalar_none() -> None:
    """Tests mock for SQLAlchemy with scalar when rows are empty."""
    mock_session = UnifiedAlchemyMagicMock()
    data = mock_session.execute(select(Model)).scalar()
    assert data is None


@pytest.mark.skipif(
    version.parse(sqlalchemy_version) < version.parse("2.0.0"),
    reason="requires sqlalchemy 2.0.0 or higher to insert using .values()",
)
def test_scalar_multiple() -> None:
    """Tests mock for SQLAlchemy with scalar when there are many rows."""
    mock_session = UnifiedAlchemyMagicMock()
    mock_session.execute(
        insert(Model).values(
            [{"pk1": "123", "name": "test"}, {"pk1": "1234", "name": "test"}]
        )
    )
    with pytest.raises(MultipleResultsFound):
        mock_session.execute(select(Model)).scalar()


@pytest.mark.skipif(
    version.parse(sqlalchemy_version) < version.parse("1.4.0"),
    reason="requires sqlalchemy 1.4.0 or higher to run",
)
def test_scalar_attribute() -> None:
    """Tests mock for SQLAlchemy with scalar for getting an attribute."""
    expected_column_val = "test"
    mock_session = UnifiedAlchemyMagicMock(
        data=[
            (
                [
                    mock.call.execute(select(Model.name).where(Model.pk1 == 3)),
                ],
                [(expected_column_val,)],
            )
        ]
    )
    data_column = mock_session.execute(
        select(Model.name).where(Model.pk1 == 3)
    ).scalar()
    assert expected_column_val == data_column


@pytest.mark.skipif(
    version.parse(sqlalchemy_version) < version.parse("1.4.0"),
    reason="requires sqlalchemy 1.4.0 or higher to run",
)
def test_update_calls() -> None:
    """Tests that update calls update dta in UnifiedAlchemyMagicMock sessions."""
    expected_row = [Model(pk1="1234", name="test")]
    mock_session = UnifiedAlchemyMagicMock(
        data=[
            (
                [
                    mock.call.execute(select(Model).where(Model.pk1 == 3)),
                ],
                expected_row,
            )
        ]
    )
    # Test all()
    actual_row = mock_session.execute(select(Model).where(Model.pk1 == 3)).all()
    assert expected_row == actual_row
    assert actual_row[0].pk1 == "1234"
    # Make sure updating something that doesn't exist does nothing
    mock_session.execute(update(Model).where(Model.pk1 == 5).values({"pk1": 3}))
    actual_row = mock_session.execute(select(Model).where(Model.pk1 == 3)).all()
    assert expected_row == actual_row
    assert actual_row[0].pk1 == "1234"
    # Update actual row
    mock_session.execute(update(Model).where(Model.pk1 == 3).values({"pk1": 3}))
    actual_row = mock_session.execute(select(Model).where(Model.pk1 == 3)).all()
    assert actual_row[0].pk1 == 3
    # Test delete()
    deleted_count = mock_session.execute(delete(Model).where(Model.pk1 == 3)).rowcount
    assert 1 == deleted_count
    actual_row = mock_session.execute(select(Model).where(Model.pk1 == 3)).all()
    assert [] == actual_row
