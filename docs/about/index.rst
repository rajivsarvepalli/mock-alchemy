.. _about:

About
=====
A project for creating mocking SQLAlchemy sessions and easily comparing SQLAlchemy statements.

Versioning
----------

There are several different versions of ``mock-alchemy`` available depending on your needs. The versions ``0.1.x`` are available for use on
Python 2.7, Python 3.6+. The newer versions serve users who are on Python 3.7+. For people interested in contributing, if you want to work
on Python 2.7 version checkout the branch `0.1.x` and then create pull-requests to that branch. There is a set of specific tests run for that
branch on pushes and pull-requests since there are different tests for the newer versions of ``mock-alchemy``. Check out :ref:`contributor guide <contributor_guide>`
for more information. Documentation for the 0.1.0 version is `available <https://mock-alchemy.readthedocs.io/en/v0.1.0/>`__. However, the current documentation should do a sufficient
job at illustrating both the past and the features of the present version at least as of now. Therefore, I suggest using the most recent documentation for now, and if you want, you can switch using
the readthedocs version system (click on the drop-down menu on the bottom right of the screen or go to the `project page <https://readthedocs.org/projects/mock-alchemy/>`__).

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
This library provides an easy way to mock SQLAlchemy's session
in unittests while preserving the ability to do sane asserts.
Normally SQLAlchemy's expressions cannot be easily compared
as comparison on binary expression produces yet another binary expression::

    >>> type((Model.foo == 5) == (Model.bar == 5))
    <class 'sqlalchemy.sql.elements.BinaryExpression'>

But they can be compared with this library::

    >>> ExpressionMatcher(Model.foo == 5) == (Model.bar == 5)
    False
