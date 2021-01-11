.. _contributor_guide:

Contributor Guide
==================

This project welcomes contributions and suggestions. Feel free to suggest any changes, correct any bugs,
or add new features. The easiest way is simply through GitHub itself with the issues tab. These suggestions or bugs
can be reported and then addressed. If you want to contribute, you can simply submit a pull-request or make your own package
of this software through forking. Pull-requests are the easiest manner in which to contribute along with appropriate issue labels
which enable a quicker release with release drafter.

Any suggestions are welcome along with any suggestions or contributions.

Thank you for your interest in improving this project.
This project is open-source under the `MIT license`_ and
welcomes contributions in the form of bug reports, feature requests, and pull requests.

Here is a list of important resources for contributors:

- `Source Code`_
- `Documentation`_
- `Issue Tracker`_
- `Code of Conduct`_

.. _MIT license: https://opensource.org/licenses/MIT
.. _Source Code: https://github.com/rajivsarvepalli/mock-alchemy
.. _Documentation: https://mock-alchemy.readthedocs.io/
.. _Issue Tracker: https://github.com/rajivsarvepalli/mock-alchemy/issues

Versioning
----------

different versions based on python version


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

You can now run an interactive Python session,
or the command-line interface:

.. code:: console

   $ poetry run python
   $ poetry run {{cookiecutter.project_name}}

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
.. _Code of Conduct: ../codeofconduct.html

Future Plans
------------

In the near future, I intend to drop support for Python 2 and move to Python 3.7 and above for newer releases. The idea is to keep a branch of release-0.1
that will support Python 2.7, 3.6, and 3.7. This branch will be updated with whatever hotfixes are required and new features are requested. Pull-requests to this branch
will allow for a new release of the 0.1.x version of this package. Any 0.1.x version, as stated before, will support Python 2.7, 3.6, and 3.7. However, the future releases
of > 0.1 will only support Python 3.7 and up.

For the newer releases, type annotations are planned along with other Python 3.7+ features.

Along with this upgrade, many of the tools inside this project have upgraded versions or more modernized alternatives. One major upgrades/changes includes
upgrading `tox <https://tox.readthedocs.io/en/latest/>`__ to `nox <https://nox.thea.codes/en/stable/>`__. Additional alterations may include adding flake8 plugins such
as ``flake8-bandit``, ``flake8-docstrings``, ``flake8-annotations``, and so on.
