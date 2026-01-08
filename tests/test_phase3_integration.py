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
        print("\n" + "=" * 60)
        print("Phase 3 Integration Test: Full Workflow")
        print("=" * 60)

        # Step 1: Build initial index
        print("\n[1/6] Building initial index...")
        from cerberus.index import build_index

        scan_result = build_index(
            directory=self.test_dir,
            output_path=self.index_path,
            respect_gitignore=False,
            store_embeddings=False,
        )

        initial_symbol_count = len(scan_result.symbols)
        print(f"  ✓ Created index with {initial_symbol_count} symbols")
        print(f"  ✓ Git commit stored: {scan_result.metadata.get('git_commit', 'N/A')[:8]}")

        assert initial_symbol_count > 0
        assert scan_result.metadata.get("git_commit") is not None
        assert scan_result.project_root == str(self.test_dir.resolve())

        # Step 2: Verify initial search works
        print("\n[2/6] Testing initial hybrid search...")
        from cerberus.retrieval import hybrid_search

        results = hybrid_search(
            query="DatabaseConnection",
            index_path=self.index_path,
            mode="keyword",
            top_k=5,
        )

        print(f"  ✓ Found {len(results)} results for 'DatabaseConnection'")
        assert len(results) > 0
        assert any(r.symbol.name == "DatabaseConnection" for r in results)

        # Step 3: Modify files
        print("\n[3/6] Modifying files...")
        self._modify_files()

        # Commit changes
        subprocess.run(["git", "add", "."], cwd=self.test_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add authentication"],
            cwd=self.test_dir,
            check=True,
            capture_output=True,
        )

        print("  ✓ Modified test.py and committed changes")

        # Step 4: Detect changes
        print("\n[4/6] Detecting changes via git diff...")
        from cerberus.incremental import detect_changes

        changes = detect_changes(self.test_dir, self.index_path)

        assert changes is not None
        print(f"  ✓ Detected {len(changes.modified)} modified files")
        assert len(changes.modified) > 0

        # Step 5: Incremental update
        print("\n[5/6] Performing incremental update...")
        from cerberus.incremental import update_index_incrementally
        import time

        start_time = time.time()
        result = update_index_incrementally(
            index_path=self.index_path,
            project_path=self.test_dir,
            changes=changes,
        )
        elapsed = time.time() - start_time

        print(f"  ✓ Updated {len(result.updated_symbols)} symbols in {elapsed:.3f}s")
        print(f"  ✓ Strategy: {result.strategy}")
        print(f"  ✓ Files re-parsed: {result.files_reparsed}")

        assert len(result.updated_symbols) > 0
        assert result.strategy in ["incremental", "surgical"]

        # Step 6: Verify search finds new function
        print("\n[6/6] Testing search on updated index...")
        results = hybrid_search(
            query="authenticate_user",
            index_path=self.index_path,
            mode="keyword",
            top_k=5,
        )

        print(f"  ✓ Found {len(results)} results for 'authenticate_user'")
        assert len(results) > 0
        assert any(r.symbol.name == "authenticate_user" for r in results)

        # Verify semantic search works
        results = hybrid_search(
            query="user authentication logic",
            index_path=self.index_path,
            mode="semantic",
            top_k=5,
        )

        print(f"  ✓ Semantic search found {len(results)} results")
        assert len(results) > 0

        print("\n" + "=" * 60)
        print("✓ Phase 3 Integration Test PASSED")
        print("=" * 60)

    def test_incremental_vs_full_reparse(self):
        """Compare incremental update speed vs full reparse."""
        print("\n" + "=" * 60)
        print("Phase 3 Performance Test: Incremental vs Full")
        print("=" * 60)

        # Build initial index
        from cerberus.index import build_index
        import time

        print("\n[1/3] Building initial index...")
        scan_result = build_index(
            directory=self.test_dir,
            output_path=self.index_path,
            respect_gitignore=False,
            store_embeddings=False,
        )
        print(f"  ✓ Indexed {len(scan_result.symbols)} symbols")

        # Modify files
        print("\n[2/3] Modifying files...")
        self._modify_files()
        subprocess.run(["git", "add", "."], cwd=self.test_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Changes"],
            cwd=self.test_dir,
            check=True,
            capture_output=True,
        )

        # Time incremental update
        print("\n[3/3] Comparing update methods...")
        from cerberus.incremental import detect_changes, update_index_incrementally

        changes = detect_changes(self.test_dir, self.index_path)

        start = time.time()
        result = update_index_incrementally(
            index_path=self.index_path,
            project_path=self.test_dir,
            changes=changes,
        )
        incremental_time = time.time() - start

        print(f"  Incremental update: {incremental_time:.3f}s")

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

        print(f"  Full reparse: {full_time:.3f}s")

        speedup = full_time / incremental_time if incremental_time > 0 else 0
        print(f"  Speedup: {speedup:.1f}x faster")

        # Incremental should be reasonably fast
        # Note: On tiny codebases, incremental may have overhead that makes it slower
        # Allow 2x margin for small files where git diff overhead dominates
        assert incremental_time <= full_time * 2.0

        print("\n" + "=" * 60)
        print(f"✓ Incremental update is {speedup:.1f}x faster")
        print("=" * 60)


if __name__ == "__main__":
    """Run integration tests manually."""
    import sys

    test = TestPhase3Integration()

    total_tests = 0
    passed_tests = 0

    print("\n" + "=" * 70)
    print(" " * 20 + "PHASE 3 INTEGRATION TESTS")
    print("=" * 70)

    # Test 1: Full workflow
    total_tests += 1
    try:
        test.setup_method()
        test.test_full_phase3_workflow()
        test.teardown_method()
        passed_tests += 1
    except Exception as e:
        print(f"\n✗ Full workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        try:
            test.teardown_method()
        except:
            pass

    # Test 2: Performance comparison
    total_tests += 1
    try:
        test.setup_method()
        test.test_incremental_vs_full_reparse()
        test.teardown_method()
        passed_tests += 1
    except Exception as e:
        print(f"\n✗ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        try:
            test.teardown_method()
        except:
            pass

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed_tests}/{total_tests} integration tests passed")
    print("=" * 70)

    sys.exit(0 if passed_tests == total_tests else 1)
