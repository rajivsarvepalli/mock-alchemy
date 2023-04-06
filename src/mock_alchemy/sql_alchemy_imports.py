"""A module for importing SQLAlchemy sessions and calls."""
import sqlalchemy
from packaging import version

if version.parse(sqlalchemy.__version__) >= version.parse("1.4.0"):
    from sqlalchemy.orm import declarative_base
else:
    from sqlalchemy.ext.declarative import declarative_base
