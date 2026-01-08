import pytest
from cerberus.logging_config import setup_logging

@pytest.fixture(autouse=True)
def setup_test_logging():
    """
    Forces the logger to DEBUG level for all tests.
    """
    # Re-run setup, but force the level. 
    # This is a simple way to do it for our project.
    setup_logging(level="DEBUG")
