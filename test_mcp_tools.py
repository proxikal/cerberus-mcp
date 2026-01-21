#!/usr/bin/env python3
"""Test MCP tools to verify bug fixes work end-to-end."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Change to XCalibr directory
import os
os.chdir("/Users/proxikal/dev/projects/xcalibr")

# Import the underlying functions that power the MCP tools
from cerberus.mcp.index_manager import get_index_manager
from cerberus.storage.sqlite.symbols import SQLiteSymbolStorage
from cerberus.resolution.context_assembler import ContextAssembler
from cerberus.resolution.call_graph_builder import CallGraphBuilder

print("=" * 80)
print("MCP TOOLS VERIFICATION")
print("=" * 80)
print()

# Get manager and storage
manager = get_index_manager()
storage = SQLiteSymbolStorage(Path("/Users/proxikal/dev/projects/xcalibr/.cerberus/cerberus.db"))

print("-" * 80)
print("TEST: get_symbol() equivalent - Retrieve HandleCreateServer")
print("-" * 80)
print()

# Search for the symbol
results = storage.search_symbols("HandleCreateServer", limit=5)
if results:
    symbol = results[0]
    print(f"Found: {symbol['name']} in {Path(symbol['file_path']).name}")
    print(f"Lines: {symbol['start_line']}-{symbol['end_line']} (span: {symbol['end_line'] - symbol['start_line']})")
    print(f"Type: {symbol['type']}")

    # Read the actual code
    file_path = Path(symbol['file_path'])
    if file_path.exists():
        with open(file_path, 'r') as f:
            lines = f.readlines()
            start_idx = symbol['start_line'] - 1
            end_idx = symbol['end_line']
            code_lines = lines[start_idx:end_idx]
            line_count = len(code_lines)

            print(f"\nCode retrieved: {line_count} lines")
            print(f"First 5 lines:")
            for i, line in enumerate(code_lines[:5], start=symbol['start_line']):
                print(f"  {i:4d}: {line.rstrip()}")
            print(f"  ...")
            print(f"Last 2 lines:")
            for i, line in enumerate(code_lines[-2:], start=symbol['end_line']-1):
                print(f"  {i:4d}: {line.rstrip()}")

            if line_count >= 20:
                print(f"\n✅ SUCCESS: Retrieved full function body ({line_count} lines)")
            else:
                print(f"\n⚠️  WARNING: Retrieved {line_count} lines (expected ~26)")
    else:
        print(f"❌ File not found: {file_path}")
else:
    print("❌ Symbol not found")

print()
print("-" * 80)
print("TEST: deps() equivalent - Get dependencies for HandleCreateServer")
print("-" * 80)
print()

# Build call graph to get dependencies
builder = CallGraphBuilder(storage)

try:
    # Get the symbol info first
    results = storage.search_symbols("HandleCreateServer", limit=1)
    if results:
        symbol = results[0]
        abs_file = str(Path(symbol['file_path']).resolve())

        # Get callees (what this function calls)
        graph = builder.build_graph(
            root_symbol=symbol['name'],
            root_file=abs_file,
            depth=1,
            direction='forward'
        )

        callees = [edge['target'] for edge in graph.get('edges', [])]

        print(f"Symbol: {symbol['name']}")
        print(f"File: {Path(abs_file).name}")
        print(f"Callees found: {len(callees)}")

        if callees:
            print("\nFunctions called by HandleCreateServer:")
            for callee in callees[:10]:  # Show first 10
                print(f"  - {callee}")
            if len(callees) > 10:
                print(f"  ... and {len(callees) - 10} more")

            if len(callees) >= 5:
                print(f"\n✅ SUCCESS: Found {len(callees)} callees (expected ~5+)")
            else:
                print(f"\n⚠️  WARNING: Found {len(callees)} callees (expected ~5+)")
        else:
            print("\n❌ FAILED: No callees found")
    else:
        print("❌ Symbol not found")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("-" * 80)
print("TEST: call_graph() equivalent - Build call graph")
print("-" * 80)
print()

try:
    results = storage.search_symbols("HandleCreateServer", limit=1)
    if results:
        symbol = results[0]
        abs_file = str(Path(symbol['file_path']).resolve())

        # Build both forward and reverse graphs
        forward_graph = builder.build_graph(
            root_symbol=symbol['name'],
            root_file=abs_file,
            depth=1,
            direction='forward'
        )

        reverse_graph = builder.build_graph(
            root_symbol=symbol['name'],
            root_file=abs_file,
            depth=1,
            direction='reverse'
        )

        print("Forward graph (callees - what HandleCreateServer calls):")
        print(f"  Nodes: {len(forward_graph.get('nodes', []))}")
        print(f"  Edges: {len(forward_graph.get('edges', []))}")

        print("\nReverse graph (callers - what calls HandleCreateServer):")
        print(f"  Nodes: {len(reverse_graph.get('nodes', []))}")
        print(f"  Edges: {len(reverse_graph.get('edges', []))}")

        total_edges = len(forward_graph.get('edges', [])) + len(reverse_graph.get('edges', []))

        if total_edges > 0:
            print(f"\n✅ SUCCESS: Call graph has {total_edges} total edges")

            # Show some edges
            if forward_graph.get('edges'):
                print("\nSample forward edges:")
                for edge in forward_graph['edges'][:5]:
                    print(f"  {edge['source']} → {edge['target']}")
        else:
            print("\n❌ FAILED: Call graph has no edges")
    else:
        print("❌ Symbol not found")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("-" * 80)
print("TEST: context() equivalent - Assemble full context")
print("-" * 80)
print()

try:
    assembler = ContextAssembler(storage)

    results = storage.search_symbols("HandleCreateServer", limit=1)
    if results:
        symbol = results[0]

        # Assemble context (this is what the context() tool does)
        result = assembler.assemble_context(
            symbol_name=symbol['name'],
            file_path=symbol['file_path'],
            include_bases=True,
            include_deps=True,
            include_callers=True,
            include_callees=True
        )

        if result.get('status') == 'ok':
            target = result.get('target_symbol', {})
            print(f"Symbol: {target.get('name')}")
            print(f"Type: {target.get('type')}")

            code = target.get('code', '')
            code_lines = code.count('\n') + 1 if code else 0
            print(f"Code lines: {code_lines}")

            deps = result.get('dependencies', {})
            bases = deps.get('bases', [])
            callees = deps.get('callees', [])
            callers = deps.get('callers', [])

            print(f"\nDependencies:")
            print(f"  Base classes: {len(bases)}")
            print(f"  Callees: {len(callees)}")
            print(f"  Callers: {len(callers)}")

            if code_lines >= 20 and len(callees) >= 5:
                print(f"\n✅ SUCCESS: Context assembled with full code and dependencies")
            else:
                print(f"\n⚠️  PARTIAL: Code={code_lines} lines, Callees={len(callees)}")
        else:
            print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
    else:
        print("❌ Symbol not found")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("MCP TOOLS VERIFICATION COMPLETE")
print("=" * 80)
