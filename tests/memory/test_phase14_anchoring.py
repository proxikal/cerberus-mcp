"""
Phase 14: Dynamic Anchoring Tests

Test suite for code anchor discovery, storage, retrieval, and injection.

Requirements tested:
1. Anchor discovery finds relevant code examples
2. Anchor scoring (relevance, size, recency)
3. Storage integration (stores anchors with memories)
4. Retrieval integration (retrieves anchor data)
5. Injection integration (formats code examples)
6. End-to-end flow
"""

import pytest
import sqlite3
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from cerberus.memory.anchoring import (
    AnchorEngine,
    AnchorCandidate,
    extract_language_from_scope,
    extract_project_from_scope
)
from cerberus.memory.storage import MemoryStorage
from cerberus.memory.retrieval import MemoryRetrieval
from cerberus.memory.context_injector import ContextInjector, DetectedContext
from cerberus.memory.indexing import MemoryIndexManager


@pytest.fixture
def temp_memory_dir(tmp_path):
    """Create temporary memory directory with database."""
    memory_dir = tmp_path / ".cerberus"
    memory_dir.mkdir()

    # Initialize database schema
    manager = MemoryIndexManager(memory_dir)

    return memory_dir


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create temporary project directory with example code files."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create Python example files
    (project_dir / "repository.py").write_text("""
class UserRepository:
    \"\"\"Repository pattern for user data access.\"\"\"

    def __init__(self, db_connection):
        self.db = db_connection

    def find_by_id(self, user_id: int):
        return self.db.query("SELECT * FROM users WHERE id = ?", user_id)

    def save(self, user):
        return self.db.execute("INSERT INTO users VALUES (?)", user)
""")

    (project_dir / "validator.py").write_text("""
def validate_input(data: dict) -> bool:
    \"\"\"Validate user input data.\"\"\"
    required_fields = ['username', 'email', 'password']

    for field in required_fields:
        if field not in data:
            return False
        if not data[field]:
            return False

    return True
""")

    (project_dir / "async_handler.py").write_text("""
import asyncio

async def handle_request(request):
    \"\"\"Async request handler.\"\"\"
    await asyncio.sleep(0.1)
    return {"status": "ok"}
""")

    return project_dir


class TestAnchorEngine:
    """Test AnchorEngine anchor discovery and scoring."""

    def test_extract_keywords(self, temp_project_dir):
        """Test keyword extraction from rules."""
        engine = AnchorEngine(temp_project_dir)

        # Test 1: Simple rule
        keywords = engine._extract_keywords("Use Repository pattern")
        assert "repository" in keywords
        assert "pattern" in keywords
        assert "use" not in keywords  # Stopword

        # Test 2: Technical rule
        keywords = engine._extract_keywords("Always validate input")
        assert "validate" in keywords
        assert "input" in keywords
        assert "always" not in keywords  # Stopword

        # Test 3: Async rule
        keywords = engine._extract_keywords("Prefer async/await")
        assert "async" in keywords or "await" in keywords
        assert "prefer" not in keywords  # Stopword

    def test_calculate_relevance(self, temp_project_dir):
        """Test TF-IDF relevance calculation."""
        engine = AnchorEngine(temp_project_dir)

        # Test 1: High relevance
        rule = "Use Repository pattern for database access"
        file_path = str(temp_project_dir / "repository.py")
        relevance = engine._calculate_relevance(rule, file_path)

        assert relevance > 0.0, "Should find some relevance"
        assert relevance <= 1.0, "Relevance should be normalized"

        # Test 2: Low relevance
        rule = "Use Repository pattern"
        file_path = str(temp_project_dir / "async_handler.py")
        relevance = engine._calculate_relevance(rule, file_path)

        # Repository rule should have lower relevance to async_handler
        assert relevance >= 0.0

    def test_calculate_recency(self, temp_project_dir):
        """Test file recency scoring."""
        engine = AnchorEngine(temp_project_dir)

        file_path = str(temp_project_dir / "repository.py")
        recency = engine._calculate_recency(file_path)

        # Recently created file should have high recency
        assert recency > 0.5, "New file should have high recency"
        assert recency <= 1.0, "Recency should be normalized"

    def test_get_file_size(self, temp_project_dir):
        """Test file size calculation."""
        engine = AnchorEngine(temp_project_dir)

        file_path = str(temp_project_dir / "repository.py")
        size = engine._get_file_size(file_path)

        assert size > 0, "File should have lines"
        assert size < 100, "Example file should be small"

    @patch('cerberus.mcp.index_manager.get_index_manager')
    @patch('cerberus.retrieval.hybrid_search')
    def test_search_code(self, mock_hybrid_search, mock_get_index_manager, temp_project_dir):
        """Test code search via Cerberus index."""
        # Mock Cerberus index manager
        mock_manager = Mock()
        mock_manager._index_path = str(temp_project_dir / ".cerberus_index")
        mock_manager._discover_index_path.return_value = str(temp_project_dir / ".cerberus_index")
        mock_get_index_manager.return_value = mock_manager

        # Mock search results
        mock_result = Mock()
        mock_result.symbol = Mock()
        mock_result.symbol.file_path = str(temp_project_dir / "repository.py")
        mock_result.symbol.name = "UserRepository"
        mock_result.symbol.type = "class"
        mock_result.symbol.start_line = 2
        mock_result.symbol.end_line = 11
        mock_result.hybrid_score = 0.85

        mock_hybrid_search.return_value = [mock_result]

        # Test search
        engine = AnchorEngine(temp_project_dir)
        keywords = ["repository", "pattern"]
        candidates = engine._search_code(keywords, temp_project_dir, language="python")

        assert len(candidates) > 0, "Should find candidates"
        assert candidates[0]['file_path'] == str(temp_project_dir / "repository.py")
        assert candidates[0]['name'] == "UserRepository"

    @patch('cerberus.mcp.index_manager.get_index_manager')
    @patch('cerberus.retrieval.hybrid_search')
    def test_find_anchor_success(self, mock_hybrid_search, mock_get_index_manager, temp_project_dir):
        """Test successful anchor discovery."""
        # Mock Cerberus components
        mock_manager = Mock()
        mock_manager._index_path = str(temp_project_dir / ".cerberus_index")
        mock_manager._discover_index_path.return_value = str(temp_project_dir / ".cerberus_index")
        mock_get_index_manager.return_value = mock_manager

        mock_result = Mock()
        mock_result.symbol = Mock()
        mock_result.symbol.file_path = str(temp_project_dir / "repository.py")
        mock_result.symbol.name = "UserRepository"
        mock_result.symbol.type = "class"
        mock_result.symbol.start_line = 2
        mock_result.symbol.end_line = 11
        mock_result.hybrid_score = 0.85

        mock_hybrid_search.return_value = [mock_result]

        # Test anchor discovery
        engine = AnchorEngine(temp_project_dir)
        anchor = engine.find_anchor(
            rule="Use Repository pattern for database access",
            scope="language:python",
            language="python",
            project_path=temp_project_dir,
            min_quality=0.3  # Lower threshold for testing
        )

        assert anchor is not None, "Should find anchor"
        assert anchor.file_path == str(temp_project_dir / "repository.py")
        assert anchor.quality_score > 0.0

    def test_find_anchor_universal_scope(self, temp_project_dir):
        """Test that universal scope returns no anchor."""
        engine = AnchorEngine(temp_project_dir)
        anchor = engine.find_anchor(
            rule="Use consistent naming",
            scope="universal",
            min_quality=0.7
        )

        assert anchor is None, "Universal scope should not anchor"

    def test_read_anchor_code(self, temp_project_dir):
        """Test reading code snippet from anchor file."""
        engine = AnchorEngine(temp_project_dir)

        # Test reading with symbol name
        file_path = str(temp_project_dir / "repository.py")
        code = engine.read_anchor_code(file_path, symbol_name="UserRepository", max_lines=10)

        assert "UserRepository" in code, "Should contain symbol"
        assert "class" in code, "Should contain class definition"

        # Test reading without symbol (first N lines)
        code = engine.read_anchor_code(file_path, max_lines=5)
        assert len(code.split('\n')) <= 6, "Should limit lines"  # +1 for potential trailing newline

    def test_anchor_memory_language_scope(self, temp_project_dir):
        """Test anchoring with language scope."""
        # We'll mock the find_anchor call since it requires Cerberus index
        engine = AnchorEngine(temp_project_dir)

        with patch.object(engine, 'find_anchor', return_value=None) as mock_find:
            result = engine.anchor_memory(
                memory_id="test-123",
                content="Use Repository pattern",
                scope="language:python"
            )

            # Verify find_anchor was called with correct language
            mock_find.assert_called_once()
            call_kwargs = mock_find.call_args[1]
            assert call_kwargs['language'] == "python"


class TestStorageIntegration:
    """Test anchor discovery integration with storage."""

    @patch('cerberus.memory.storage.AnchorEngine')
    def test_store_with_anchor_discovery(self, mock_anchor_engine_class, temp_memory_dir):
        """Test that storage discovers and stores anchors."""
        # Mock AnchorEngine
        mock_engine = Mock()
        mock_anchor = Mock()
        mock_anchor.file_path = "/path/to/example.py"
        mock_anchor.symbol_name = "ExampleClass"
        mock_anchor.quality_score = 0.85
        mock_anchor.file_size = 50
        mock_anchor.match_score = 0.9
        mock_anchor.recency_score = 0.8
        mock_engine.anchor_memory.return_value = mock_anchor
        mock_anchor_engine_class.return_value = mock_engine

        # Create storage with anchoring enabled
        storage = MemoryStorage(base_dir=temp_memory_dir, enable_anchoring=True)

        # Create test proposal
        proposal = Mock()
        proposal.category = "rule"
        proposal.scope = "language:python"
        proposal.content = "Use Repository pattern"
        proposal.confidence = 1.0
        proposal.rationale = "Improves testability"
        proposal.evidence = []
        proposal.source_variants = []

        # Store proposal
        result = storage.store_batch([proposal])

        assert result['total_stored'] == 1

        # Verify anchor was stored in database
        conn = sqlite3.connect(str(temp_memory_dir / "memory.db"))
        cursor = conn.execute("""
            SELECT anchor_file, anchor_symbol, anchor_score, anchor_metadata
            FROM memory_store
        """)
        row = cursor.fetchone()
        conn.close()

        assert row[0] == "/path/to/example.py"  # anchor_file
        assert row[1] == "ExampleClass"  # anchor_symbol
        assert row[2] == 0.85  # anchor_score

        metadata = json.loads(row[3])
        assert metadata['file_size'] == 50
        assert metadata['match_score'] == 0.9

    def test_store_without_anchor_discovery(self, temp_memory_dir):
        """Test that anchoring can be disabled."""
        storage = MemoryStorage(base_dir=temp_memory_dir, enable_anchoring=False)

        proposal = Mock()
        proposal.category = "rule"
        proposal.scope = "language:python"
        proposal.content = "Use Repository pattern"
        proposal.confidence = 1.0
        proposal.rationale = "Improves testability"
        proposal.evidence = []
        proposal.source_variants = []

        result = storage.store_batch([proposal])

        assert result['total_stored'] == 1

        # Verify no anchor stored
        conn = sqlite3.connect(str(temp_memory_dir / "memory.db"))
        cursor = conn.execute("""
            SELECT anchor_file, anchor_symbol, anchor_score
            FROM memory_store
        """)
        row = cursor.fetchone()
        conn.close()

        assert row[0] is None  # No anchor_file
        assert row[1] is None  # No anchor_symbol
        assert row[2] is None  # No anchor_score


class TestRetrievalIntegration:
    """Test anchor data retrieval."""

    def test_retrieve_with_anchor_data(self, temp_memory_dir):
        """Test that retrieval includes anchor data."""
        # Insert test memory with anchor
        conn = sqlite3.connect(str(temp_memory_dir / "memory.db"))
        memory_id = "test-anchor-123"

        conn.execute("""
            INSERT INTO memory_store (
                id, category, scope, confidence, created_at, last_accessed, access_count, metadata,
                anchor_file, anchor_symbol, anchor_score, anchor_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id, "rule", "language:python", 1.0,
            datetime.now().isoformat(), datetime.now().isoformat(), 0,
            json.dumps({"rationale": "Testing"}),
            "/path/to/example.py", "ExampleClass", 0.85,
            json.dumps({"file_size": 50, "match_score": 0.9, "recency_score": 0.8})
        ))

        conn.execute("""
            INSERT INTO memory_fts (id, content)
            VALUES (?, ?)
        """, (memory_id, "Use Repository pattern"))

        conn.commit()
        conn.close()

        # Retrieve memories
        retrieval = MemoryRetrieval(base_dir=temp_memory_dir)
        memories = retrieval.retrieve(language="python", token_budget=2000)

        assert len(memories) > 0
        memory = memories[0]

        assert memory.anchor_file == "/path/to/example.py"
        assert memory.anchor_symbol == "ExampleClass"
        assert memory.anchor_score == 0.85
        assert memory.anchor_metadata is not None
        assert memory.anchor_metadata['file_size'] == 50

    def test_retrieve_without_anchor(self, temp_memory_dir):
        """Test retrieval of memories without anchors."""
        # Insert test memory without anchor
        conn = sqlite3.connect(str(temp_memory_dir / "memory.db"))
        memory_id = "test-no-anchor-123"

        conn.execute("""
            INSERT INTO memory_store (
                id, category, scope, confidence, created_at, last_accessed, access_count, metadata,
                anchor_file, anchor_symbol, anchor_score, anchor_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id, "rule", "universal", 1.0,
            datetime.now().isoformat(), datetime.now().isoformat(), 0,
            json.dumps({"rationale": "Testing"}),
            None, None, None, None
        ))

        conn.execute("""
            INSERT INTO memory_fts (id, content)
            VALUES (?, ?)
        """, (memory_id, "Use consistent naming"))

        conn.commit()
        conn.close()

        # Retrieve memories
        retrieval = MemoryRetrieval(base_dir=temp_memory_dir)
        memories = retrieval.retrieve(token_budget=2000)

        assert len(memories) > 0
        memory = memories[0]

        assert memory.anchor_file is None
        assert memory.anchor_symbol is None
        assert memory.anchor_score is None
        assert memory.anchor_metadata is None


class TestInjectionIntegration:
    """Test anchor integration with context injection."""

    def test_inject_with_code_examples(self, temp_memory_dir, temp_project_dir):
        """Test that injection includes code examples from anchors."""
        # Insert test memory with anchor
        conn = sqlite3.connect(str(temp_memory_dir / "memory.db"))
        memory_id = "test-inject-123"

        anchor_file = str(temp_project_dir / "repository.py")

        conn.execute("""
            INSERT INTO memory_store (
                id, category, scope, confidence, created_at, last_accessed, access_count, metadata,
                anchor_file, anchor_symbol, anchor_score, anchor_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id, "rule", "language:python", 1.0,
            datetime.now().isoformat(), datetime.now().isoformat(), 0,
            json.dumps({"rationale": "Testing"}),
            anchor_file, "UserRepository", 0.85,
            json.dumps({"file_size": 50, "match_score": 0.9, "recency_score": 0.8})
        ))

        conn.execute("""
            INSERT INTO memory_fts (id, content)
            VALUES (?, ?)
        """, (memory_id, "Use Repository pattern"))

        conn.commit()
        conn.close()

        # Inject with anchoring enabled
        injector = ContextInjector(base_dir=temp_memory_dir, enable_anchoring=True)
        context = DetectedContext(project="test_project", language="python")

        formatted = injector.inject_startup(context=context, min_relevance=0.0)

        assert "Use Repository pattern" in formatted
        assert "Example:" in formatted
        assert "repository.py" in formatted
        assert "```py" in formatted or "```python" in formatted
        assert "UserRepository" in formatted

    def test_inject_without_anchoring(self, temp_memory_dir, temp_project_dir):
        """Test that anchoring can be disabled in injection."""
        # Insert test memory with anchor
        conn = sqlite3.connect(str(temp_memory_dir / "memory.db"))
        memory_id = "test-inject-no-anchor-123"

        anchor_file = str(temp_project_dir / "repository.py")

        conn.execute("""
            INSERT INTO memory_store (
                id, category, scope, confidence, created_at, last_accessed, access_count, metadata,
                anchor_file, anchor_symbol, anchor_score, anchor_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id, "rule", "language:python", 1.0,
            datetime.now().isoformat(), datetime.now().isoformat(), 0,
            json.dumps({"rationale": "Testing"}),
            anchor_file, "UserRepository", 0.85,
            json.dumps({"file_size": 50, "match_score": 0.9, "recency_score": 0.8})
        ))

        conn.execute("""
            INSERT INTO memory_fts (id, content)
            VALUES (?, ?)
        """, (memory_id, "Use Repository pattern"))

        conn.commit()
        conn.close()

        # Inject with anchoring disabled
        injector = ContextInjector(base_dir=temp_memory_dir, enable_anchoring=False)
        context = DetectedContext(project="test_project", language="python")

        formatted = injector.inject_startup(context=context, min_relevance=0.0)

        assert "Use Repository pattern" in formatted
        assert "Example:" not in formatted  # No code examples
        assert "```" not in formatted  # No code blocks


class TestEndToEnd:
    """Test complete end-to-end anchor flow."""

    @patch('cerberus.memory.storage.AnchorEngine')
    def test_complete_anchor_flow(self, mock_anchor_engine_class, temp_memory_dir, temp_project_dir):
        """Test complete flow: store → retrieve → inject with anchors."""
        # Mock AnchorEngine for storage
        mock_engine = Mock()
        mock_anchor = Mock()
        anchor_file = str(temp_project_dir / "repository.py")
        mock_anchor.file_path = anchor_file
        mock_anchor.symbol_name = "UserRepository"
        mock_anchor.quality_score = 0.85
        mock_anchor.file_size = 50
        mock_anchor.match_score = 0.9
        mock_anchor.recency_score = 0.8
        mock_engine.anchor_memory.return_value = mock_anchor
        mock_anchor_engine_class.return_value = mock_engine

        # Step 1: Store memory with anchor
        storage = MemoryStorage(base_dir=temp_memory_dir, enable_anchoring=True)

        proposal = Mock()
        proposal.category = "rule"
        proposal.scope = "language:python"
        proposal.content = "Use Repository pattern for data access"
        proposal.confidence = 1.0
        proposal.rationale = "Improves testability and maintainability"
        proposal.evidence = []
        proposal.source_variants = []

        result = storage.store_batch([proposal])
        assert result['total_stored'] == 1

        # Step 2: Retrieve memory with anchor data
        retrieval = MemoryRetrieval(base_dir=temp_memory_dir)
        memories = retrieval.retrieve(language="python", token_budget=2000)

        assert len(memories) > 0
        memory = memories[0]
        assert memory.anchor_file == anchor_file
        assert memory.anchor_symbol == "UserRepository"

        # Step 3: Inject with code example
        injector = ContextInjector(base_dir=temp_memory_dir, enable_anchoring=True)
        context = DetectedContext(project="test_project", language="python")

        formatted = injector.inject_startup(context=context, min_relevance=0.0)

        assert "Use Repository pattern" in formatted
        assert "Example:" in formatted
        assert "repository.py" in formatted
        assert "```" in formatted
        assert "UserRepository" in formatted


class TestUtilityFunctions:
    """Test utility functions."""

    def test_extract_language_from_scope(self):
        """Test language extraction from scope."""
        assert extract_language_from_scope("language:python") == "python"
        assert extract_language_from_scope("language:go") == "go"
        assert extract_language_from_scope("universal") is None
        assert extract_language_from_scope("project:cerberus") is None

    def test_extract_project_from_scope(self):
        """Test project extraction from scope."""
        assert extract_project_from_scope("project:cerberus") == "cerberus"
        assert extract_project_from_scope("project:myapp") == "myapp"
        assert extract_project_from_scope("universal") is None
        assert extract_project_from_scope("language:python") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
