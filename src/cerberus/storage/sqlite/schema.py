"""
SQLite Schema Definitions

Contains all table definitions, indices, triggers, and schema initialization logic.
"""

import sqlite3
from cerberus.logging_config import logger
from cerberus.exceptions import IndexCorruptionError


# SQLite schema for Cerberus index
SCHEMA_SQL = """
-- Files table
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    abs_path TEXT NOT NULL,
    size INTEGER NOT NULL,
    last_modified REAL NOT NULL,
    indexed_at REAL DEFAULT (julianday('now'))
);

CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
CREATE INDEX IF NOT EXISTS idx_files_last_modified ON files(last_modified);

-- Symbols table
CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('function', 'class', 'method', 'variable', 'interface', 'enum', 'struct', 'section')),
    file_path TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    signature TEXT,
    return_type TEXT,
    parameters TEXT,  -- JSON array serialized as TEXT
    parameter_types TEXT,  -- Phase 16.4: JSON dict {param_name: type_name}
    parent_class TEXT,

    FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_file_path ON symbols(file_path);
CREATE INDEX IF NOT EXISTS idx_symbols_type ON symbols(type);
CREATE INDEX IF NOT EXISTS idx_symbols_parent_class ON symbols(parent_class) WHERE parent_class IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_symbols_file_range ON symbols(file_path, start_line, end_line);

-- Phase 7: FTS5 virtual table for zero-RAM keyword search
-- Indexes symbol name, type, signature, and file_path using SQLite's full-text search engine
-- file_path is now indexed to support filename searches (e.g., "cli.py", "main.go")
CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
    name,
    type,
    signature,
    file_path,
    start_line UNINDEXED,
    end_line UNINDEXED,
    content='symbols',
    content_rowid='id'
);

-- Triggers to keep FTS5 table synchronized with symbols table
CREATE TRIGGER IF NOT EXISTS symbols_ai AFTER INSERT ON symbols BEGIN
    INSERT INTO symbols_fts(rowid, name, type, signature, file_path, start_line, end_line)
    VALUES (new.id, new.name, new.type, COALESCE(new.signature, ''), new.file_path, new.start_line, new.end_line);
END;

CREATE TRIGGER IF NOT EXISTS symbols_ad AFTER DELETE ON symbols BEGIN
    INSERT INTO symbols_fts(symbols_fts, rowid, name, type, signature, file_path, start_line, end_line)
    VALUES ('delete', old.id, old.name, old.type, COALESCE(old.signature, ''), old.file_path, old.start_line, old.end_line);
END;

CREATE TRIGGER IF NOT EXISTS symbols_au AFTER UPDATE ON symbols BEGIN
    INSERT INTO symbols_fts(symbols_fts, rowid, name, type, signature, file_path, start_line, end_line)
    VALUES ('delete', old.id, old.name, old.type, COALESCE(old.signature, ''), old.file_path, old.start_line, old.end_line);
    INSERT INTO symbols_fts(rowid, name, type, signature, file_path, start_line, end_line)
    VALUES (new.id, new.name, new.type, COALESCE(new.signature, ''), new.file_path, new.start_line, new.end_line);
END;

-- Embeddings metadata table (actual vectors stored in FAISS)
CREATE TABLE IF NOT EXISTS embeddings_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_id INTEGER NOT NULL UNIQUE,
    faiss_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at REAL DEFAULT (julianday('now')),

    FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embeddings_symbol_id ON embeddings_metadata(symbol_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_faiss_id ON embeddings_metadata(faiss_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_lookup ON embeddings_metadata(name, file_path);

-- Imports table
CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line INTEGER NOT NULL,

    FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_imports_file_path ON imports(file_path);
CREATE INDEX IF NOT EXISTS idx_imports_module ON imports(module);

-- Calls table
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_file TEXT NOT NULL,
    callee TEXT NOT NULL,
    line INTEGER NOT NULL,

    FOREIGN KEY (caller_file) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_calls_caller_file ON calls(caller_file);
CREATE INDEX IF NOT EXISTS idx_calls_callee ON calls(callee);
CREATE INDEX IF NOT EXISTS idx_calls_caller_line ON calls(caller_file, line);

-- Type infos table
CREATE TABLE IF NOT EXISTS type_infos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type_annotation TEXT,
    inferred_type TEXT,
    file_path TEXT NOT NULL,
    line INTEGER NOT NULL,

    FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_type_infos_file ON type_infos(file_path);
CREATE INDEX IF NOT EXISTS idx_type_infos_name ON type_infos(name);

-- Import links table
CREATE TABLE IF NOT EXISTS import_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    importer_file TEXT NOT NULL,
    imported_module TEXT NOT NULL,
    imported_symbols TEXT NOT NULL,  -- JSON array
    import_line INTEGER NOT NULL,
    definition_file TEXT,
    definition_symbol TEXT,

    FOREIGN KEY (importer_file) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_import_links_importer ON import_links(importer_file);
CREATE INDEX IF NOT EXISTS idx_import_links_module ON import_links(imported_module);
CREATE INDEX IF NOT EXISTS idx_import_links_definition ON import_links(definition_file, definition_symbol)
    WHERE definition_file IS NOT NULL;

-- Phase 5.1: Method calls table
CREATE TABLE IF NOT EXISTS method_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_file TEXT NOT NULL,
    line INTEGER NOT NULL,
    receiver TEXT NOT NULL,
    method TEXT NOT NULL,
    receiver_type TEXT,

    FOREIGN KEY (caller_file) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_method_calls_file ON method_calls(caller_file);
CREATE INDEX IF NOT EXISTS idx_method_calls_receiver ON method_calls(receiver);
CREATE INDEX IF NOT EXISTS idx_method_calls_method ON method_calls(method);
CREATE INDEX IF NOT EXISTS idx_method_calls_location ON method_calls(caller_file, line);

-- Phase 5.2+: Symbol references table
CREATE TABLE IF NOT EXISTS symbol_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    source_line INTEGER NOT NULL,
    source_symbol TEXT NOT NULL,
    reference_type TEXT NOT NULL CHECK(reference_type IN ('method_call', 'instance_of', 'inherits', 'type_annotation', 'return_type')),
    target_file TEXT,
    target_symbol TEXT,
    target_type TEXT,
    confidence REAL DEFAULT 1.0,
    resolution_method TEXT,

    FOREIGN KEY (source_file) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_symbol_refs_source ON symbol_references(source_file, source_line);
CREATE INDEX IF NOT EXISTS idx_symbol_refs_target ON symbol_references(target_file, target_symbol)
    WHERE target_file IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_symbol_refs_type ON symbol_references(reference_type);
CREATE INDEX IF NOT EXISTS idx_symbol_refs_source_symbol ON symbol_references(source_symbol);

-- Metadata table
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL DEFAULT (julianday('now'))
);

-- Phase 13.1: Blueprint cache table
CREATE TABLE IF NOT EXISTS blueprint_cache (
    cache_key TEXT PRIMARY KEY,  -- Format: file_path:mtime:flags_hash
    blueprint_json TEXT NOT NULL,  -- Serialized Blueprint object
    created_at REAL DEFAULT (julianday('now')),
    expires_at REAL NOT NULL,  -- TTL expiration timestamp
    file_path TEXT NOT NULL,  -- For easier invalidation

    FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_blueprint_cache_file ON blueprint_cache(file_path);
CREATE INDEX IF NOT EXISTS idx_blueprint_cache_expires ON blueprint_cache(expires_at);

-- Initialize schema version
INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', '1.3.0');
INSERT OR IGNORE INTO metadata (key, value) VALUES ('created_at', strftime('%s', 'now'));
"""


def init_schema(conn: sqlite3.Connection, db_path: str) -> None:
    """
    Initialize database schema if not exists.

    Args:
        conn: SQLite connection
        db_path: Path to database file (for logging)

    Raises:
        IndexCorruptionError: If schema initialization fails
    """
    try:
        conn.executescript(SCHEMA_SQL)
        _run_migrations(conn)
        logger.debug(f"Initialized SQLite schema at {db_path}")
    except Exception as e:
        raise IndexCorruptionError(f"Failed to initialize database schema: {e}")


def _run_migrations(conn: sqlite3.Connection) -> None:
    """
    Run forward-only schema/data migrations.

    - 1.2.0: purge duplicate symbols and enforce uniqueness.
    - 1.3.0: rebuild FTS5 table with file_path indexed for filename searches.
    """
    # Fetch current version (default to 1.1.0 if unset)
    cur = conn.execute("SELECT value FROM metadata WHERE key = 'schema_version'")
    row = cur.fetchone()
    current_version = row[0] if row else "1.1.0"

    # Migration to 1.2.0: remove duplicate symbols before UNIQUE index enforcement
    if current_version < "1.2.0":
        # Delete duplicate symbol rows, keeping the lowest id per unique span
        conn.execute(
            """
            DELETE FROM symbols
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM symbols
                GROUP BY file_path, name, start_line, end_line, type
            )
            """
        )
        # Enforce uniqueness going forward
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_symbols_unique
                ON symbols(file_path, name, start_line, end_line, type)
            """
        )
        conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', '1.2.0')"
        )
        conn.commit()

    # Migration to 1.3.0: rebuild FTS5 table with file_path indexed
    if current_version < "1.3.0":
        logger.info("Migrating to schema 1.3.0: rebuilding FTS5 with searchable file_path")

        # Drop old FTS5 table and triggers
        conn.execute("DROP TRIGGER IF EXISTS symbols_ai")
        conn.execute("DROP TRIGGER IF EXISTS symbols_ad")
        conn.execute("DROP TRIGGER IF EXISTS symbols_au")
        conn.execute("DROP TABLE IF EXISTS symbols_fts")

        # Create new FTS5 table with file_path indexed
        conn.execute("""
            CREATE VIRTUAL TABLE symbols_fts USING fts5(
                name,
                type,
                signature,
                file_path,
                start_line UNINDEXED,
                end_line UNINDEXED,
                content='symbols',
                content_rowid='id'
            )
        """)

        # Recreate triggers
        conn.execute("""
            CREATE TRIGGER symbols_ai AFTER INSERT ON symbols BEGIN
                INSERT INTO symbols_fts(rowid, name, type, signature, file_path, start_line, end_line)
                VALUES (new.id, new.name, new.type, COALESCE(new.signature, ''), new.file_path, new.start_line, new.end_line);
            END
        """)

        conn.execute("""
            CREATE TRIGGER symbols_ad AFTER DELETE ON symbols BEGIN
                INSERT INTO symbols_fts(symbols_fts, rowid, name, type, signature, file_path, start_line, end_line)
                VALUES ('delete', old.id, old.name, old.type, COALESCE(old.signature, ''), old.file_path, old.start_line, old.end_line);
            END
        """)

        conn.execute("""
            CREATE TRIGGER symbols_au AFTER UPDATE ON symbols BEGIN
                INSERT INTO symbols_fts(symbols_fts, rowid, name, type, signature, file_path, start_line, end_line)
                VALUES ('delete', old.id, old.name, old.type, COALESCE(old.signature, ''), old.file_path, old.start_line, old.end_line);
                INSERT INTO symbols_fts(rowid, name, type, signature, file_path, start_line, end_line)
                VALUES (new.id, new.name, new.type, COALESCE(new.signature, ''), new.file_path, new.start_line, new.end_line);
            END
        """)

        # Repopulate FTS5 table from existing symbols
        conn.execute("""
            INSERT INTO symbols_fts(rowid, name, type, signature, file_path, start_line, end_line)
            SELECT id, name, type, COALESCE(signature, ''), file_path, start_line, end_line
            FROM symbols
        """)

        conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', '1.3.0')"
        )
        conn.commit()

        logger.info("Migration to 1.3.0 complete: file_path is now searchable in FTS5")
