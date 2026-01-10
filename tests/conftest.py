import pytest
from cerberus.logging_config import setup_logging

@pytest.fixture(autouse=True)
def setup_test_logging():
    """
    Phase 10: Machine mode by default - suppress console logs for clean test output.
    """
    # Machine mode: suppress console logging, only write to file
    setup_logging(level="DEBUG", suppress_console=True)
