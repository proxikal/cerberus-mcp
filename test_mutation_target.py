"""Test file for mutation testing."""


def original_function():
    """A simple function to test editing."""
    return "original"


def function_to_delete():
    """A function that will be deleted."""
    return "delete me"


class TestClass:
    """A test class."""

    def method_one(self):
        """First method."""
        return 1

    def method_two(self):
        """Second method."""
        return 2
