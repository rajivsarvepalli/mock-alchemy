.. _contributor_guide:

Contributor Guide
==================

This project welcomes contributions and suggestions. Feel free to suggest any changes, correct any bugs,
or add new features. The easiest way is simply through GitHub itself with the issues tab. These suggestions or bugs
can be reported and then addressed. If you want to contribute, you can simply submit a pull-request or make your own package
of this software through forking. Pull-requests are the easiest manner in which to contribute along with appropriate issue labels
which enable a quicker release with release drafter..

Any suggestions are welcome along with any suggestions or contributions.

Dependencies
------------

To develop, there is a much longer list of dependencies than just for the package mainly for the purposes of linting and testing.

The ones to download separately are ``tox``, ``poetry``, and ``pre-commit``. They need to be installed and then the poetry can be used to build and install the project.
``poetry install`` can be used to install in the project in the poetry virtual environment for development. Then tox can be used for testing and pre-commit for
linting. `Poetry <https://python-poetry.org/>`__ is used for easy publishing and managing dependencies in a simpler manner than just pure setuptools.

The major libraries used are ``tox``, ``flake8``, ``poetry``, and ``pre-commit``. A full list is available in ``requirements-dev.txt``.

Future Plans
------------

In the near future, I intend to drop support for Python 2 and move to Python 3.7 and above for newer releases. The idea is to keep a branch of release-0.1
that will support Python 2.7, 3.6, and 3.7. This branch will be updated with whatever hotfixes are required and new features are requested. Pull-requests to this branch
will allow for a new release of 0.1.x version of this package. Any 0.1.x version, as stated before, will support Python 2.7, 3.6, and 3.7. However, the future releases
of > 0.1 will only support Python 3.7 and up.

For the newer releases, type annotations are planned along with other Python 3.7+ features.

Along with this upgrade, many of the tools inside this project have upgraded versions or more modernized alternatives. One major upgrades/changes includes
upgrading `tox <https://tox.readthedocs.io/en/latest/>`__ to `nox <https://nox.thea.codes/en/stable/>`__. Additional changes may include adding flake8 plugins such
as ``flake8-bandit``, ``flake8-docstrings``, ``flake8-annotations``, and so on.
