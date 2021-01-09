.. _about:

About
=====
A project for creating mocking SQLAlchemy sessions and easily comparing SQLAlchemy statements.

Credit
----------

The original library (``alchemy-mock``) was created by Miroslav Shubernetskiy and Serkan Hoscai. This is a forked version due to a lack of updates
in the original library. It appeared that the ``alchemy-mock`` project was no longer supported. Therefore, since I desired to add some basic support
for deleting, I created my own version of the library. Full credit goes to the original creators for starting and building this project. You can find the
original package on `PyPi <https://pypi.org/project/alchemy-mock/>`__ and `Github <https://github.com/miki725/alchemy-mock>`__.

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
