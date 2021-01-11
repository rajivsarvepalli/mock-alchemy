.. _contributor_guide:

Contributor Guide
==================

This project welcomes contributions and suggestions. Feel free to suggest any changes, correct any bugs,
or add new features. The easiest way is simply through GitHub itself with the issues tab. These suggestions or bugs
can be reported and then addressed. If you want to contribute, you can simply submit a pull-request or make your own package
of this software through forking. Pull-requests are the easiest manner in which to contribute along with tagging appropriate issues
which enable a quicker release with release drafter.


This project is open-source under the `MIT license`_ and
welcomes contributions in the form of bug reports, feature requests, and pull requests.

Here is a list of important resources for contributors:

- `Source Code`_
- `Documentation`_
- `Issue Tracker`_
- :ref:`Code of Conduct <codeofconduct>`

.. _MIT license: https://opensource.org/licenses/MIT
.. _Source Code: https://github.com/rajivsarvepalli/mock-alchemy
.. _Documentation: https://mock-alchemy.readthedocs.io/

Versioning
----------

There are several different versions of ``mock-alchemy`` available depending on your needs. The versions ``0.1.x`` are available for use on
Python 2.7, Python 3.6+. The newer versions serve users who are on Python 3.7+. For people interested in contributing, if you want to work
on Python 2.7 version checkout the branch `0.1.x` and then create pull-requests to that branch. There is a set of specific tests run for that
branch on pushes and pull-requests since there are different tests for the newer versions of ``mock-alchemy``.

0.1.x Versions
^^^^^^^^^^^^^^

These versions support Python 2.7 and Python 3.6+. They have their development done off the `0.1.x branch <https://github.com/rajivsarvepalli/mock-alchemy/tree/0.1.x>`__.
The tests run for them are through ``tox`` and will run on any push or pull request to 0.1.x branch. To contribute to this branch, you will need different tools
than the ones detailed below. You will need ``tox``, ``poetry``, and ``pre-commit``. I suggest using the versions pinned in the GitHub workflow called Python2-Branch-Tests located
in the ``tests-release.yml`` file. This branch maintains a 100% coverage just like the main branch does for testing. The reason for this separate branch is so that development
can be done on the Python 2.7 version of :mod:`mock-alchemy` while other development can continue on the main branch. This separation through branching allows the ability to keep several releases
live and patchable.

Newer Versions
^^^^^^^^^^^^^^

These versions support Python 3.7+ and have their development done off the `main branch <https://github.com/rajivsarvepalli/mock-alchemy>`__.
The tests run for them are through ``nox`` and will run on any push or pull request to the main branch. To contribute to this branch, use the information
below to support your contribution. The :ref:`dependencies <dependencies>` section should give some information about what tools are required for development of :mod:`mock-alchemy`.

How to report a bug
-------------------

Report bugs on the `Issue Tracker`_.

When filing an issue, make sure to answer these questions:

- Which operating system and Python version are you using?
- Which version of this project are you using?
- What did you do?
- What did you expect to see?
- What did you see instead?

The best way to get your bug fixed is to provide a test case,
and/or steps to reproduce the issue.


How to request a feature
------------------------

Request features on the `Issue Tracker`_.


.. _dependencies:

Dependencies
------------

To develop, there is a much longer list of dependencies than just for the package mainly for the purposes of linting and testing.

The ones to download separately are ``tox``, ``poetry``, and ``pre-commit``. They need to be installed and then the poetry can be used to build and install the project.
``poetry install`` can be used to install the project in the poetry virtual environment for development. Then tox can be used for testing and pre-commit for
linting. `Poetry <https://python-poetry.org/>`__ is used for easy publishing and managing dependencies in a simpler manner than just pure setuptools.

The major libraries used are ``tox``, ``flake8``, ``poetry``, and ``pre-commit``. A full list is available in ``requirements-dev.txt``.

How to set up your development environment
------------------------------------------

You need Python 3.7+ and the following tools:

- Poetry_
- Nox_
- nox-poetry_

Install the package with development requirements:

.. code:: console

   $ poetry install

You can now run an interactive Python session:

.. code:: console

   $ poetry run python

.. _Poetry: https://python-poetry.org/
.. _Nox: https://nox.thea.codes/
.. _nox-poetry: https://nox-poetry.readthedocs.io/


How to test the project
-----------------------

Run the full test suite:

.. code:: console

   $ nox

List the available Nox sessions:

.. code:: console

   $ nox --list-sessions

You can also run a specific Nox session.
For example, invoke the unit test suite like this:

.. code:: console

   $ nox --session=tests

Unit tests are located in the ``tests`` directory,
and are written using the pytest_ testing framework.

.. _pytest: https://pytest.readthedocs.io/


How to submit changes
---------------------

Open a `pull request`_ to submit changes to this project.

Your pull request needs to meet the following guidelines for acceptance:

- The Nox test suite must pass without errors and warnings.
- Include unit tests. This project maintains 100% code coverage.
- If your changes add functionality, update the documentation accordingly.

Feel free to submit early, though—we can always iterate on this.

To run linting and code formatting checks before commiting your change, you can install pre-commit as a Git hook by running the following command:

.. code:: console

   $ nox --session=pre-commit -- install

It is recommended to open an issue before starting work on anything.
This will allow a chance to talk it over with the owners and validate your approach.

.. _pull request: https://github.com/rajivsarvepalli/mock-alchemy/pulls

Future Plans
------------

With the upgraded master branch switching to Python 3.7+, and the 0.1.x branch supporting the older version of this package, the plan
is to continue to modernize this package. Several items are on the list of possible improvements to make:

- Unifying some of the data inside query calls to ensure consistency across mocked filter calls.
- Exploring static type-checking with mypy and more accurate type-hints.
- Adding more complex SQLAlchemy and setting up a simpler way to import data.
   - Maybe enable the ability to import CSV files directly from SQL to provide consistent test data files.

Feel free to suggest any ideas through the `Issue Tracker`_ or any other of the listed means.

.. _Issue Tracker: https://github.com/rajivsarvepalli/mock-alchemy/issues
