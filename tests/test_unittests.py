"""Testing the module for unittests in mock-alchemy."""
import unittest

import pytest
from sqlalchemy.sql.expression import column

from mock_alchemy.unittests import AlchemyUnittestMixin


def test_unittest_mixin() -> None:
    """Tests if SQLAlchemy expressin matching works correctly in unittest enviroment."""

    class FooTest(AlchemyUnittestMixin, unittest.TestCase):
        def test_true(self) -> None:
            c = column("column")
            self.assertEqual(c == 5, c == 5)

        def test_false(self) -> None:
            c = column("column")
            self.assertEqual(c == 5, c == 10)

    FooTest("test_true").test_true()
    with pytest.raises(AssertionError):
        FooTest("test_false").test_false()
