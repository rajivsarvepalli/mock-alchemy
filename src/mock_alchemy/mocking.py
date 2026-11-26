"""A module for basic mocking of SQLAlchemy sessions and calls."""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from collections.abc import Mapping
from functools import partial
from itertools import takewhile
from typing import Any
from typing import Callable
from typing import Dict
from typing import Generator
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence
from typing import Set
from typing import Tuple
from typing import overload
from unittest import mock

from sqlalchemy import Delete
from sqlalchemy import Insert
from sqlalchemy import Update
from sqlalchemy import select
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.exc import UnmappedColumnError
from sqlalchemy.sql.elements import ClauseElement

from .comparison import ExpressionMatcher
from .utils import build_identity_map
from .utils import copy_and_update
from .utils import get_item_attr
from .utils import get_scalar
from .utils import indexof
from .utils import match_row_to_clause
from .utils import raiser
from .utils import setattr_tmp

Call = type(mock.call)

__all__ = [
    "AlchemyMagicMock",
    "UnifiedAlchemyMagicMock",
    "UnifiedAlchemyMappingResult",
    "UnifiedAlchemyResult",
    "UnifiedAlchemyScalarResult",
    "UnorderedCall",
    "UnorderedTuple",
    "sqlalchemy_call",
]

_DEFAULT_RETURN_VALUE = object()


class UnorderedTuple(tuple):
    """Same as tuple except in comparison order does not matter.

    A tuple in which order does not matter for equality. It compares
    by remove elements from the other tuple.

    For example::

        >>> UnorderedTuple((1, 2, 3)) == (3, 2, 1)
        True
    """

    def __eq__(self, other: tuple) -> bool:
        """Compares another tuple for equality."""
        if len(self) != len(other):
            return False

        remaining = list(other)
        for i in self:
            try:
                remaining.remove(i)
            except ValueError:
                return False

        return True


class UnorderedCall(Call):
    """Same as Call except in comparison order of parameters does not matter.

    A ``mock.Call`` subclass that ensures that eqaulity does not depend on order.
    This isued to check if SQLAlchemy calls match up regardless of order. For example,
    this is useful in the case of filtering when ``.filter(y == 4).filter(y == 2)``
    is the same as ``.filter(y == 2).filter(y == 4)``.

    For example::

        >>> a = ((1, 2, 3), {'hello': 'world'})
        >>> b = ((3, 2, 1), {'hello': 'world'})
        >>> UnorderedCall(a) == Call(b)
        True
    """

    def __eq__(self, other: Call) -> bool:
        """Compares another call for equality."""
        _other = list(other)
        _other[-2] = UnorderedTuple(other[-2])
        other = Call(
            tuple(_other),
            **{k.replace("_mock_", ""): v for k, v in vars(other).items()},
        )

        return super(UnorderedCall, self).__eq__(other)


def _get_selected_column_keys(statement: Optional[Any]) -> List[str]:
    """Get the column keys selected by a SQLAlchemy statement.

    Args:
        statement: A SQLAlchemy statement or ``None``.

    Returns:
        A list of column keys in the order they are selected.
    """
    if statement is None:
        return []
    descriptions = getattr(statement, "column_descriptions", None)
    if descriptions:
        keys = []
        for description in descriptions:
            expression = description.get("expr")
            key = getattr(expression, "key", None)
            if key is None:
                key = description.get("name")
            if key is not None:
                keys.append(key)
        return keys
    selected_columns = getattr(statement, "selected_columns", None)
    if selected_columns is None:
        return []
    return [
        getattr(column, "key", getattr(column, "name", str(column)))
        for column in selected_columns
    ]


class UnifiedAlchemyScalarResult(object):
    """A result object that only exposes scalar values.

    This mirrors the object returned by ``Result.scalars()`` in SQLAlchemy.
    """

    def __init__(self, rows: Sequence[Any]) -> None:
        """Create a scalar result from the given rows."""
        self._rows = list(rows)

    def _scalar_value(self, row: Any) -> Any:
        """Get the scalar value from a row."""
        if isinstance(row, (list, tuple)) and row:
            return row[0]
        return row

    def all(self) -> List[Any]:
        """Return all scalar values as a list."""
        return [self._scalar_value(r) for r in self._rows]

    def fetchall(self) -> List[Any]:
        """Return all scalar values as a list."""
        return self.all()

    def __iter__(self) -> Iterator[Any]:
        """Iterate over the scalar values."""
        return iter(self.all())

    def __len__(self) -> int:
        """Get the number of scalar values."""
        return len(self._rows)

    def first(self) -> Any:
        """Return the first scalar value or ``None``."""
        return self._scalar_value(self._rows[0]) if self._rows else None

    def one(self) -> Any:
        """Return exactly one scalar value."""
        if len(self._rows) == 1:
            return self._scalar_value(self._rows[0])
        if self._rows:
            raise MultipleResultsFound("Multiple rows were found for one()")
        raise NoResultFound("No row was found for one()")

    def one_or_none(self) -> Any:
        """Return one scalar value or ``None``."""
        if len(self._rows) == 1:
            return self._scalar_value(self._rows[0])
        if self._rows:
            raise MultipleResultsFound("Multiple rows were found for one_or_none()")
        return None

    def unique(self) -> "UnifiedAlchemyScalarResult":
        """Return this result since mocked results are already unique."""
        return self

    def freeze(self) -> "UnifiedAlchemyScalarResult":
        """Return this result since mocked results are already buffered."""
        return self

    def __await__(self) -> Generator[Any, None, "UnifiedAlchemyScalarResult"]:
        """Allow the result to be awaited by async SQLAlchemy sessions."""
        yield
        return self


class UnifiedAlchemyMappingResult(object):
    """A result object that exposes rows as mappings.

    This mirrors the object returned by ``Result.mappings()`` in SQLAlchemy.
    """

    def __init__(self, rows: Sequence[Any], statement: Optional[Any] = None) -> None:
        """Create a mapping result from the given rows."""
        self._rows = list(rows)
        self._keys = _get_selected_column_keys(statement)

    def _as_mapping(self, row: Any) -> Any:
        """Convert a single row into a mapping."""
        if isinstance(row, Mapping):
            return dict(row)

        if self._keys:
            if isinstance(row, (list, tuple)):
                if len(self._keys) == len(row):
                    return dict(zip(self._keys, row, strict=True))
                return {i: v for i, v in enumerate(row)}
            values = {}
            for key in self._keys:
                if hasattr(row, key):
                    values[key] = getattr(row, key)
            if values:
                return values
            if len(self._keys) == 1:
                return {self._keys[0]: row}

        if isinstance(row, (list, tuple)):
            return {i: v for i, v in enumerate(row)}

        return row

    def all(self) -> List[Any]:
        """Return all rows as mappings."""
        return [self._as_mapping(r) for r in self._rows]

    def fetchall(self) -> List[Any]:
        """Return all rows as mappings."""
        return self.all()

    def __iter__(self) -> Iterator[Any]:
        """Iterate over the rows as mappings."""
        return iter(self.all())

    def __len__(self) -> int:
        """Get the number of rows."""
        return len(self._rows)

    def first(self) -> Any:
        """Return the first mapping or ``None``."""
        return self._as_mapping(self._rows[0]) if self._rows else None

    def one(self) -> Any:
        """Return exactly one mapping."""
        if len(self._rows) == 1:
            return self._as_mapping(self._rows[0])
        if self._rows:
            raise MultipleResultsFound("Multiple rows were found for one()")
        raise NoResultFound("No row was found for one()")

    def one_or_none(self) -> Any:
        """Return one mapping or ``None``."""
        if len(self._rows) == 1:
            return self._as_mapping(self._rows[0])
        if self._rows:
            raise MultipleResultsFound("Multiple rows were found for one_or_none()")
        return None

    def unique(self) -> "UnifiedAlchemyMappingResult":
        """Return this result since mocked results are already unique."""
        return self

    def freeze(self) -> "UnifiedAlchemyMappingResult":
        """Return this result since mocked results are already buffered."""
        return self


class UnifiedAlchemyResult(object):
    """A SQLAlchemy ``Result``-like object returned by mock sessions.

    It supports the common terminal operations on ``Session.execute``
    results such as ``all``, ``fetchall``, ``first``, ``one``,
    ``one_or_none``, ``scalar``, ``scalars``, and ``mappings``.
    """

    def __init__(
        self,
        rows: Sequence[Any],
        statement: Optional[Any] = None,
        rowcount: Optional[int] = None,
    ) -> None:
        """Create a result from the given rows and statement."""
        self._rows = list(rows)
        self._statement = statement
        self._rowcount = len(self._rows) if rowcount is None else rowcount

    @property
    def rowcount(self) -> int:
        """Get the number of affected rows."""
        return self._rowcount

    def all(self) -> List[Any]:
        """Return all rows as a list."""
        return list(self._rows)

    def fetchall(self) -> List[Any]:
        """Return all rows as a list."""
        return self.all()

    def fetchone(self) -> Any:
        """Return the first row or ``None``."""
        return self._rows[0] if self._rows else None

    def first(self) -> Any:
        """Return the first row or ``None``."""
        return self.fetchone()

    def one(self) -> Any:
        """Return exactly one row."""
        if len(self._rows) == 1:
            return self._rows[0]
        if self._rows:
            raise MultipleResultsFound("Multiple rows were found for one()")
        raise NoResultFound("No row was found for one()")

    def one_or_none(self) -> Any:
        """Return one row or ``None``."""
        if len(self._rows) == 1:
            return self._rows[0]
        if self._rows:
            raise MultipleResultsFound("Multiple rows were found for one_or_none()")
        return None

    def scalar(self) -> Any:
        """Return the first column of the first row."""
        return get_scalar(self._rows)

    def scalars(self) -> UnifiedAlchemyScalarResult:
        """Return a scalar-only view of this result."""
        return UnifiedAlchemyScalarResult(self._rows)

    def mappings(self) -> UnifiedAlchemyMappingResult:
        """Return a mapping view of this result."""
        return UnifiedAlchemyMappingResult(self._rows, statement=self._statement)

    def count(self) -> int:
        """Get the number of rows in the result."""
        return len(self._rows)

    def unique(self) -> "UnifiedAlchemyResult":
        """Return this result since mocked results are already unique."""
        return self

    def freeze(self) -> "UnifiedAlchemyResult":
        """Return this result since mocked results are already buffered."""
        return self

    def close(self) -> None:
        """Close the result (a no-op for mocked results)."""
        return None

    def __await__(self) -> Generator[Any, None, "UnifiedAlchemyResult"]:
        """Allow the result to be awaited by async SQLAlchemy sessions."""
        yield
        return self

    def __iter__(self) -> Iterator[Any]:
        """Iterate over the rows."""
        return iter(self._rows)

    def __len__(self) -> int:
        """Get the number of rows."""
        return len(self._rows)

    def __getitem__(self, index: int) -> Any:
        """Get a row by index."""
        return self._rows[index]


def sqlalchemy_call(call: Call, with_name: bool = False, base_call: Any = Call) -> Any:
    """Convert ``mock.call()`` into call.

    Convert ``mock.call()`` into call with all parameters
    wrapped with ``ExpressionMatcher``. This is useful for comparing
    SQLAlchemy statements for equality.

    Args:
        call: The call to convert.
        with_name: Whether to convert the name of the call.
        base_call: The type of call to convert into.

    Returns:
        Returns the converted call of the type ``base_call``.

    For example::

        >>> args, kwargs = sqlalchemy_call(mock.call(5, foo='bar'))
        >>> isinstance(args[0], ExpressionMatcher)
        True
        >>> isinstance(kwargs['foo'], ExpressionMatcher)
        True
    """
    try:
        args, kwargs = call
    except ValueError:
        name, args, kwargs = call
    else:
        name = ""

    args = tuple([ExpressionMatcher(i) for i in args])
    kwargs = {k: ExpressionMatcher(v) for k, v in kwargs.items()}

    if with_name:
        return base_call((name, args, kwargs))
    else:
        return base_call((args, kwargs), two=True)


class AlchemyMagicMock(mock.MagicMock):
    """Compares SQLAlchemy expressions for simple asserts.

    MagicMock for SQLAlchemy which can compare alchemys expressions in assertions.

    For example::

        >>> from sqlalchemy import or_
        >>> from sqlalchemy.sql.expression import column
        >>> c = column('column')
        >>> s = AlchemyMagicMock()

        >>> _ = s.filter(or_(c == 5, c == 10))

        >>> _ = s.filter.assert_called_once_with(or_(c == 5, c == 10))
        >>> _ = s.filter.assert_any_call(or_(c == 5, c == 10))
        >>> _ = s.filter.assert_has_calls([mock.call(or_(c == 5, c == 10))])

        >>> s.reset_mock()
        >>> _ = s.filter(c == 5)
        >>> _ = s.filter.assert_called_once_with(c == 10)
        Traceback (most recent call last):
        ...
        AssertionError: expected call not found.
        Expected: filter(BinaryExpression(sql='"column" = :column_1', \
        params={'column_1': 10}))
        Actual: filter(BinaryExpression(sql='"column" = :column_1', \
        params={'column_1': 5}))
    """

    @overload
    def __init__(  # noqa: E704
        self,
        spec: Optional[Any] = ...,
        side_effect: Optional[Any] = ...,
        return_value: Any = ...,
        wraps: Optional[Any] = ...,
        name: Optional[Any] = ...,
        spec_set: Optional[Any] = ...,
        parent: Optional[Any] = ...,
        _spec_state: Optional[Any] = ...,
        _new_name: Any = ...,
        _new_parent: Optional[Any] = ...,
        **kwargs: Any,
    ) -> None: ...  # noqa: E704  # pragma: no cover

    def __init__(self, *args, **kwargs) -> None:
        """Creates AlchemyMagicMock that can be used as limited SQLAlchemy session."""
        kwargs.setdefault("__name__", "Session")
        super(AlchemyMagicMock, self).__init__(*args, **kwargs)

    def _format_mock_call_signature(self, args: Any, kwargs: Any) -> str:
        """Formats the mock call into a string."""
        name = self._mock_name or "mock"
        args, kwargs = sqlalchemy_call(mock.call(*args, **kwargs))
        return mock._format_call_signature(name, args, kwargs)

    def __await__(self) -> Generator[Any, None, "AlchemyMagicMock"]:
        """Allow the mock to be awaited in async SQLAlchemy code."""
        yield
        return self

    def assert_called_with(self, *args: Any, **kwargs: Any) -> None:
        """Assert for a specific call to have happened."""
        args, kwargs = sqlalchemy_call(mock.call(*args, **kwargs))
        return super(AlchemyMagicMock, self).assert_called_with(*args, **kwargs)

    def assert_any_call(self, *args: Any, **kwargs: Any) -> None:
        """Assert for a specific call to have happened."""
        args, kwargs = sqlalchemy_call(mock.call(*args, **kwargs))
        with setattr_tmp(
            self,
            "call_args_list",
            [sqlalchemy_call(i) for i in self.call_args_list],
        ):
            return super(AlchemyMagicMock, self).assert_any_call(*args, **kwargs)

    def assert_has_calls(self, calls: List[Call], any_order: bool = False) -> None:
        """Assert for a list of calls to have happened."""
        calls = [sqlalchemy_call(i) for i in calls]
        with setattr_tmp(
            self,
            "mock_calls",
            type(self.mock_calls)([sqlalchemy_call(i) for i in self.mock_calls]),
        ):
            return super(AlchemyMagicMock, self).assert_has_calls(calls, any_order)


class UnifiedAlchemyMagicMock(AlchemyMagicMock):
    """A MagicMock that combines SQLALchemy to mock a session.

    MagicMock which unifies common SQLALchemy session functions for easier assertions.

    Attributes:
        boundary: A dict of SQLAlchemy functions or statements that get
            or retreive data from calls. This dictionary has values
            that are the callable functions to process the function calls.
        unify: A dict of SQLAlchemy functions or statements that are to
            unifying expressions together. This dictionary has values
            that are the callable functions to process the function calls. Note
            that across query calls data and, as such, these calls are not unified.
            Check out the examples for this class for more detail about this
            limitation.
        mutate: A set of operations that mutate data. The currently supported
            operations include ``.delete()``, ``.add()``, and ``.add_all()``.
            More operations are planned and this is a future area of work.

    For example::

        >>> from sqlalchemy.sql.expression import column
        >>> c = column('column')

        >>> s = UnifiedAlchemyMagicMock()
        >>> s.query(None).filter(c == 'one').filter(c == 'two').all()
        []
        >>> s.query(None).filter(c == 'three').filter(c == 'four').all()
        []
        >>> s.filter.call_count
        2
        >>> s.filter.assert_any_call(c == 'one', c == 'two')
        >>> s.filter.assert_any_call(c == 'three', c == 'four')

    In addition, mock data be specified to stub real DB interactions.
    Result-sets are specified per filtering criteria so that unique data
    can be returned depending on query/filter/options criteria.
    Data is given as a list of ``(criteria, result)`` tuples where ``criteria``
    is a list of calls.
    Reason for passing data as a list vs a dict is that calls and SQLAlchemy
    expressions are not hashable hence cannot be dict keys.

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

        >>> s = UnifiedAlchemyMagicMock(data=[
        ...     (
        ...         [mock.call.query('foo'),
        ...          mock.call.filter(c == 'one', c == 'two')],
        ...         [SomeClass(pk1=1, pk2=1), SomeClass(pk1=2, pk2=2)]
        ...     ),
        ...     (
        ...         [mock.call.query('foo'),
        ...          mock.call.filter(c == 'one', c == 'two'),
        ...          mock.call.order_by(c)],
        ...         [SomeClass(pk1=2, pk2=2), SomeClass(pk1=1, pk2=1)]
        ...     ),
        ...     (
        ...         [mock.call.filter(c == 'three')],
        ...         [SomeClass(pk1=3, pk2=3)]
        ...     ),
        ... ])

        # .all()
        >>> s.query('foo').filter(c == 'one').filter(c == 'two').all()
        [1, 2]
        >>> s.query('bar').filter(c == 'one').filter(c == 'two').all()
        []
        >>> s.query('foo').filter(c == 'one').filter(c == 'two').order_by(c).all()
        [2, 1]
        >>> s.query('foo').filter(c == 'one').filter(c == 'three').order_by(c).all()
        []
        >>> s.query('foo').filter(c == 'three').all()
        [3]
        >>> s.query(None).filter(c == 'four').all()
        []

        # .iter()
        >>> list(s.query('foo').filter(c == 'two').filter(c == 'one'))
        [1, 2]

        # .count()
        >>> s.query('foo').filter(c == 'two').filter(c == 'one').count()
        2

        # .first()
        >>> s.query('foo').filter(c == 'one').filter(c == 'two').first()
        1
        >>> s.query('bar').filter(c == 'one').filter(c == 'two').first()

        # .one() and scalar
        >>> s.query('foo').filter(c == 'three').one()
        3
        >>> s.query('foo').filter(c == 'three').scalar()
        3
        >>> s.query('bar').filter(c == 'one').filter(c == 'two').one_or_none()

        # .get()
        >>> s.query('foo').get((1, 1))
        1
        >>> s.query('foo').get((4, 4))
        >>> s.query('foo').filter(c == 'two').filter(c == 'one').get((1, 1))
        1
        >>> s.query('foo').filter(c == 'three').get((1, 1))
        1
        >>> s.query('foo').filter(c == 'three').get((4, 4))

        # dynamic session
        >>> class Model(Base):
        ...     __tablename__ = 'model_table'
        ...     pk1 = Column(Integer, primary_key=True)
        ...     name = Column(String)
        ...     def __repr__(self):
        ...         return str(self.pk1)
        >>> s = UnifiedAlchemyMagicMock()
        >>> s.add(SomeClass(pk1=1, pk2=1))
        >>> s.add_all([SomeClass(pk1=2, pk2=2)])
        >>> s.add_all([SomeClass(pk1=4, pk2=3)])
        >>> s.add_all([Model(pk1=4, name='some_name')])
        >>> s.query(SomeClass).all()
        [1, 2, 4]
        >>> s.query(SomeClass).get((1, 1))
        1
        >>> s.query(SomeClass).get((2, 2))
        2
        >>> s.query(SomeClass).get((3, 3))
        >>> s.query(SomeClass).filter(c == 'one').all()
        [1, 2, 4]
        >>> s.query(SomeClass).get((4, 3))
        4
        >>> s.query(SomeClass).get({"pk2": 3, "pk1": 4})
        4
        >>> s.query(Model).get(4)
        4

        # .delete()
        >>> s = UnifiedAlchemyMagicMock(data=[
        ...     (
        ...         [mock.call.query('foo'),
        ...          mock.call.filter(c == 'one', c == 'two')],
        ...         [SomeClass(pk1=1, pk2=1), SomeClass(pk1=2, pk2=2)]
        ...     ),
        ...     (
        ...         [mock.call.query('foo'),
        ...          mock.call.filter(c == 'one', c == 'two'),
        ...          mock.call.order_by(c)],
        ...         [SomeClass(pk1=2, pk2=2), SomeClass(pk1=1, pk2=1)]
        ...     ),
        ...     (
        ...         [mock.call.filter(c == 'three')],
        ...         [SomeClass(pk1=3, pk2=3)]
        ...     ),
        ...     (
        ...         [mock.call.query('foo'),
        ...          mock.call.filter(
        ...             c == 'one',
        ...             c == 'two',
        ...             c == 'three',
        ...         )],
        ...         [
        ...             SomeClass(pk1=1, pk2=1),
        ...             SomeClass(pk1=2, pk2=2),
        ...             SomeClass(pk1=3, pk2=3),
        ...         ]
        ...     ),
        ... ])

        >>> s.query('foo').filter(c == 'three').all()
        [3]
        >>> s.query('foo').all()
        []
        >>> s.query('foo').filter(c == 'three').delete()
        1
        >>> s.query('foo').filter(c == 'three').all()
        []
        >>> s.query('foo').filter(c == 'one').filter(c == 'two').all()
        [1, 2]
        >>> a = s.query('foo').filter(c == 'one').filter(c == 'two')
        >>> a.filter(c == 'three').all()
        [1, 2, 3]
        >>> s = UnifiedAlchemyMagicMock()
        >>> s.add(SomeClass(pk1=1, pk2=1))
        >>> s.add_all([SomeClass(pk1=2, pk2=2)])
        >>> s.query(SomeClass).all()
        [1, 2]
        >>> s.query(SomeClass).delete()
        2
        >>> s.query(SomeClass).all()
        []
        >>> s = UnifiedAlchemyMagicMock()
        >>> s.add_all([SomeClass(pk1=2, pk2=2)])
        >>> s.query(SomeClass).delete()
        1
        >>> s.query(SomeClass).delete()
        0
        >>> s.query(SomeClass).scalar()
        None

        Keyword arguments to ``delete`` such as ``synchronize_session`` are
        accepted but have no impact on mocked data::

        >>> s = UnifiedAlchemyMagicMock()
        >>> s.add_all([SomeClass(pk1=1, pk2=1), SomeClass(pk1=2, pk2=2)])
        >>> s.query(SomeClass).delete(synchronize_session=False)
        2
        >>> s.query(SomeClass).all()
        []

        Deleting a model instance directly with ``s.delete(instance)`` is not
        supported; delete through a query instead.

        SQLAlchemy 2.0 identity lookups work with dynamically added data::

        >>> s = UnifiedAlchemyMagicMock()
        >>> s.add(Model(pk1=1, name='some_name'))
        >>> s.get(Model, 1)
        1

        Explicitly configured mock return values take precedence over mocked
        data, just like regular mocks::

        >>> s = UnifiedAlchemyMagicMock()
        >>> s.query.return_value.filter.return_value.first.return_value = 112
        >>> s.query(SomeClass).filter(SomeClass.pk1 == 1).first()
        112

        Results returned by ``execute`` and ``scalars`` are awaitable so they
        can be used in async test cases. See the user guide for an example.

    Also note that only within same query functions are unified.
    After ``.all()`` is called or query is iterated over, future queries
    are not unified.
    """

    boundary: Dict[str, Callable] = {
        "all": lambda x: x,
        "__iter__": lambda x: iter(x),
        "__len__": lambda x: len(x),
        "count": lambda x: len(x),
        "first": lambda x: next(iter(x), None),
        "one": lambda x: (
            x[0]
            if len(x) == 1
            else (
                raiser(MultipleResultsFound, "Multiple rows were found for one()")
                if x
                else raiser(NoResultFound, "No row was found for one()")
            )
        ),
        "one_or_none": lambda x: (
            x[0]
            if len(x) == 1
            else (
                raiser(
                    MultipleResultsFound,
                    "Multiple rows were found for one_or_none()",
                )
                if x
                else None
            )
        ),
        "get": lambda x, idmap: get_item_attr(build_identity_map(x), idmap),
        "scalar": lambda x: get_scalar(x),
        "scalars": lambda x: UnifiedAlchemyScalarResult(x),
        "scalar_one": lambda x: (
            get_scalar(x)
            if x
            else raiser(NoResultFound, "No row was found for scalar_one()")
        ),
        "scalar_one_or_none": lambda x: get_scalar(x),
        "update": lambda x, *args, **kwargs: None,
        "close": lambda x: None,
    }
    unify: Dict[str, Optional[UnorderedCall]] = {
        "add_columns": None,
        "distinct": None,
        "filter": UnorderedCall,
        "filter_by": UnorderedCall,
        "from_statement": None,
        "group_by": None,
        "having": None,
        "join": None,
        "offset": None,
        "options": None,
        "order_by": None,
        "limit": None,
        "query": None,
        "select_from": None,
        "where": None,
        "with_for_update": None,
    }

    mutate: Set[str] = {"add", "add_all", "delete"}

    _mock_default: Any = []
    _mock_data: Optional[Any] = None

    scalar_methods: Set[str] = {
        "scalar",
        "scalars",
        "scalar_one",
        "scalar_one_or_none",
    }

    @overload
    def __init__(  # noqa: E704
        self,
        spec: Optional[Any] = ...,
        side_effect: Optional[Any] = ...,
        return_value: Any = ...,
        wraps: Optional[Any] = ...,
        name: Optional[Any] = ...,
        spec_set: Optional[Any] = ...,
        parent: Optional[Any] = ...,
        _spec_state: Optional[Any] = ...,
        _new_name: Any = ...,
        _new_parent: Optional[Any] = ...,
        **kwargs: Any,
    ) -> None: ...  # noqa: E704  # pragma: no cover

    def __init__(self, *args, **kwargs) -> None:
        """Creates an UnifiedAlchemyMagicMock to mock a SQLAlchemy session."""
        kwargs["_mock_default"] = kwargs.pop("default", [])
        kwargs["_mock_data"] = kwargs.pop("data", None)
        kwargs.update(
            {
                k: AlchemyMagicMock(
                    return_value=_DEFAULT_RETURN_VALUE,
                    side_effect=partial(self._get_data, _mock_name=k),
                )
                for k in self.boundary
            }
        )

        kwargs.update(
            {
                k: AlchemyMagicMock(
                    return_value=self,
                    side_effect=partial(self._unify, _mock_name=k),
                )
                for k in self.unify
            }
        )

        kwargs.update(
            {
                k: AlchemyMagicMock(
                    return_value=None,
                    side_effect=partial(self._mutate_data, _mock_name=k),
                )
                for k in self.mutate
            }
        )

        kwargs["execute"] = AlchemyMagicMock(
            return_value=_DEFAULT_RETURN_VALUE,
            side_effect=partial(self._execute, _mock_name="execute"),
        )

        super(UnifiedAlchemyMagicMock, self).__init__(*args, **kwargs)

    def _get_previous_calls(self, calls: Sequence[Call]) -> Iterator:
        """Gets the previous calls on the same line."""
        # the calls that end lines
        call_enders = list(self.boundary.keys()) + ["delete", "execute"]
        return iter(takewhile(lambda i: i[0] not in call_enders, reversed(calls)))

    def _get_previous_call(self, name: str, calls: Sequence[Call]) -> Optional[Call]:
        """Gets the previous call right before the current call."""
        # get all previous session calls within same session query
        previous_calls = self._get_previous_calls(calls)

        # skip last call
        next(previous_calls)

        return next(iter(filter(lambda i: i[0] == name, previous_calls)), None)

    @overload
    def _unify(  # noqa: E704
        self,
        value: Any = ...,
        name: Optional[Any] = ...,
        parent: Optional[Any] = ...,
        two: bool = ...,
        from_kall: bool = ...,
    ) -> None: ...  # noqa: E704  # pragma: no cover

    def _unify(self, *args, **kwargs) -> Any:
        """Unify the SQLAlchemy expressions."""
        _mock_name = kwargs.pop("_mock_name")
        submock = getattr(self, _mock_name)

        previous_method_call = self._get_previous_call(_mock_name, self.method_calls)
        previous_mock_call = self._get_previous_call(_mock_name, self.mock_calls)

        if previous_mock_call is None:
            return submock.return_value

        # remove immediate call from both filter mock as well as the parent mock object
        # as it already registered in self.__call__ before this side-effect is call
        submock.call_count -= 1
        submock.call_args_list.pop()
        submock.mock_calls.pop()
        self.method_calls.pop()
        self.mock_calls.pop()

        # remove previous call since we will be inserting new call instead
        submock.call_args_list.pop()
        submock.mock_calls.pop()
        self.method_calls.pop(indexof(previous_method_call, self.method_calls))
        self.mock_calls.pop(indexof(previous_mock_call, self.mock_calls))

        name, pargs, pkwargs = previous_method_call
        args = pargs + args
        kwargs = copy_and_update(pkwargs, kwargs)

        submock.call_args = Call((args, kwargs), two=True)
        submock.call_args_list.append(Call((args, kwargs), two=True))
        submock.mock_calls.append(Call(("", args, kwargs)))

        self.method_calls.append(Call((name, args, kwargs)))
        self.mock_calls.append(Call((name, args, kwargs)))

        return submock.return_value

    def _convert_calls(self, calls: Iterable[Call]) -> List[Call]:
        """Convert mock calls into SQLAlchemy-aware calls.

        Args:
            calls: A sequence of calls to convert.

        Returns:
            A list of converted calls.
        """
        return [
            sqlalchemy_call(i, with_name=True, base_call=self.unify.get(i[0]) or Call)
            for i in calls
        ]

    def _find_data(self, calls: Sequence[Call]) -> Optional[Sequence[Any]]:
        """Find the stubbed data matching the given calls.

        Args:
            calls: The calls that must contain every call of a data criterion.

        Returns:
            The matching result or ``None`` if no data criterion matches.
        """
        if self._mock_data is None:
            return None

        sorted_mock_data = sorted(
            self._mock_data, key=lambda x: len(x[0]), reverse=True
        )
        for data_calls, result in sorted_mock_data:
            if all(c in calls for c in self._convert_calls(data_calls)):
                return result
        return None

    def _adapt_query_calls(
        self, calls: Sequence[Call]
    ) -> Tuple[List[Call], List[List[Any]]]:
        """Adapt column-based query calls to their originating models.

        Querying a column such as ``Model.name`` should return the same data
        as querying ``Model`` but projected onto the selected columns.

        Args:
            calls: The previous calls to adapt.

        Returns:
            The adapted calls and the projection list for each adapted query.
        """
        adapted: List[Call] = []
        projections: List[List[Any]] = []

        for call in calls:
            if call[0] == "query":
                query_args = list(call[1])
                attributes = [
                    arg.expr
                    for arg in query_args
                    if isinstance(arg.expr, InstrumentedAttribute)
                ]
                other_args = [
                    arg
                    for arg in query_args
                    if not isinstance(arg.expr, InstrumentedAttribute)
                ]
                if attributes and not other_args:
                    base_classes = []
                    for attribute in attributes:
                        if attribute.class_ not in base_classes:
                            base_classes.append(attribute.class_)
                    adapted.append(
                        Call(
                            (
                                "query",
                                tuple(ExpressionMatcher(c) for c in base_classes),
                                call[2],
                            )
                        )
                    )
                    projections.append(attributes)
                    continue
            adapted.append(call)

        return adapted, projections

    @staticmethod
    def _project_rows(
        rows: Sequence[Any], projection: Sequence[InstrumentedAttribute]
    ) -> List[Any]:
        """Project rows onto the given model attributes.

        Args:
            rows: The rows to project.
            projection: The attributes to project each row onto.

        Returns:
            A list of projected tuples.
        """
        projected = []
        for row in rows:
            try:
                projected.append(
                    tuple(getattr(row, attribute.key) for attribute in projection)
                )
            except AttributeError:
                projected.append(row)
        return projected

    def _get_data(self, *args: Any, **kwargs: Any) -> Any:
        """Get the data for the SQLAlchemy expression."""
        _mock_name = kwargs.pop("_mock_name")

        configured = getattr(self, _mock_name).return_value
        if configured is not _DEFAULT_RETURN_VALUE:
            return configured

        statement = None
        if (
            _mock_name in self.scalar_methods
            and args
            and isinstance(args[0], ClauseElement)
        ):
            statement = args[0]
            args = args[1:]

        if statement is not None:
            return self._get_statement_data(_mock_name, statement, args, kwargs)

        if _mock_name == "get" and args and isinstance(args[0], type):
            rows = self._find_data(
                [sqlalchemy_call(mock.call.query(args[0]), with_name=True)]
            )
            if rows is None:
                rows = self._mock_default
            return self.boundary["get"](rows, *args[1:])

        if self._mock_data is None:
            return self.boundary[_mock_name](self._mock_default, *args, **kwargs)

        history = [call for call in self.mock_calls[:-1] if call[0] != "__len__"]
        previous_calls = self._convert_calls(self._get_previous_calls(history))

        if _mock_name == "get":
            return self._get_data_for_get(previous_calls, args, kwargs)

        result, projection = self._find_query_result(previous_calls)
        if result is None:
            return self.boundary[_mock_name](self._mock_default, *args, **kwargs)
        if projection:
            result = self._project_rows(result, projection)
        return self.boundary[_mock_name](result, *args, **kwargs)

    def _get_statement_data(
        self,
        _mock_name: str,
        statement: Any,
        args: Sequence[Any],
        kwargs: Dict[str, Any],
    ) -> Any:
        """Get the data for a directly executed statement.

        Args:
            _mock_name: The name of the mocked boundary method.
            statement: The statement passed to the method.
            args: The additional positional arguments.
            kwargs: The additional keyword arguments.

        Returns:
            The boundary method's result.
        """
        rows = self._resolve_statement(
            statement,
            args,
            kwargs,
            extra_calls=[
                sqlalchemy_call(
                    getattr(mock.call, _mock_name)(statement, *args),
                    with_name=True,
                )
            ],
        )
        if rows is None:
            rows = self._mock_default
        return self.boundary[_mock_name](rows, *args, **kwargs)

    def _get_data_for_get(
        self,
        previous_calls: Sequence[Call],
        args: Sequence[Any],
        kwargs: Dict[str, Any],
    ) -> Any:
        """Get the data for a ``get`` call.

        Args:
            previous_calls: The previous calls in the query chain.
            args: The additional positional arguments.
            kwargs: The additional keyword arguments.

        Returns:
            The boundary method's result.
        """
        query_calls = [c for c in previous_calls if c[0] in ["query", "execute"]]
        results = []
        for data_calls, result in sorted(
            self._mock_data or [], key=lambda x: len(x[0]), reverse=True
        ):
            converted = self._convert_calls(data_calls)
            if query_calls and any(c in converted for c in query_calls):
                results.extend(result)
        return self.boundary["get"](results, *args, **kwargs)

    def _find_query_result(
        self, previous_calls: Sequence[Call]
    ) -> Tuple[Optional[Sequence[Any]], Optional[List[Any]]]:
        """Find the result and projection for the current query chain.

        Args:
            previous_calls: The previous calls in the query chain.

        Returns:
            The matching result and the projection to apply, if any.
        """
        result = self._find_data(previous_calls)
        projection: Optional[List[Any]] = None
        if result is None:
            adapted_calls, projections = self._adapt_query_calls(previous_calls)
            result = self._find_data(adapted_calls)
            if result is not None and projections:
                projection = projections[0]
        return result, projection

    def _resolve_statement(
        self,
        statement: Any,
        args: Sequence[Any],
        kwargs: Optional[Dict[str, Any]] = None,
        extra_calls: Optional[Sequence[Any]] = None,
    ) -> Optional[Sequence[Any]]:
        """Resolve the mocked rows for a directly executed statement.

        Args:
            statement: The statement passed to ``execute`` or a scalar method.
            args: The additional positional arguments for the statement.
            kwargs: The additional keyword arguments for the statement.
            extra_calls: Additional calls that can satisfy a data criterion.

        Returns:
            The matching rows or ``None`` if no data criterion matched.
        """
        kwargs = kwargs or {}
        calls = self._convert_calls(self._get_previous_calls(self.mock_calls[:-1]))
        calls.append(
            sqlalchemy_call(
                mock.call.execute(statement, *args, **kwargs), with_name=True
            )
        )
        if extra_calls:
            calls.extend(extra_calls)

        rows = self._find_data(calls)
        if rows is None:
            filtered = self._filter_statement_rows(statement, calls)
            if filtered is not None:
                rows = filtered
        return rows

    def _filter_statement_rows(
        self, statement: Any, calls: Sequence[Call]
    ) -> Optional[Sequence[Any]]:
        """Filter the base rows of a SELECT statement by its WHERE clause.

        Args:
            statement: The SELECT statement being executed.
            calls: The calls used to find the base data criterion.

        Returns:
            The filtered rows or ``None`` if no base rows could be found.
        """
        whereclause = getattr(statement, "whereclause", None)
        descriptions = getattr(statement, "column_descriptions", None)
        if not descriptions:
            return None
        entity = descriptions[0].get("entity")
        if entity is None:
            return None

        base_call = sqlalchemy_call(mock.call.execute(select(entity)), with_name=True)
        rows = self._find_data(list(calls) + [base_call])
        if rows is None:
            return None

        if whereclause is not None:
            rows = [row for row in rows if match_row_to_clause(row, whereclause)]

        expressions = [description.get("expr") for description in descriptions]
        if expressions and all(
            isinstance(expression, InstrumentedAttribute) for expression in expressions
        ):
            return self._project_rows(rows, expressions)
        return rows

    def _append_to_data(self, criteria_call: Any, item: Any) -> None:
        """Append an item to the data criterion matching the given call.

        Args:
            criteria_call: The call identifying the data criterion.
            item: The item to append.
        """
        criterion = self._convert_calls([criteria_call])
        _mock_data = self._mock_data = self._mock_data or []
        for calls, result in _mock_data:
            if self._convert_calls(calls) == criterion:
                result.append(item)
                return
        _mock_data.append(([criteria_call], [item]))

    @staticmethod
    def _get_model_type(statement: Any) -> Optional[Any]:
        """Get the ORM model type for a DML statement.

        Args:
            statement: The INSERT, UPDATE, or DELETE statement.

        Returns:
            The model type or ``None`` if the statement is not ORM-mapped.
        """
        entity_description = getattr(statement, "entity_description", None) or {}
        return entity_description.get("type")

    @staticmethod
    def _unwrap_dml_value(value: Any) -> Any:
        """Unwrap a bind parameter into its Python value.

        Args:
            value: A column binding or plain value.

        Returns:
            The plain Python value.
        """
        return getattr(value, "value", value)

    @staticmethod
    def _get_attribute_name(model_type: Optional[Any], column: Any) -> Any:
        """Get the model attribute name for a DML column.

        Args:
            model_type: The ORM model type, if any.
            column: A column or a string key.

        Returns:
            The model attribute name.
        """
        if isinstance(column, str):
            return column
        mapper = getattr(model_type, "__mapper__", None)
        if mapper is not None and hasattr(column, "table"):
            try:
                return mapper.get_property_by_column(column).key
            except UnmappedColumnError:
                pass
        return getattr(column, "key", getattr(column, "name", column))

    @classmethod
    def _row_as_kwargs(
        cls: Any, row: Mapping, model_type: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Convert a DML row mapping into model keyword arguments.

        Args:
            row: A mapping of columns to values.
            model_type: The ORM model type, if any.

        Returns:
            A dictionary mapping attribute names to unwrapped values.
        """
        return {
            cls._get_attribute_name(model_type, key): cls._unwrap_dml_value(value)
            for key, value in row.items()
        }

    def _object_matches_statement(
        self, item: Any, model_type: Optional[Any], table: Optional[Any]
    ) -> bool:
        """Check whether a mocked object belongs to a DML statement.

        Args:
            item: A mocked row.
            model_type: The ORM model type, if any.
            table: The core table, if any.

        Returns:
            Whether the item belongs to the statement.
        """
        if model_type is not None:
            return isinstance(item, model_type)
        if table is not None:
            return getattr(item, "__table__", None) is table
        return isinstance(item, Mapping)

    def _execute_insert(
        self,
        statement: Any,
        extra_args: Sequence[Any],
        kwargs: Dict[str, Any],
    ) -> UnifiedAlchemyResult:
        """Apply an INSERT statement to the mocked data.

        Args:
            statement: The INSERT statement.
            extra_args: The additional positional arguments.
            kwargs: The additional keyword arguments.

        Returns:
            A result with the number of inserted rows.
        """
        model_type = self._get_model_type(statement)
        rows: List[Any] = []

        if extra_args:
            params = extra_args[0]
            rows = list(params) if isinstance(params, (list, tuple)) else [params]
        elif getattr(statement, "_multi_values", None):
            rows = [row for values in statement._multi_values for row in values]
        elif getattr(statement, "_values", None):
            rows = [statement._values]

        instances = []
        for row in rows:
            if model_type is not None and isinstance(row, model_type):
                instance = row
            elif model_type is not None and isinstance(row, Mapping):
                instance = model_type(**self._row_as_kwargs(row, model_type=model_type))
            elif model_type is not None:
                instance = model_type(**dict(row))
            else:
                instance = row
            self._mutate_data(instance, _mock_name="add")
            instances.append(instance)

        return UnifiedAlchemyResult([], statement=statement, rowcount=len(instances))

    def _execute_update(
        self,
        statement: Any,
        extra_args: Sequence[Any],
        kwargs: Dict[str, Any],
    ) -> UnifiedAlchemyResult:
        """Apply an UPDATE statement to the mocked data.

        Args:
            statement: The UPDATE statement.
            extra_args: The additional positional arguments.
            kwargs: The additional keyword arguments.

        Returns:
            A result with the number of updated rows.
        """
        model_type = self._get_model_type(statement)
        table = getattr(statement, "table", None)
        whereclause = getattr(statement, "whereclause", None)
        values = {
            self._get_attribute_name(model_type, column): self._unwrap_dml_value(value)
            for column, value in (getattr(statement, "_values", None) or {}).items()
        }

        updated = set()
        for _calls, result in self._mock_data or []:
            for item in result:
                if id(item) in updated:
                    continue
                if not self._object_matches_statement(item, model_type, table):
                    continue
                if match_row_to_clause(item, whereclause):
                    if isinstance(item, Mapping):
                        item.update(values)
                    else:
                        for name, value in values.items():
                            setattr(item, name, value)
                    updated.add(id(item))

        return UnifiedAlchemyResult([], statement=statement, rowcount=len(updated))

    def _execute_delete(
        self,
        statement: Any,
        extra_args: Sequence[Any],
        kwargs: Dict[str, Any],
    ) -> UnifiedAlchemyResult:
        """Apply a DELETE statement to the mocked data.

        Args:
            statement: The DELETE statement.
            extra_args: The additional positional arguments.
            kwargs: The additional keyword arguments.

        Returns:
            A result with the number of deleted rows.
        """
        model_type = self._get_model_type(statement)
        table = getattr(statement, "table", None)
        whereclause = getattr(statement, "whereclause", None)

        deleted = set()
        for _calls, result in self._mock_data or []:
            remaining = []
            for item in result:
                if id(item) in deleted:
                    continue
                if self._object_matches_statement(
                    item, model_type, table
                ) and match_row_to_clause(item, whereclause):
                    deleted.add(id(item))
                else:
                    remaining.append(item)
            result[:] = remaining

        return UnifiedAlchemyResult([], statement=statement, rowcount=len(deleted))

    def _execute(self, *args: Any, **kwargs: Any) -> UnifiedAlchemyResult:
        """Execute a SQLAlchemy statement against the mocked data.

        Args:
            args: The statement and any additional statement arguments.
            kwargs: The additional keyword arguments for the statement.

        Returns:
            A SQLAlchemy ``Result``-like object.
        """
        kwargs.pop("_mock_name", None)
        configured = self.execute.return_value
        if configured is not _DEFAULT_RETURN_VALUE:
            return configured
        if not args:
            return UnifiedAlchemyResult([])

        statement = args[0]
        extra_args = args[1:]

        if isinstance(statement, Insert):
            return self._execute_insert(statement, extra_args, kwargs)
        if isinstance(statement, Update):
            return self._execute_update(statement, extra_args, kwargs)
        if isinstance(statement, Delete):
            return self._execute_delete(statement, extra_args, kwargs)

        rows = self._resolve_statement(statement, extra_args, kwargs)
        if rows is None:
            rows = self._mock_default
        return UnifiedAlchemyResult(rows, statement=statement)

    def _mutate_data(self, *args: Any, **kwargs: Any) -> Optional[int]:
        """Alter the data for the SQLAlchemy expression."""
        _mock_name = kwargs.get("_mock_name")
        if _mock_name == "add":
            to_add = args[0]
            self._append_to_data(mock.call.query(type(to_add)), to_add)
            try:
                execute_call = mock.call.execute(select(type(to_add)))
            except (ArgumentError, TypeError):
                # Some mocked classes cannot be used as a select target.
                pass
            else:
                self._append_to_data(execute_call, to_add)

        elif _mock_name == "add_all":
            to_add = args[0]
            _kwargs = kwargs.copy()
            _kwargs["_mock_name"] = "add"

            for i in to_add:
                self._mutate_data(i, *args[1:], **_kwargs)
        # delete case
        return self._delete_data(*args, **kwargs)

    def _delete_data(self, *args: Any, **kwargs: Any) -> Optional[int]:
        """Delete the data for the current query chain.

        Args:
            args: Unused positional arguments of the ``delete`` call.
            kwargs: Unused keyword arguments of the ``delete`` call.

        Returns:
            The number of deleted rows.
        """
        _mock_data = self._mock_data = self._mock_data or []
        num_deleted = 0
        previous_calls = self._convert_calls(
            self._get_previous_calls(self.mock_calls[:-1])
        )
        sorted_mock_data = sorted(_mock_data, key=lambda x: len(x[0]), reverse=True)
        temp_mock_data = []
        found_query = False
        deleted = []

        for calls, result in sorted_mock_data:
            converted = self._convert_calls(calls)
            if all(c in previous_calls for c in converted) and not found_query:
                num_deleted = len(result)
                deleted.extend(result)
                temp_mock_data.append((converted, []))
                found_query = True
            else:
                temp_mock_data.append((converted, result))

        if deleted:
            deleted_ids = {id(i) for i in deleted}
            for _calls, result in temp_mock_data:
                if result:
                    result[:] = [i for i in result if id(i) not in deleted_ids]

        self._mock_data = temp_mock_data
        return num_deleted
