"""
Phase 2: Duplicate elimination guardrails.

Covers search fusion dedup, symbol query dedup, and blueprint symbol dedup.
"""

import sqlite3
from pathlib import Path

import pytest

from cerberus.schemas import CodeSymbol, CodeSnippet, SearchResult
from cerberus.retrieval.hybrid_ranker import reciprocal_rank_fusion
from cerberus.storage.sqlite.schema import init_schema
from cerberus.storage.sqlite.symbols import SQLiteSymbolsOperations
from cerberus.blueprint.facade import BlueprintGenerator

pytestmark = [pytest.mark.fast, pytest.mark.phase2]


@pytest.fixture
def in_memory_conn():
    """Provide an initialized in-memory SQLite index."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn, ":memory:")
    # Simulate legacy/dirty indexes by allowing duplicate symbols in tests
    conn.execute("DROP INDEX IF EXISTS idx_symbols_unique")
    yield conn
    conn.close()


def _insert_file(conn, path: str):
    conn.execute(
        """
        INSERT INTO files (path, abs_path, size, last_modified)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(path) DO NOTHING
        """,
        (path, path, 10, 0.0),
    )


def test_reciprocal_rank_fusion_deduplicates_same_symbol():
    """RRF should collapse duplicate symbols across and within sources."""
    symbol = CodeSymbol(
        name="foo", type="function", file_path="test.py", start_line=10, end_line=12
    )
    snippet = CodeSnippet(file_path="test.py", start_line=10, end_line=12, content="code")

    # Duplicate in BM25 and again in vector, plus a unique symbol
    bm25_results = [
        SearchResult(symbol=symbol, score=0.9, snippet=snippet),
        SearchResult(symbol=symbol, score=0.8, snippet=snippet),
    ]
    vector_results = [
        SearchResult(symbol=symbol, score=0.7, snippet=snippet),
        SearchResult(
            symbol=CodeSymbol(
                name="bar",
                type="function",
                file_path="test.py",
                start_line=20,
                end_line=22,
            ),
            score=0.6,
            snippet=snippet,
        ),
    ]

    fused = reciprocal_rank_fusion(bm25_results, vector_results, k=60)

    # Expect only two unique symbols despite duplicates in inputs
    assert len(fused) == 2
    names = {r.symbol.name for r in fused}
    assert names == {"foo", "bar"}


def test_query_symbols_deduplicates_results(in_memory_conn):
    """Query layer should emit unique symbols per (file,name,line,type)."""
    path = "/tmp/dup.py"
    _insert_file(in_memory_conn, path)
    # Insert duplicate rows for the same span
    in_memory_conn.execute(
        """
        INSERT INTO symbols (name, type, file_path, start_line, end_line)
        VALUES ('dup', 'function', ?, 10, 20)
        """,
        (path,),
    )
    in_memory_conn.execute(
        """
        INSERT INTO symbols (name, type, file_path, start_line, end_line)
        VALUES ('dup', 'function', ?, 10, 20)
        """,
        (path,),
    )
    in_memory_conn.commit()

    ops = SQLiteSymbolsOperations(lambda: in_memory_conn)

    symbols = list(ops.query_symbols(filter={"file_path": path}))
    # Deduped to a single symbol
    assert len(symbols) == 1
    assert symbols[0].name == "dup"
    assert symbols[0].start_line == 10


def test_blueprint_query_deduplicates_symbols(in_memory_conn):
    """Blueprint symbol fetch should not return duplicate rows for a file."""
    path = "/tmp/blueprint.py"
    _insert_file(in_memory_conn, path)
    # Duplicate symbols
    for _ in range(2):
        in_memory_conn.execute(
            """
            INSERT INTO symbols (name, type, file_path, start_line, end_line)
            VALUES ('MyClass', 'class', ?, 5, 15)
            """,
            (path,),
        )
    in_memory_conn.commit()

    generator = BlueprintGenerator(in_memory_conn, repo_path=Path("."))
    symbols = generator._query_symbols(path)

    assert len(symbols) == 1
    assert symbols[0].name == "MyClass"
