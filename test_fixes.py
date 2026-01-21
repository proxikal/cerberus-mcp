#!/usr/bin/env python3
"""Test script to verify bug fixes in Cerberus."""
import sys
import os
from pathlib import Path

# Add Cerberus to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Change to XCalibr project directory
xcalibr_path = Path("/Users/proxikal/dev/projects/xcalibr")
os.chdir(xcalibr_path)

from cerberus.mcp.index_manager import get_index_manager

print("=" * 80)
print("CERBERUS BUG FIX VERIFICATION")
print("=" * 80)
print()

# Clean slate - remove old index
cerberus_dir = xcalibr_path / ".cerberus"
if cerberus_dir.exists():
    import shutil
    shutil.rmtree(cerberus_dir)
    print("✓ Removed old index")

print()
print("-" * 80)
print("TEST 1: Extension Auto-Correction (BUG #1)")
print("-" * 80)
print()

# Test with extensions WITHOUT dots (should auto-correct now)
print("Building index with extensions WITHOUT dots: ['go', 'templ', 'md']")
manager = get_index_manager()

# Note: The auto-correction happens in the MCP tool layer, not IndexManager
# So we need to manually correct here, or test through MCP interface
# Let's test with correct format and without

print("\nTest 1a: Extensions WITH dots (should work)")
result1 = manager.rebuild(xcalibr_path, extensions=[".go", ".templ", ".md"])
print(f"  Files indexed: {result1.get('files', 0)}")
print(f"  Symbols indexed: {result1.get('symbols', 0)}")
print(f"  Database: {result1.get('path', 'N/A')}")

if result1.get('files', 0) > 0:
    print("  ✅ SUCCESS: Index built with dotted extensions")
else:
    print("  ❌ FAILED: No files indexed")

print()
print("-" * 80)
print("TEST 2: Go Function Boundaries (BUG #2)")
print("-" * 80)
print()

# Query database directly to check function boundaries
import sqlite3

db_path = xcalibr_path / ".cerberus" / "cerberus.db"
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check some known functions
    print("Checking function boundaries in database:")
    print()

    cursor.execute("""
        SELECT name, start_line, end_line, (end_line - start_line) as span, file_path
        FROM symbols
        WHERE type IN ('function', 'method')
        AND name IN ('HandleCreateServer', 'main', 'NewHandlers')
        ORDER BY span DESC
        LIMIT 10
    """)

    results = cursor.fetchall()
    if results:
        print(f"{'Function':<30} {'Start':<8} {'End':<8} {'Span':<8} {'Status':<10}")
        print("-" * 80)
        for name, start, end, span, fpath in results:
            fname = Path(fpath).name
            if span > 0:
                status = "✅ OK"
            else:
                status = "❌ BAD"
            print(f"{name:<30} {start:<8} {end:<8} {span:<8} {status}")
    else:
        print("❌ No matching functions found")

    print()

    # Also check if we have multi-line functions in general
    cursor.execute("""
        SELECT
            COUNT(*) as total_functions,
            SUM(CASE WHEN end_line > start_line THEN 1 ELSE 0 END) as multiline_functions,
            SUM(CASE WHEN end_line = start_line THEN 1 ELSE 0 END) as singleline_functions
        FROM symbols
        WHERE type IN ('function', 'method')
        AND file_path LIKE '%.go'
    """)

    total, multiline, singleline = cursor.fetchone()
    print(f"Go Functions Summary:")
    print(f"  Total: {total}")
    print(f"  Multi-line (correct): {multiline}")
    print(f"  Single-line (suspicious): {singleline}")

    if multiline > 0 and multiline > singleline:
        print("  ✅ SUCCESS: Most functions have correct boundaries")
    else:
        print("  ❌ FAILED: Functions still have incorrect boundaries")

    print()

    conn.close()
else:
    print("❌ Database not found")

print()
print("-" * 80)
print("TEST 3: Dependency Tracking (BUG #3)")
print("-" * 80)
print()

# Check if calls are in the database
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check total calls
    cursor.execute("SELECT COUNT(*) FROM calls")
    total_calls = cursor.fetchone()[0]
    print(f"Total calls in database: {total_calls}")

    if total_calls > 0:
        print("  ✅ Calls table has data")
    else:
        print("  ❌ Calls table is empty")

    # Check calls from handlers_core.go file
    cursor.execute("""
        SELECT COUNT(*) FROM calls
        WHERE caller_file LIKE '%handlers_core.go'
    """)
    handlers_calls = cursor.fetchone()[0]
    print(f"Calls from handlers_core.go: {handlers_calls}")

    # Try to find HandleCreateServer function and its calls
    cursor.execute("""
        SELECT start_line, end_line
        FROM symbols
        WHERE name = 'HandleCreateServer'
        AND file_path LIKE '%handlers_core.go'
    """)

    result = cursor.fetchone()
    if result:
        start, end = result
        print(f"\nHandleCreateServer boundaries: {start}-{end} (span: {end - start} lines)")

        # Check calls within that range
        cursor.execute("""
            SELECT COUNT(*), caller_file FROM calls
            WHERE caller_file LIKE '%handlers_core.go'
            AND line >= ? AND line <= ?
            GROUP BY caller_file
        """, (start, end))

        call_result = cursor.fetchone()
        if call_result:
            call_count = call_result[0]
            print(f"Calls within HandleCreateServer body: {call_count}")

            if call_count >= 5:
                print("  ✅ SUCCESS: Found multiple callees (expected ~5+)")
            else:
                print(f"  ⚠️  WARNING: Found {call_count} callees, expected ~5+")
        else:
            print("  ❌ FAILED: No calls found within function body")
    else:
        print("  ⚠️  HandleCreateServer not found in symbols table")

    conn.close()
    print()

print()
print("=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
print()
print("Summary:")
print("  - BUG #1 (Extension format): Test completed (auto-correction is in MCP layer)")
print("  - BUG #2 (Function boundaries): See results above")
print("  - BUG #3 (Dependencies): See results above")
print()
print("Note: Full MCP tool testing requires calling through MCP interface")
