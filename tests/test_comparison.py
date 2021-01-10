"""Testing the module for comparison in mock-alchemy."""
from unittest import mock

from sqlalchemy import func
from sqlalchemy.sql.expression import column, or_

from mock_alchemy.comparison import ExpressionMatcher, PrettyExpression


def test_pretty_expression() -> None:
    """Tests pretty representations of SqlAlchemy expressions."""
    c = column("column")
    str_repr = (
        """BinaryExpression(sql='"column" = :column_1', params={'column_1': 5})"""
    )
    assert str(PrettyExpression(c == 5)) == str_repr
    assert str(PrettyExpression(PrettyExpression(15))) == "15"


def test_expression_matcher() -> None:
    """Tests expression matching of SqlAlchemy expressions."""
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
