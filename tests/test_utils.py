"""Testing the module for utils in mock-alchemy."""
import pytest
from sqlalchemy.orm.exc import MultipleResultsFound

from mock_alchemy.sql_alchemy_imports import declarative_base
from mock_alchemy.utils import build_identity_map
from mock_alchemy.utils import copy_and_update
from mock_alchemy.utils import get_item_attr
from mock_alchemy.utils import get_scalar
from mock_alchemy.utils import indexof
from mock_alchemy.utils import match_type
from mock_alchemy.utils import raiser
from mock_alchemy.utils import setattr_tmp

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
