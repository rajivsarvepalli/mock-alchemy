"""Testing the module for utils in mock-alchemy."""

from types import SimpleNamespace

import pytest
from sqlalchemy import null
from sqlalchemy import text
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.sql import operators
from sqlalchemy.sql.expression import column

from mock_alchemy.sql_alchemy_imports import declarative_base
from mock_alchemy.utils import _MISSING
from mock_alchemy.utils import _compare_values
from mock_alchemy.utils import _get_expression_value
from mock_alchemy.utils import build_identity_map
from mock_alchemy.utils import copy_and_update
from mock_alchemy.utils import get_item_attr
from mock_alchemy.utils import get_scalar
from mock_alchemy.utils import indexof
from mock_alchemy.utils import match_row_to_clause
from mock_alchemy.utils import match_type
from mock_alchemy.utils import raiser
from mock_alchemy.utils import setattr_tmp

from .common import Model
from .common import SomeClass

Base = declarative_base()


def test_match_type() -> None:
    """Tests matching string type."""
    assert type(match_type(b"hello", bytes)) is bytes
    assert type(match_type(b"hello", str)) is str
    assert type(match_type("hello", bytes)) is bytes
    assert type(match_type(b"hello", str)) is str


def test_copy_update() -> None:
    """Tests copying and updating dictionary."""
    a = {"foo": "bar"}
    b = copy_and_update(a, {1: 2})
    assert a is not b
    assert b == {"foo": "bar", 1: 2}


def test_indexof() -> None:
    """Tests finding an index of needle in haystack."""
    a = {}
    b = {}
    haystack = [1, a, 2, b]
    assert 3 == indexof(b, haystack)
    assert 1 == indexof(a, haystack)
    with pytest.raises(ValueError):
        indexof(None, haystack)


def test_setattr_tmp() -> None:
    """Tests temporarily setting value in an object."""

    class Foo(object):
        foo = "foo"

    with setattr_tmp(Foo, "foo", "bar"):
        assert Foo.foo == "bar"
    Foo.foo = None
    with setattr_tmp(Foo, "foo", "bar"):
        assert Foo.foo is None


def test_raiser() -> None:
    """Tests utility for raising exceptions."""

    def test_func(x: bool) -> None:
        not x and raiser(ValueError, "error message")

    _ = test_func(True)
    with pytest.raises(ValueError) as excinfo:
        _ = test_func(False)
    assert "error message" in str(excinfo.value)


def test_idmap() -> None:
    """Tests building an idmap."""
    expected_idmap = {(1, 2): 1}
    idmap = build_identity_map([SomeClass(pk1=1, pk2=2)])
    assert str(expected_idmap) == str(idmap)


def test_get_attr() -> None:
    """Tests utility for accessing dict by different key types (for get)."""
    idmap = {(1,): 2}
    assert 2 == get_item_attr(idmap, 1)
    assert 2 == get_item_attr(idmap, {"pk": 1})
    assert 2 == get_item_attr(idmap, (1,))


def test_get_scalar() -> None:
    """Tests utility for getting scalar values."""
    assert 1 == get_scalar([(1, 2)])
    assert None is get_scalar([(None, 2)])
    assert None is get_scalar([])
    with pytest.raises(MultipleResultsFound):
        get_scalar([(1, 2), (2, 3)])


def test_get_scalar_mapping() -> None:
    """Tests getting scalar values from mapping rows."""
    assert 1 == get_scalar([{"pk1": 1, "pk2": 2}])
    assert None is get_scalar([{}])


def test_missing_value_repr() -> None:
    """Tests the representation of the missing value sentinel."""
    assert "<missing>" == repr(_MISSING)


def test_get_expression_value() -> None:
    """Tests resolving expression values from rows and mappings."""
    row = SimpleNamespace(name="foo")
    assert _get_expression_value(None, row) is None
    assert _get_expression_value(null(), row) is None
    assert _get_expression_value(column("name"), row) == "foo"
    assert _get_expression_value(column("missing"), row) is _MISSING

    model = Model(pk1=1, name="one")
    assert _get_expression_value(Model.pk1, model) == 1
    assert _get_expression_value(Model.pk1, {"pk1": 7}) == 7
    assert _get_expression_value(column("name"), model) == "one"
    assert _get_expression_value(SomeClass.pk2, model) is _MISSING

    class ValueOnly(object):
        """An expression-like object that only exposes a value."""

        value = 5

    assert _get_expression_value(ValueOnly(), row) == 5
    expression = object()
    assert _get_expression_value(expression, row) is expression


def test_compare_values() -> None:
    """Tests comparing values using SQLAlchemy operators."""
    assert _compare_values(operators.eq, 1, 1)
    assert not _compare_values(operators.eq, _MISSING, 1)
    assert not _compare_values(operators.eq, 1, _MISSING)
    assert not _compare_values(operators.is_, _MISSING, _MISSING)
    assert not _compare_values(object(), 1, 2)
    assert not _compare_values(operators.lt, "a", 1)


def test_match_row_to_clause() -> None:
    """Tests matching mocked rows against SQLAlchemy WHERE clauses."""
    row = SimpleNamespace(name="foo", age=12)
    assert match_row_to_clause(row, None)
    assert match_row_to_clause(row, column("name") == "foo")
    assert match_row_to_clause(row, (column("name") == "foo") & (column("age") < 18))
    assert not match_row_to_clause(
        row, (column("name") == "bar") & (column("age") < 18)
    )
    assert match_row_to_clause(row, (column("name") == "bar") | (column("age") < 18))
    assert not match_row_to_clause(row, column("name").desc())
    assert not match_row_to_clause(row, text("select 1"))
