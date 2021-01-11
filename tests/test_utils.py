"""Testing the module for utils in mock-alchemy."""
import pytest
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base

from mock_alchemy.utils import build_identity_map
from mock_alchemy.utils import copy_and_update
from mock_alchemy.utils import get_item_attr
from mock_alchemy.utils import indexof
from mock_alchemy.utils import match_type
from mock_alchemy.utils import raiser
from mock_alchemy.utils import setattr_tmp

Base = declarative_base()


def test_match_type() -> None:
    """Tests matching string type."""
    assert type(match_type(b"hello", bytes)) is bytes
    assert type(match_type(b"hello", str)) is str
    assert type(match_type(u"hello", bytes)) is bytes
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

    class SomeClass(Base):
        __tablename__ = "some_table"
        pk1 = Column(Integer, primary_key=True)
        pk2 = Column(Integer, primary_key=True)
        name = Column(String(50))

        def __repr__(self) -> str:
            return str(self.pk1)

    expected_idmap = {(1, 2): 1}
    idmap = build_identity_map([SomeClass(pk1=1, pk2=2)])
    assert str(expected_idmap) == str(idmap)


def test_get_attr() -> None:
    """Tests utility for accessing dict by different key types (for get)."""
    idmap = {(1,): 2}
    assert 2 == get_item_attr(idmap, 1)
    assert 2 == get_item_attr(idmap, {"pk": 1})
    assert 2 == get_item_attr(idmap, (1,))
