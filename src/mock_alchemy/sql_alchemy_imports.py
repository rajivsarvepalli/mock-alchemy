"""A module for importing SQLAlchemy sessions and calls."""
from packaging import version
from sqlalchemy import __version__ as sqlalchemy_version

if version.parse(sqlalchemy_version) >= version.parse("1.4.0"):
    from sqlalchemy.orm import declarative_base
else:
    from sqlalchemy.ext.declarative import declarative_base
