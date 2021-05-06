.. _user_guide:

User Guide
==========

There several major uses for this package and I will try to detail out several examples in this guide.

Installation
--------------

You can install ``mock-alchemy`` using pip::

    $ pip install mock-alchemy

If you want to use this package on Python 2.7 or Python 3.6, then install ``mock-alchemy`` using::

    $ pip install "mock-alchemy>=0.1.0,<0.2.0"

Pip should auto-detect the correct version but this ensures the correct version is downloaded for your needs.

Quick Examples
--------------

ExpressionMatcher
^^^^^^^^^^^^^^^^^

``ExpressionMatcher`` can be directly used::

    >>> from mock_alchemy.comparison import ExpressionMatcher
    >>> ExpressionMatcher(Model.foo == 5) == (Model.foo == 5)
    True

AlchemyMagicMock
^^^^^^^^^^^^^^^^^

Alternatively ``AlchemyMagicMock`` can be used to mock out SQLAlchemy session::

    >>> from mock_alchemy.mocking import AlchemyMagicMock
    >>> session = AlchemyMagicMock()
    >>> session.query(Model).filter(Model.foo == 5).all()

    >>> session.query.return_value.filter.assert_called_once_with(Model.foo == 5)

UnifiedAlchemyMagicMock
^^^^^^^^^^^^^^^^^^^^^^^

Asserts
~~~~~~~

In the real-world, a SQLAlchemy session can be interacted with multiple times to query some data.
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

Stub Data
~~~~~~~~~

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

Sessions
~~~~~~~~

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

Filter Limitation
+++++++++++++++++

Note that its partially correct since if added models are filtered on,
session is unable to actually apply any filters so it returns everything::

   >>> session.query(Model).filter(Model.foo == 'bar').all()
   [Model(foo='bar'), Model(foo='baz')]

Deleting in Sessions
++++++++++++++++++++

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

Dynamic Session Limitation
++++++++++++++++++++++++++

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

More examples are available inside the documentation for :class:`mock_alchemy.mocking.UnifiedAlchemyMagicMock`, or generally
inside :mod:`mock_alchemy.mocking`.

Real-World Examples
-------------------

In these real-world examples, I will explain hypothetical or real scenarios in which I have used this library to mock SQLAlchemy in
order to efficiently test my code. I will also explain several alternatives to this library to use for testing, and why specifically this
library may be useful in the specific scenario.

.. _data_stubbing:

Data Stubbing
^^^^^^^^^^^^^

My main use case for this library came into play when using a codebase that had entry points (runnable scripts) that required session objects.
These scripts use the session objects to integrate a combination of SQL tables to perform data analysis or other techniques in some manner.
While each individual data analysis techniques were tested separately through unit tests, I wanted to test the integration of these components.
One solution is to use transactions so that your database is never modified. However, this method requires access to the real SQL server and also
is unlikely to provide stable and consistent data. Tests should be rerunnable with the same output every time and consistent. Another solution would be to
set up a test database. However, this is very time consuming both in set up and tests take quite long to run. Additionally, some local machines
struggle to set up a SQL server locally, so it is not the best solution. Finally, I ran into the original version of this library created by
`Miroslav Shubernetskiy <https://github.com/miki725>`__. I found this library to combine the abilities I needed in order to test scripts that required
a session object as a parameter. By creating a mocked-up session, I was able to effectively test my functions that combined many different SQL tables
together for data analysis. Since there were some additional features I desired to add, I created my own version of the library to use in my own projects.

Now, let us take a look at some example code for this scenario.
First, let us consider the function we want to test. Please note the code below was created to support the scenario above and therefore is not runnable,
but merely exemplary to what this library can perform.

.. code-block:: python

    from sqlalchemy import Column, Integer, String
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()

    # assume similar classes for Data2 and Data3
    class Data1(Base):
        __tablename__ = 'some_table'
        pk1 = Column(Integer, primary_key=True)
        data_val1 = Column(Integer)
        data_val2 = Column(Integer)
        data_val3 = Column(Integer)
        def __init__(self, pk1, val1, val2, val3):
            self.pk1 = pk1
            self.data_val1 = val1
            self.data_val2 = val2
            self.data_val3 = val3

    class CombinedAnalysis(Base):
        __tablename__ = 'some_table'
        pk1 = Column(Integer, primary_key=True)
        analysis_val1 = Column(Integer)
        analysis_val2 = Column(Integer)
        analysis_val3 = Column(Integer)
        def __init__(self, pk1, val1, val2, val3):
            self.pk1 = pk1
            self.analysis_val1 = val1
            self.analysis_val2 = val2
            self.analysis_val3 = val3

        def __eq__(self, other):
            if not isinstance(other, CombinedAnalysis):
                return NotImplemented
            return (
                self.analysis_val1 == other.analysis_val1
                and self.analysis_val2 == other.analysis_val2
                and self.analysis_val3 == other.analysis_val3
            )

    def complex_data_analysis(cfg, session):
        # collects some data upto some point
        dataset1 = session.query(Data1).filter(Data1.utc_time < cfg["final_time"])
        dataset2 = session.query(Data2).filter(Data2.utc_time < cfg["final_time"])
        dataset3 = session.query(Data3).filter(Data3.utc_time < cfg["final_time"])
        # performs some analysis
        analysis12 = analysis(dataset1, dataset2)
        analysis13 = analysis(dataset1, dataset3)
        analysis23 = analysis(dataset2, dataset3)
        # combine the data analysis (returns object CombinedAnalysis)
        combined_analysis = intergrate_analysis(analysis12, analysis13, analysis23)
        # assume the combined_analysis are stored in some SQL table
        self.session.add_all(combined_analysis)
        self.session.commit()

When using the :mod:`mock-alchemy` package, the test function can now test this ``complex_data_analysis`` function despite it containing multiple calls to SQL and combining those calls.
Here is an example of how this might look. Assume the file detailed above is called ``data_analysis``.

.. code-block:: python

    import datetime
    import mock

    import pytest
    from mock_alchemy.mocking import UnifiedAlchemyMagicMock

    from data_analysis import complex_data_analysis, Data1, Data2, Data3, CombinedAnalysis

    def test_data_analysis():
        stop_time = datetime.datetime.utcnow()
        cfg = {
            "final_time": stop_time
        }
        data1_values = [
            Data1(1, some, data, values),
            Data1(2, some, data, values),
            Data1(3, some, data, values),
        ]
        data2_values = [
            Data2(1, some, data, values),
            Data2(2, some, data, values),
            Data2(3, some, data, values),
        ]
        data3_values = [
            Data3(1, some, data, values),
            Data3(2, some, data, values),
            Data3(3, some, data, values),
        ]
        session = UnifiedAlchemyMagicMock(data=[
            (
                [mock.call.query(Data1),
                 mock.call.filter(Data1.utc_time < stop_time)],
                data1_values
            ),
            (
                [mock.call.query(Data2),
                 mock.call.filter(Data2.utc_time < stop_time)],
                data2_values
            ),
            (
                [mock.call.query(Data3),
                 mock.call.filter(Data3.utc_time < stop_time)],
                data3_values
            ),
        ])
        complex_data_analysis(cfg, session)
        expected_anyalsis = [
            CombinedAnalysis(1, some, anyalsis, values),
            CombinedAnalysis(2, some, anyalsis, values),
            CombinedAnalysis(3, some, anyalsis, values),
        ]
        combined_anyalsis = session.query(CombinedAnalysis).all()
        assert sorted(combined_anyalsis, key=lambda x: x.pk1) == sorted(expected_anyalsis, key=lambda x: x.pk1)


Assert Calls
^^^^^^^^^^^^

Consider a scenario where we simply want to test whether certain SQLAlchemy statements have been called.
This will not verify the actual data processing but will enable a degree of testing verification to ensure
that either the correct branches are taken or that other functions call upon the session an appropriate amount
of times. This ability can be combined with ``UnifiedAlchemyMagicMock`` to combine both data checking and the
correct SQLAlchemy calls.

For example, consider the following function we want to test.

.. code-block:: python

    def alchemy_stmts(session):
        q = session.query(Model).filter(Model.foo == 5)
        q = some_func(q)
        q.filter(Model.baz > 11)
        if condition


To test this function, we can use the

.. code-block:: python

    from mock_alchemy.mocking import UnifiedAlchemyMagicMock

    def test_stms():
        session = UnifiedAlchemyMagicMock()
        session.filter.assert_has_calls([
            mock.call(Model.foo == 5, Model.som_attr < 31, Model.baz > 11),
            mock.call(Model.note == 'hello world'),
        ])

With the combination of this example and the :ref:`previous example <data_stubbing>`, we can use ``UnifiedAlchemyMagicMock`` to assert calls
to check branching in code and verify data values using a mock SQLAlchemy session

Getting and Deleting
^^^^^^^^^^^^^^^^^^^^

Let us reuse the :ref:`previous example <data_stubbing>`, but now we can test deleting as well.
We modify the ``complex_data_analysis`` to be:

.. code-block:: python

    def complex_data_analysis(cfg, session):
        # collects some data upto some point
        dataset1 = session.query(Data1).filter(Data1.utc_time < cfg["final_time"])
        dataset2 = session.query(Data2).filter(Data2.utc_time < cfg["final_time"])
        dataset3 = session.query(Data3).filter(Data3.utc_time < cfg["final_time"])
        # performs some analysis
        analysis12 = analysis(dataset1, dataset2)
        analysis13 = analysis(dataset1, dataset3)
        analysis23 = analysis(dataset2, dataset3)
        # combine the data analysis (returns object CombinedAnalysis)
        combined_analysis = intergrate_analysis(analysis12, analysis13, analysis23)
        # assume the combined_analysis are stored in some SQL table
        self.session.add_all(combined_analysis)
        session.query(Data3).filter(Data3.utc_time < cfg["final_time"]).delete()
        self.session.commit()

We also modify the test function now to ensure that we correctly deleted the data. Additionally, we can use get to check
for specific objects being present and ensure their values are correct and still intact.

.. code-block:: python

    import datetime
    import mock

    import pytest
    from mock_alchemy.mocking import UnifiedAlchemyMagicMock

    from data_analysis import complex_data_analysis, Data1, Data2, Data3, CombinedAnalysis

    def test_data_analysis():
        stop_time = datetime.datetime.utcnow()
        cfg = {
            "final_time": stop_time
        }
        data1_values = [
            Data1(1, some, data, values),
            Data1(2, some, data, values),
            Data1(3, some, data, values),
        ]
        data2_values = [
            Data2(1, some, data, values),
            Data2(2, some, data, values),
            Data2(3, some, data, values),
        ]
        data3_values = [
            Data3(1, some, data, values),
            Data3(2, some, data, values),
            Data3(3, some, data, values),
        ]
        session = UnifiedAlchemyMagicMock(data=[
            (
                [mock.call.query(Data1),
                 mock.call.filter(Data1.utc_time < stop_time)],
                data1_values
            ),
            (
                [mock.call.query(Data2),
                 mock.call.filter(Data2.utc_time < stop_time)],
                data2_values
            ),
            (
                [mock.call.query(Data3),
                 mock.call.filter(Data3.utc_time < stop_time)],
                data3_values
            ),
        ])
        complex_data_analysis(cfg, session)
        expected_anyalsis = [
            CombinedAnalysis(1, some, anyalsis, values),
            CombinedAnalysis(2, some, anyalsis, values),
            CombinedAnalysis(3, some, anyalsis, values),
        ]
        combined_anyalsis = session.query(CombinedAnalysis).all()
        assert sorted(combined_anyalsis, key=lambda x: x.pk1) == sorted(expected_anyalsis, key=lambda x: x.pk1)
        assert [] == session.query(Data3).filter(Data3.utc_time < cfg["final_time"])
        expected_anyalsis3 = CombinedAnalysis(3, some, anyalsis, values)
        anyalsis3 = session.query(CombinedAnalysis).get({"pk1": 3})
        assert anyalsis3 == expected_anyalsis3

Abstract Classes
^^^^^^^^^^^^^^^^

It is important to note that mock_alchemy uses Python object attributes instead of SQLAlchemy table attributes. Therefore, please make sure when testing that the column values
are added as object attributes. Refer to the `SQLAlchemy documentation <https://docs.sqlalchemy.org/en/13/orm/constructors.html>`__ for the details on SQLAlchemy initialization, but for this library,
attributes from Python objects are currently used to get column values. In the below example, this is why the primary key must be created inside the class Concrete's __init__. Normally, this is not a
concern since if you do not write a constructor for your Python object, SQLAlchemy initializes the attributes for you. However, if you do write a constructor make sure that the class itself has those
attributes set.

.. code-block:: python

    import datetime
    import mock

    from sqlalchemy import Integer
    from sqlalchemy import Column
    from sqlalchemy.ext.declarative import declarative_base

    from mock_alchemy.mocking import UnifiedAlchemyMagicMock

    Base = declarative_base()


    class BaseModel(Base):
        """Abstract data model to test."""

        __abstract__ = True
        created = Column(Integer, nullable=False, default=3)
        createdby = Column(Integer, nullable=False, default={})
        updated = Column(Integer, nullable=False, default=1)
        updatedby = Column(Integer, nullable=False, default={})
        disabled = Column(Integer, nullable=True)

    class Concrete(BaseModel):
        """A testing SQLAlchemy object."""

        __tablename__ = "concrete"
        id = Column(Integer, primary_key=True)

        def __init__(self, **kwargs: Any) -> None:
            """Creates a Concrete object."""
            self.id = kwargs.pop("id")
            super(Concrete, self).__init__(**kwargs)

        def __eq__(self, other: Concrete) -> bool:
            """Equality override."""
            return self.id == other.id

    objs = Concrete(id=1)
    session = UnifiedAlchemyMagicMock(
        data=[
            ([mock.call.query(Concrete)], [objs]),
        ]
    )
    ret = session.query(Concrete).get(1)
    assert ret == objs

Contribute
-----------

This concludes the example section. If you found these examples lacking in any form, or found a use
for this library in a manner in which these examples failed to illustrate, feel free to contribute to this
documentation. The best way to contribute is to either open an issue or a pull request to suggest changes. If
these examples failed to be useful, feel free to open an issue asking for either more examples or explaining
what is currently unclear. For more details on how to contribute, check out the :ref:`contributor guide <contributor_guide>`.
