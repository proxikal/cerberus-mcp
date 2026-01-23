# Obsolete Tests

This directory contains test files that are no longer compatible with the current codebase architecture.

## Why These Tests Are Obsolete

The memory system was refactored from **file-based storage** to **SQLite-based storage** (commit 62e9ee9 and earlier).

### Removed APIs

Phase 16/17 tests reference functions and classes that were removed during the SQLite migration:

**From `hooks.py`:**
- `start_session()` - moved to `session_lifecycle.py`
- `end_session()` - moved to `session_lifecycle.py`
- `SESSION_FILE` constant - removed (now in SQLite)

**From `session_lifecycle.py`:**
- `SessionRecovery` class - removed
- `detect_crash()` - removed
- `auto_recover_crash()` - removed
- `check_idle_timeout()` - removed
- `idle_timeout_daemon()` - removed

### Affected Test Files

- `test_phase16_end_to_end.py` - End-to-end integration tests
- `test_phase16_integration.py` - Integration tests
- `test_phase17_crash_scenarios.py` - Crash detection tests
- `test_phase17_lifecycle.py` - Session lifecycle tests

## Future Work

These tests could be rewritten to match the new SQLite-based architecture if needed.
