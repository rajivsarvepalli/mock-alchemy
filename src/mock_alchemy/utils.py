"""A module for utils for the ``mock-alchemy`` library."""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any
from typing import Callable
from typing import Dict
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import Union

from sqlalchemy import inspect
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import UnmappedColumnError
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.elements import BindParameter
from sqlalchemy.sql.elements import BooleanClauseList
from sqlalchemy.sql.elements import Null
from sqlalchemy.sql.elements import UnaryExpression


def match_type(
    s: Union[bytes, str], t: Union[Type[bytes], Type[str]]
) -> Union[bytes, str]:
    """Match the string type.

    Matches the string type with the provided type and returns the string
    of the desired type.

    Args:
        s: The string to match the type with.
        t: The type to make the string with.

    Returns:
        An object of the desired type of type ``t``.

    For example::

        >>> assert type(match_type(b'hello', bytes)) is bytes
        >>> assert type(match_type(u'hello', str)) is str
        >>> assert type(match_type(b'hello', str)) is str
        >>> assert type(match_type(u'hello', bytes)) is bytes
    """
    if isinstance(s, t):
        return s
    if t is str:
        return s.decode("utf-8")
    else:
        return s.encode("utf-8")


def copy_and_update(target: Dict, updater: Dict) -> Dict:
    """Copy and update dictionary.

    Copy dictionary and update it all in one operation.

    Args:
        target: The dictionary to copy and update.
        updater: The updating dictionary.

    Returns:
        Dict: A new dictionary of the ``target`` copied and
        updated by ``updater``.

    For example::

        >>> a = {'foo': 'bar'}
        >>> b = copy_and_update(a, {1: 2})
        >>> a is b
        False
        >>> b == {'foo': 'bar', 1: 2}
        True
    """
    result = target.copy()
    result.update(updater)
    return result


def indexof(needle: Any, haystack: Sequence[Any]) -> int:
    """Gets the index of some item in a sequence.

    Find an index of ``needle`` in ``haystack`` by looking for exact same
    item by pointer ids vs usual ``list.index()`` which finds
    by object comparison.

    Args:
        needle: The object or item to find in the sequence.
        haystack: The sequence of items to search for the ``needle``.

    Returns:
        The index of the needle in the haystack.

    Raises:
        ValueError: If the needle is not found inside the haystack.

    For example::

        >>> a = {}
        >>> b = {}
        >>> haystack = [1, a, 2, b]
        >>> indexof(b, haystack)
        3
        >>> indexof(None, haystack)
        Traceback (most recent call last):
        ...
        ValueError: None is not in [1, {}, 2, {}]
    """
    for i, item in enumerate(haystack):
        if needle is item:
            return i
    raise ValueError("{!r} is not in {!r}".format(needle, haystack))


@contextmanager
def setattr_tmp(obj: object, name: str, value: Any) -> Any:
    """Set the atrributes of object temporarily.

    Utility for temporarily setting value in an object.

    Args:
        obj: An object to set the attribute of.
        name: The name of the attribute.
        value: The value to set the attribute to.

    Returns:
        A context manager that can be used.

    Yields:
        Used for the context manager so that this function can be used
        as ``with setattr_tmp``.

    For example::

        >>> class Foo(object):
        ...     foo = 'foo'
        >>> print(Foo.foo)
        foo
        >>> with setattr_tmp(Foo, 'foo', 'bar'):
        ...     print(Foo.foo)
        bar
        >>> print(Foo.foo)
        foo

        >>> Foo.foo = None
        >>> with setattr_tmp(Foo, 'foo', 'bar'):
        ...     print(Foo.foo)
        None
    """
    original = getattr(obj, name)

    if original is None:
        yield
        return

    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, original)


def raiser(exp: Type[Exception], *args: Any, **kwargs: Any) -> Type[Exception]:
    """Raises an exception with the given args.

    Utility for raising exceptions
    Useful in one-liners.

    Args:
        exp: The exception to raise.
        args: The args to use for the exception.
        kwargs: The kwargs to use for the exception.

    Raises:
        exp: The parameterized exception of the specified kind.

    For example::

        >>> a = lambda x: not x and raiser(ValueError, 'error message')
        >>> _ = a(True)
        >>> _ = a(False)
        Traceback (most recent call last):
        ...
        ValueError: error message
    """
    raise exp(*args, **kwargs)


def build_identity_map(items: Sequence[Any]) -> Dict:
    """Builds identity map.

    Utility for building identity map from given SQLAlchemy models.

    Args:
        items: A sequence of SQLAlchemy objects.

    Returns:
        An identity map of the given SQLAlchemy objects.

    For example::

        >>> from sqlalchemy import Column, Integer, String
        >>> from sqlalchemy.ext.declarative import declarative_base

        >>> Base = declarative_base()

        >>> class SomeClass(Base):
        ...     __tablename__ = 'some_table'
        ...     pk1 = Column(Integer, primary_key=True)
        ...     pk2 = Column(Integer, primary_key=True)
        ...     name =  Column(String(50))
        ...     def __repr__(self):
        ...         return str(self.pk1)

        >>> build_identity_map([SomeClass(pk1=1, pk2=2)])
        {(1, 2): 1}
    """
    idmap = {}

    for i in items:
        mapper = inspect(type(i)).mapper
        pk_keys = tuple(
            mapper.get_property_by_column(c).key for c in mapper.primary_key
        )
        pk = tuple(getattr(i, k) for k in sorted(pk_keys))
        idmap[pk] = i

    return idmap


def get_item_attr(idmap: Dict, access: Union[Dict, Tuple, Any]) -> Any:
    """Access dictionary in different methods.

    Utility for accessing dict by different key types (for get).

    Args:
        idmap: A dictionary of identity map of SQLAlchemy objects.
        access: The access pattern which should either be basic data type, dictionary,
            or a tuple. If it is dictionary it should map to the names of the primary
            keys of the SQLAlchemy objects. If it is a tuple, it should be a set of
            keys to search for. If it is not a dict or a tuple, then the objects in
            question must have only one primary key of the type passed
            (such as a string, integer, etc.).

    Returns:
        An SQlAlchemy object that was requested.

    For example::
        >>> idmap = {(1,): 2}
        >>> get_item_attr(idmap, 1)
        2
        >>> idmap = {(1,): 2}
        >>> get_item_attr(idmap, {"pk": 1})
        2
        >>> get_item_attr(idmap, (1,))
        2
    """
    if isinstance(access, dict):
        keys = []
        for names in sorted(access):
            keys.append(access[names])
        return idmap.get(tuple(keys))
    elif isinstance(access, tuple):
        return idmap.get(access)
    else:
        return idmap.get((access,))


def get_scalar(rows: Sequence[Any]) -> Any:
    """Utility for mocking sqlalchemy.orm.Query.scalar()."""
    if len(rows) == 1:
        row = rows[0]
        if isinstance(row, Mapping):
            return next(iter(row.values()), None)
        try:
            return row[0]
        except (TypeError, KeyError, IndexError):
            return row
    elif len(rows) > 1:
        raise MultipleResultsFound(
            "Multiple rows were found when exactly one was required"
        )
    return None


class _MissingValue(object):
    """Sentinel indicating that a value could not be resolved from a row."""

    def __repr__(self) -> str:
        """Represent the missing value."""
        return "<missing>"


_MISSING = _MissingValue()


def _get_identifier(expression: Any) -> Any:
    """Get the row attribute name for a SQLAlchemy expression."""
    return getattr(expression, "key", getattr(expression, "name", None))


def _get_expression_value(expression: Any, row: Any) -> Any:
    """Get the value of a SQLAlchemy expression for a given row.

    Args:
        expression: The left or right side of a SQLAlchemy expression.
        row: The object or mapping representing a row.

    Returns:
        The resolved value or the missing value sentinel.
    """
    if expression is None or isinstance(expression, Null):
        return None
    if isinstance(expression, BindParameter):
        return expression.value
    identifier = _get_identifier(expression)
    mapper = getattr(type(row), "__mapper__", None)
    if mapper is not None and hasattr(expression, "table"):
        try:
            identifier = mapper.get_property_by_column(expression).key
        except UnmappedColumnError:
            pass
    if identifier is not None:
        if isinstance(row, Mapping):
            return row.get(identifier, _MISSING)
        if hasattr(row, identifier):
            return getattr(row, identifier)
        return _MISSING
    if hasattr(expression, "value"):
        return expression.value
    return expression


_COMPARISON_FUNCTIONS: Dict[Any, Callable[[Any, Any], bool]] = {
    operators.eq: lambda left, right: left == right,
    operators.ne: lambda left, right: left != right,
    operators.lt: lambda left, right: left < right,
    operators.le: lambda left, right: left <= right,
    operators.gt: lambda left, right: left > right,
    operators.ge: lambda left, right: left >= right,
    operators.is_: lambda left, right: left is right,
    operators.is_not: lambda left, right: left is not right,
    operators.in_op: lambda left, right: left in right,
    operators.not_in_op: lambda left, right: left not in right,
}


def _compare_values(operator: Any, left: Any, right: Any) -> bool:
    """Compare two values using a SQLAlchemy operator.

    Args:
        operator: The SQLAlchemy operator.
        left: The left-hand value.
        right: The right-hand value.

    Returns:
        Whether the comparison is true.
    """
    if left is _MISSING or right is _MISSING:
        return False
    comparison = _COMPARISON_FUNCTIONS.get(operator)
    if comparison is None:
        return False
    try:
        return bool(comparison(left, right))
    except (TypeError, ValueError):
        return False


def match_row_to_clause(row: Any, clause: Any) -> bool:
    """Check whether a mocked row matches a SQLAlchemy WHERE clause.

    This is used to apply the effects of ``UPDATE`` and ``DELETE`` statements to
    dynamically mocked data. Only the common SQLAlchemy operators are supported;
    clauses that cannot be evaluated against the mocked row return ``False`` so
    that data is not accidentally mutated.

    Args:
        row: A model instance or mapping representing a row.
        clause: The SQLAlchemy WHERE clause.

    Returns:
        Whether the row matches the clause.

    For example::

        >>> from types import SimpleNamespace
        >>> from sqlalchemy.sql.expression import column
        >>> row = SimpleNamespace(name='foo', age=12)
        >>> match_row_to_clause(row, column('age') >= 18)
        False
        >>> match_row_to_clause(row, column('name') == 'foo')
        True
        >>> match_row_to_clause(row, (column('name') == 'foo') & (column('age') < 18))
        True
    """
    if clause is None:
        return True
    if isinstance(clause, BooleanClauseList):
        clauses = list(clause.clauses)
        if clause.operator is operators.or_:
            return any(match_row_to_clause(row, c) for c in clauses)
        return all(match_row_to_clause(row, c) for c in clauses)
    if isinstance(clause, UnaryExpression):
        return match_row_to_clause(row, clause.element)
    if isinstance(clause, BinaryExpression):
        left = _get_expression_value(clause.left, row)
        right = _get_expression_value(clause.right, row)
        return _compare_values(clause.operator, left, right)
    return False
