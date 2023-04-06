"""Testing the module for comparison in mock-alchemy."""
from unittest import mock

import pytest
import sqlalchemy
from packaging import version
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.sql.expression import column

from mock_alchemy.comparison import ExpressionMatcher
from mock_alchemy.comparison import PrettyExpression


def test_pretty_expression() -> None:
    """Tests pretty representations of SQLAlchemy expressions."""
    c = column("column")
    str_repr = (
        """BinaryExpression(sql='"column" = :column_1', params={'column_1': 5})"""
    )
    assert str(PrettyExpression(c == 5)) == str_repr
    assert str(PrettyExpression(PrettyExpression(15))) == "15"


def test_expression_matcher() -> None:
    """Tests expression matching of SQLAlchemy expressions."""
    c = column("column")
    e1 = c.in_(["foo", "bar"])
    e2 = c.in_(["foo", "bar"])
    e3 = c.in_(["cat", "dog"])
    e5 = func.lower(c)
    assert ExpressionMatcher(e1) == e2
    assert ExpressionMatcher({"foo": c == "foo", "bar": 5, "hello": "world"}) == {
        "foo": c == "foo",
        "bar": 5,
        "hello": "world",
    }
    assert ExpressionMatcher(e1) == e2
    assert ExpressionMatcher(ExpressionMatcher(e1)) == ExpressionMatcher(e2)
    assert ExpressionMatcher(e1) == mock.ANY
    assert ExpressionMatcher(e1) == e2
    assert ExpressionMatcher(e5) != func.upper(c)
    l1 = c.label("foo")
    l2 = c.label("foo")
    c2 = column("column2")
    l4 = c2.label("foo")
    assert ExpressionMatcher(c) != l1
    assert ExpressionMatcher(l1) == l2
    assert ExpressionMatcher([c == "foo"]) == [c == "foo"]
    assert ExpressionMatcher(l1) != l4
    assert ExpressionMatcher(e1) != e3
    assert ExpressionMatcher(column("column") == "one") != ExpressionMatcher(
        column("column") == "three"
    )


@pytest.mark.skipif(
    version.parse(sqlalchemy.__version__) < version.parse("1.4.0"),
    reason="requires sqlalchemy 1.4.0 or higher to run",
)
def test_expression_matcher_select() -> None:
    """Tests expression matching of SQLAlchemy expressions using select statements."""
    c = column("column")
    e6 = select(c)
    e7 = select(c)
    e8 = select(1)
    e9 = select(2)
    assert ExpressionMatcher(e6) == e7
    assert ExpressionMatcher(e6) != e8
    assert ExpressionMatcher(e6) != e9
    assert ExpressionMatcher(e8) != e9
