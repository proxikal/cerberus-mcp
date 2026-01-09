"""
SQLite Storage Configuration

Centralized configuration for the SQLite storage subsystem.
"""

# Transaction and batch settings
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_BATCH_SIZE = 100

# Connection settings
DEFAULT_TIMEOUT = 30.0
ENABLE_WAL_MODE = True

# Schema version
SCHEMA_VERSION = "1.0"
