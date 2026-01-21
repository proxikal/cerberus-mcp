"""
Integration tests for Phase 3: Complete pipeline testing.

Tests the full Phase 3 workflow:
1. Create index with git tracking
2. Modify files
3. Incremental update via git diff
4. Hybrid search on updated index
"""

import os
import json
import tempfile
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.phase3]

class TestPhase3Integration:
    """Integration tests for Phase 3 complete workflow."""

    def setup_method(self):
        """Set up test environment with a git repository."""
        # Create temporary directory
        self.test_dir = Path(tempfile.mkdtemp(prefix="cerberus_test_"))
        self.index_path = self.test_dir / "test_index.json"

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=self.test_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.test_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=self.test_dir,
            check=True,
            capture_output=True,
        )

        # Create initial test files
        self._create_initial_files()

        # Initial git commit
        subprocess.run(["git", "add", "."], cwd=self.test_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=self.test_dir,
            check=True,
            capture_output=True,
        )

    def teardown_method(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _create_initial_files(self):
        """Create initial test files."""
        # Create test.py
        test_py = self.test_dir / "test.py"
        test_py.write_text("""
class DatabaseConnection:
    \"\"\"Manages database connections.\"\"\"

    def connect(self):
        \"\"\"Connect to database.\"\"\"
        pass

    def disconnect(self):
        \"\"\"Disconnect from database.\"\"\"
        pass

def get_user_data(user_id):
    \"\"\"Retrieve user data from database.\"\"\"
    conn = DatabaseConnection()
    conn.connect()
    # Fetch data
    conn.disconnect()
    return data

class User:
    \"\"\"User model.\"\"\"
    def __init__(self, name):
        self.name = name
""")

    def _modify_files(self):
        """Modify test files to simulate code changes."""
        test_py = self.test_dir / "test.py"
        test_py.write_text("""
class DatabaseConnection:
    \"\"\"Manages database connections with pooling.\"\"\"

    def connect(self):
        \"\"\"Connect to database with retry logic.\"\"\"
        # Added retry logic
        pass

    def disconnect(self):
        \"\"\"Disconnect from database.\"\"\"
        pass

    def get_pool_size(self):
        \"\"\"Get connection pool size.\"\"\"
        return 10

def get_user_data(user_id):
    \"\"\"Retrieve user data from database.\"\"\"
    conn = DatabaseConnection()
    conn.connect()
    # Fetch data
    conn.disconnect()
    return data

def authenticate_user(username, password):
    \"\"\"Authenticate user with credentials.\"\"\"
    # New function
    return True

class User:
    \"\"\"User model with authentication.\"\"\"
    def __init__(self, name):
        self.name = name

    def is_authenticated(self):
        \"\"\"Check if user is authenticated.\"\"\"
        return True
""")

    def test_full_phase3_workflow(self):
        """Test complete Phase 3 workflow."""

        # Step 1: Build initial index
        from cerberus.index import build_index

        scan_result = build_index(
            directory=self.test_dir,
            output_path=self.index_path,
            respect_gitignore=False,
            store_embeddings=False,
        )

        initial_symbol_count = len(scan_result.symbols)

        assert initial_symbol_count > 0
        assert scan_result.metadata.get("git_commit") is not None
        assert scan_result.project_root == str(self.test_dir.resolve())

        # Step 2: Verify initial search works
        from cerberus.retrieval import hybrid_search

        results = hybrid_search(
            query="DatabaseConnection",
            index_path=self.index_path,
            mode="keyword",
            top_k=5,
        )

        assert len(results) > 0
        assert any(r.symbol.name == "DatabaseConnection" for r in results)

        # Step 3: Modify files
        self._modify_files()

        # Commit changes
        subprocess.run(["git", "add", "."], cwd=self.test_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add authentication"],
            cwd=self.test_dir,
            check=True,
            capture_output=True,
        )

        # Step 4: Detect changes
        from cerberus.incremental import detect_changes

        changes = detect_changes(self.test_dir, self.index_path)

        assert changes is not None
        assert len(changes.modified) > 0

        # Step 5: Incremental update
        from cerberus.incremental import update_index_incrementally
        import time

        start_time = time.time()
        result = update_index_incrementally(
            index_path=self.index_path,
            project_path=self.test_dir,
            changes=changes,
        )
        elapsed = time.time() - start_time

        assert len(result.updated_symbols) > 0
        assert result.strategy in ["incremental", "surgical"]

        # Step 6: Verify search finds new function
        results = hybrid_search(
            query="authenticate_user",
            index_path=self.index_path,
            mode="keyword",
            top_k=5,
        )

        assert len(results) > 0
        assert any(r.symbol.name == "authenticate_user" for r in results)

        # Verify semantic search works
        results = hybrid_search(
            query="user authentication logic",
            index_path=self.index_path,
            mode="semantic",
            top_k=5,
        )

        assert len(results) > 0

    def test_incremental_vs_full_reparse(self):
        """Compare incremental update speed vs full reparse."""

        # Build initial index
        from cerberus.index import build_index
        import time

        scan_result = build_index(
            directory=self.test_dir,
            output_path=self.index_path,
            respect_gitignore=False,
            store_embeddings=False,
        )

        # Modify files
        self._modify_files()
        subprocess.run(["git", "add", "."], cwd=self.test_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Changes"],
            cwd=self.test_dir,
            check=True,
            capture_output=True,
        )

        # Time incremental update
        from cerberus.incremental import detect_changes, update_index_incrementally

        changes = detect_changes(self.test_dir, self.index_path)

        start = time.time()
        result = update_index_incrementally(
            index_path=self.index_path,
            project_path=self.test_dir,
            changes=changes,
        )
        incremental_time = time.time() - start

        # Time full reparse (build new index)
        full_index_path = self.test_dir / "full_index.json"
        start = time.time()
        build_index(
            directory=self.test_dir,
            output_path=full_index_path,
            respect_gitignore=False,
            store_embeddings=False,
        )
        full_time = time.time() - start

        speedup = full_time / incremental_time if incremental_time > 0 else 0

        # Incremental should be reasonably fast
        # Note: On tiny codebases, incremental may have overhead that makes it slower
        # Allow 5x margin for small files where git diff overhead dominates
        # and to account for CI environment performance variance
        assert incremental_time <= full_time * 5.0
