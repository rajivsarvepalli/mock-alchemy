===============
Mock SQLAlchemy
===============
.. image:: https://readthedocs.org/projects/mock-alchemy/badge/?version=latest
    :target: https://mock-alchemy.readthedocs.io/en/latest/?badge=latest

.. image:: https://img.shields.io/pypi/v/mock-alchemy.svg
    :target: https://pypi.org/project/mock-alchemy/

.. image:: https://img.shields.io/pypi/pyversions/mock-alchemy.svg
    :target: https://pypi.org/project/mock-alchemy/

.. image:: https://github.com/rajivsarvepalli/mock-alchemy/workflows/Tests/badge.svg
    :target: https://github.com/rajivsarvepalli/mock-alchemy/actions?workflow=Tests

.. image:: https://codecov.io/gh/rajivsarvepalli/mock-alchemy/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/rajivsarvepalli/mock-alchemy

SQLAlchemy mock helpers.

* Free software: MIT license
* GitHub: https://github.com/rajivsarvepalli/mock-alchemy

Documentation
-------------

Full documentation is available at `http://mock-alchemy.rtfd.io/ <http://mock-alchemy.rtfd.io/>`__.
On the documentation, you should be able to select a version of your choice in order to view documentation
of an older version if need be.
This README includes some basic examples, but more detailed examples are included in the documentation, especially in the `user guide <https://mock-alchemy.readthedocs.io/en/latest/user_guide/>`__.
If you are looking for an API reference, it is also available on the `documentation <https://mock-alchemy.readthedocs.io/en/latest/api_reference/mock_alchemy.mocking.html>`__.


Credit
----------

The original library (``alchemy-mock``) was created by Miroslav Shubernetskiy and Serkan Hoscai. This is a forked version due to a lack of updates
in the original library. It appeared that the ``alchemy-mock`` project was no longer supported. Therefore, since I desired to add some basic support
for deleting, I created my own version of the library. Full credit goes to the original creators for starting and building this project. You can find the
original package on `PyPi <https://pypi.org/project/alchemy-mock/>`__ and `Github <https://github.com/miki725/alchemy-mock>`__.

Installing
----------

You can install ``mock-alchemy`` using pip::

    $ pip install mock-alchemy

Why?
----

SQLAlchemy is awesome. Unittests are great.
Accessing DB during tests - not so much.
This library provides easy way to mock SQLAlchemy's session
in unittests while preserving ability to do sane asserts.
Normally SQLAlchemy's expressions cannot be easily compared
as comparison on binary expression produces yet another binary expression::

    >>> type((Model.foo == 5) == (Model.bar == 5))
    <class 'sqlalchemy.sql.elements.BinaryExpression'>

But they can be compared with this library::

    >>> ExpressionMatcher(Model.foo == 5) == (Model.bar == 5)
    False

Using
-----

``ExpressionMatcher`` can be directly used::

    >>> from mock_alchemy.comparison import ExpressionMatcher
    >>> ExpressionMatcher(Model.foo == 5) == (Model.foo == 5)
    True

Alternatively ``AlchemyMagicMock`` can be used to mock out SQLAlchemy session::

    >>> from mock_alchemy.mocking import AlchemyMagicMock
    >>> session = AlchemyMagicMock()
    >>> session.query(Model).filter(Model.foo == 5).all()

    >>> session.query.return_value.filter.assert_called_once_with(Model.foo == 5)

In real world though session can be interacted with multiple times to query some data.
In those cases ``UnifiedAlchemyMagicMock`` can be used which combines various calls for easier assertions::

    >>> from mock_alchemy.mocking import UnifiedAlchemyMagicMock
    >>> session = UnifiedAlchemyMagicMock()

    >>> m = session.query(Model)
    >>> q = m.filter(Model.foo == 5)
    >>> if condition:
    ...     q = q.filter(Model.bar > 10).all()
    >>> data1 = q.all()
    >>> data2 = m.filter(Model.note == 'hello world').all()

    >>> session.filter.assert_has_calls([
    ...     mock.call(Model.foo == 5, Model.bar > 10),
    ...     mock.call(Model.note == 'hello world'),
    ... ])

Also real-data can be stubbed by criteria::

    >>> from mock_alchemy.mocking import UnifiedAlchemyMagicMock
    >>> session = UnifiedAlchemyMagicMock(data=[
    ...     (
    ...         [mock.call.query(Model),
    ...          mock.call.filter(Model.foo == 5, Model.bar > 10)],
    ...         [Model(foo=5, bar=11)]
    ...     ),
    ...     (
    ...         [mock.call.query(Model),
    ...          mock.call.filter(Model.note == 'hello world')],
    ...         [Model(note='hello world')]
    ...     ),
    ...     (
    ...         [mock.call.query(AnotherModel),
    ...          mock.call.filter(Model.foo == 5, Model.bar > 10)],
    ...         [AnotherModel(foo=5, bar=17)]
    ...     ),
    ... ])
    >>> session.query(Model).filter(Model.foo == 5).filter(Model.bar > 10).all()
    [Model(foo=5, bar=11)]
    >>> session.query(Model).filter(Model.note == 'hello world').all()
    [Model(note='hello world')]
    >>> session.query(AnotherModel).filter(Model.foo == 5).filter(Model.bar > 10).all()
    [AnotherModel(foo=5, bar=17)]
    >>> session.query(AnotherModel).filter(Model.note == 'hello world').all()
    []

The ``UnifiedAlchemyMagicMock`` can partially fake session mutations
such as ``session.add(instance)``. For example::

    >>> session = UnifiedAlchemyMagicMock()
    >>> session.add(Model(pk=1, foo='bar'))
    >>> session.add(Model(pk=2, foo='baz'))
    >>> session.query(Model).all()
    [Model(foo='bar'), Model(foo='baz')]
    >>> session.query(Model).get(1)
    Model(foo='bar')
    >>> session.query(Model).get(2)
    Model(foo='baz')

Note that its partially correct since if added models are filtered on,
session is unable to actually apply any filters so it returns everything::

   >>> session.query(Model).filter(Model.foo == 'bar').all()
   [Model(foo='bar'), Model(foo='baz')]

Finally, ``UnifiedAlchemyMagicMock`` can partially fake deleting. Anything that can be
accessed with ``all`` can also be deleted. For example::

    >>> s = UnifiedAlchemyMagicMock()
    >>> s.add(SomeClass(pk1=1, pk2=1))
    >>> s.add_all([SomeClass(pk1=2, pk2=2)])
    >>> s.query(SomeClass).all()
    [1, 2]
    >>> s.query(SomeClass).delete()
    2
    >>> s.query(SomeClass).all()
    []

Note the limitation for dynamic sessions remains the same. Additionally, the delete will not be propagated across
queries (only unified in the exact same query). As in if there are multiple queries in which the 'same'
object is present, this library considers them separate objects. For example::

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
    ...          mock.call.filter(c == 'one', c == 'two', c == 'three')],
    ...         [SomeClass(pk1=1, pk2=1), SomeClass(pk1=2, pk2=2), SomeClass(pk1=3, pk2=3)]
    ...     ),
    ... ])

    >>> s.query('foo').filter(c == 'three').delete()
    1
    >>> s.query('foo').filter(c == 'three').all()
    []
    >>> s.query('foo').filter(c == 'one').filter(c == 'two').filter(c == 'three').all()
    [1, 2, 3]

The item referred to by :code:`c == 'three'` is still present in the filtered query despite the individual item being deleted.
