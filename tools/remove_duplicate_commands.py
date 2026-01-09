#!/usr/bin/env python3
"""
Remove duplicate commands from main.py that have been extracted to CLI modules.
Part of Phase 7 Track B de-monolithization.
"""

from pathlib import Path
from typing import List, Set

# Commands that have been extracted to CLI modules
EXTRACTED_COMMANDS = {
    # Utils commands
    "stats", "bench", "generate_tools", "summarize", "verify_context", "generate_context",
    # Retrieval commands
    "get_symbol", "search", "skeleton_file", "skeletonize_cmd", "get_context",
    # Symbolic commands
    "deps", "calls_cmd", "references_cmd", "resolution_stats_cmd",
    "inherit_tree_cmd", "descendants_cmd", "overrides_cmd", "call_graph_cmd", "smart_context_cmd",
    # Dogfood commands
    "read", "inspect", "tree", "ls", "grep",
    # Diff (to be extracted to dogfood or kept?)
    "diff",
}

# Commands to KEEP in main.py (core operational commands)
KEEP_COMMANDS = {
    "hello", "version", "doctor", "scan", "index", "update", "watcher", "session"
}

def remove_duplicate_commands():
    """Remove duplicate commands from main.py."""
    main_py = Path("src/cerberus/main.py")

    # Read main.py
    with open(main_py, 'r') as f:
        lines = f.readlines()

    # Track which lines to keep
    new_lines = []
    skip_until = None
    removed_functions = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # If we're in a skip zone, continue skipping
        if skip_until is not None:
            if i >= skip_until:
                skip_until = None
            else:
                i += 1
                continue

        # Check if this line starts a function definition to remove
        if line.startswith("def "):
            func_name = line.split("(")[0].replace("def ", "").strip()

            # Check if this function should be removed
            if func_name in EXTRACTED_COMMANDS:
                # Find the decorator before this function
                decorator_idx = i
                for j in range(i-1, max(0, i-10), -1):
                    if "@app.command" in lines[j]:
                        decorator_idx = j
                        break

                # Find the end of this function
                end_idx = None
                for j in range(i + 1, len(lines)):
                    l = lines[j]
                    stripped = l.strip()
                    if not stripped:
                        continue
                    if (l.startswith("@app.command") or
                        (l.startswith("def ") and not l.startswith("    ") and not l.startswith("\tdef")) or
                        l.startswith("if __name__")):
                        end_idx = j
                        break

                if end_idx is None:
                    end_idx = len(lines)

                print(f"Removing {func_name} (lines {decorator_idx+1}-{end_idx})")
                removed_functions.append(func_name)

                # Skip all lines from decorator to end of function
                skip_until = end_idx
                i = end_idx
                continue

        # Keep this line
        new_lines.append(line)
        i += 1

    # Write cleaned main.py
    with open(main_py, 'w') as f:
        f.writelines(new_lines)

    print(f"\nRemoved {len(removed_functions)} functions:")
    for func in sorted(removed_functions):
        print(f"  - {func}")

    print(f"\nReduced from {len(lines)} to {len(new_lines)} lines ({len(lines) - len(new_lines)} lines removed)")
    print(f"Target was ~500 lines, actual is {len(new_lines)} lines")

if __name__ == "__main__":
    remove_duplicate_commands()
