"""Unit tests for SQLite storage layer.

Tests cover:
- SQLite CRUD operations
- Transaction management
- Streaming queries
"""

import pytest
from pathlib import Path

pytestmark = pytest.mark.fast

from cerberus.storage.sqlite_store import SQLiteIndexStore
from cerberus.schemas import (
    FileObject,
    CodeSymbol,
    ImportReference,
    CallReference,
    TypeInfo,
    ImportLink,
)


def test_sqlite_store_initialization(tmp_path):
    """Test database initialization with schema."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    assert store.db_path.exists()
    assert store.get_metadata('schema_version') == '1.0.0'


def test_write_and_query_files(tmp_path):
    """Test writing and querying files."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(
        path="test.py",
        abs_path="/abs/test.py",
        size=100,
        last_modified=123.456
    )

    store.write_file(file_obj)

    stats = store.get_stats()
    assert stats['total_files'] == 1


def test_write_and_query_symbols(tmp_path):
    """Test writing and streaming query of symbols."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="a.py", abs_path="/abs/a.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    symbols = [
        CodeSymbol(
            name="foo",
            type="function",
            file_path="a.py",
            start_line=1,
            end_line=10,
            signature="def foo():",
        ),
        CodeSymbol(
            name="Bar",
            type="class",
            file_path="a.py",
            start_line=15,
            end_line=30,
        ),
    ]

    store.write_symbols_batch(symbols)

    result = list(store.query_symbols())
    assert len(result) == 2
    assert result[0].name == "foo"
    assert result[1].name == "Bar"

    result = list(store.query_symbols(filter={'name': 'foo'}))
    assert len(result) == 1
    assert result[0].type == "function"

    result = list(store.query_symbols(filter={'file_path': 'a.py'}))
    assert len(result) == 2


def test_write_symbols_with_parameters(tmp_path):
    """Test symbols with parameter lists (JSON serialization)."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    symbol = CodeSymbol(
        name="func",
        type="function",
        file_path="test.py",
        start_line=1,
        end_line=10,
        parameters=["arg1", "arg2", "arg3"],
    )

    store.write_symbols_batch([symbol])

    result = list(store.query_symbols(filter={'name': 'func'}))
    assert len(result) == 1
    assert result[0].parameters == ["arg1", "arg2", "arg3"]


def test_write_and_query_imports(tmp_path):
    """Test writing and querying imports."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    imports = [
        ImportReference(module="os", file_path="test.py", line=1),
        ImportReference(module="sys", file_path="test.py", line=2),
    ]

    store.write_imports_batch(imports)

    stats = store.get_stats()
    assert stats['total_imports'] == 2


def test_write_and_query_calls(tmp_path):
    """Test writing and querying call references."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    calls = [
        CallReference(caller_file="test.py", callee="foo", line=10),
        CallReference(caller_file="test.py", callee="bar", line=20),
        CallReference(caller_file="test.py", callee="foo", line=30),
    ]

    store.write_calls_batch(calls)

    result = list(store.query_calls_by_callee("foo"))
    assert len(result) == 2
    assert all(c.callee == "foo" for c in result)

    stats = store.get_stats()
    assert stats['total_calls'] == 3


def test_write_and_query_type_infos(tmp_path):
    """Test writing and querying type information."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    type_infos = [
        TypeInfo(
            name="x",
            type_annotation="int",
            inferred_type=None,
            file_path="test.py",
            line=5
        ),
    ]

    store.write_type_infos_batch(type_infos)

    stats = store.get_stats()
    assert stats['total_type_infos'] == 1


def test_write_and_query_import_links(tmp_path):
    """Test writing and querying import links."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="main.py", abs_path="/main.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    import_links = [
        ImportLink(
            importer_file="main.py",
            imported_module="utils",
            imported_symbols=["helper", "process"],
            import_line=1,
            definition_file="utils.py",
            definition_symbol="helper",
        ),
    ]

    store.write_import_links_batch(import_links)

    result = list(store.query_import_links(filter={'importer_file': 'main.py'}))
    assert len(result) == 1
    assert result[0].imported_symbols == ["helper", "process"]

    stats = store.get_stats()
    assert stats['total_import_links'] == 1


def test_delete_file_cascade(tmp_path):
    """Test file deletion with foreign key cascade."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    symbol = CodeSymbol(
        name="func",
        type="function",
        file_path="test.py",
        start_line=1,
        end_line=10,
    )
    store.write_symbols_batch([symbol])

    call = CallReference(caller_file="test.py", callee="foo", line=5)
    store.write_calls_batch([call])

    assert store.get_stats()['total_symbols'] == 1
    assert store.get_stats()['total_calls'] == 1

    store.delete_file("test.py")

    assert store.get_stats()['total_files'] == 0
    assert store.get_stats()['total_symbols'] == 0
    assert store.get_stats()['total_calls'] == 0


def test_find_symbol_by_line(tmp_path):
    """Test finding symbol containing a specific line."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    symbols = [
        CodeSymbol(name="outer", type="class", file_path="test.py", start_line=1, end_line=50),
        CodeSymbol(name="inner", type="method", file_path="test.py", start_line=10, end_line=20),
    ]
    store.write_symbols_batch(symbols)

    result = store.find_symbol_by_line("test.py", 15)
    assert result is not None
    assert result.name == "inner"

    result = store.find_symbol_by_line("test.py", 30)
    assert result is not None
    assert result.name == "outer"

    result = store.find_symbol_by_line("test.py", 100)
    assert result is None


def test_transaction_commit(tmp_path):
    """Test transaction commit on success."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    symbol = CodeSymbol(name="func", type="function", file_path="test.py", start_line=1, end_line=10)

    with store.transaction() as conn:
        store.write_file(file_obj, conn=conn)
        store.write_symbols_batch([symbol], conn=conn)

    assert store.get_stats()['total_files'] == 1
    assert store.get_stats()['total_symbols'] == 1


def test_transaction_rollback(tmp_path):
    """Test transaction rollback on exception."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)

    try:
        with store.transaction() as conn:
            store.write_file(file_obj, conn=conn)
            raise ValueError("Forced error")
    except ValueError:
        pass

    assert store.get_stats()['total_files'] == 0


def test_metadata_operations(tmp_path):
    """Test metadata get/set operations."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    store.set_metadata('project_root', '/path/to/project')
    store.set_metadata('git_commit', 'abc123')

    assert store.get_metadata('project_root') == '/path/to/project'
    assert store.get_metadata('git_commit') == 'abc123'

    assert store.get_metadata('nonexistent') is None

    store.set_metadata('git_commit', 'def456')
    assert store.get_metadata('git_commit') == 'def456'


def test_get_stats(tmp_path):
    """Test comprehensive stats reporting."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    symbol = CodeSymbol(name="func", type="function", file_path="test.py", start_line=1, end_line=10)
    store.write_symbols_batch([symbol])

    stats = store.get_stats()

    assert stats['total_files'] == 1
    assert stats['total_symbols'] == 1
    assert stats['total_embeddings'] == 0
    assert stats['total_calls'] == 0
    assert stats['total_imports'] == 0
    assert stats['total_type_infos'] == 0
    assert stats['total_import_links'] == 0
    assert stats['db_size_bytes'] > 0


def test_streaming_batch_size(tmp_path):
    """Test streaming queries with different batch sizes."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    symbols = [
        CodeSymbol(name=f"func_{i}", type="function", file_path="test.py", start_line=i, end_line=i+1)
        for i in range(50)
    ]
    store.write_symbols_batch(symbols)

    result = list(store.query_symbols(batch_size=10))
    assert len(result) == 50

    result = list(store.query_symbols(batch_size=100))
    assert len(result) == 50
