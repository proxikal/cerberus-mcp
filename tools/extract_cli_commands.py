#!/usr/bin/env python3
"""
Extract CLI commands from main.py to modular CLI files.
Part of Phase 7 Track B de-monolithization.
"""

import re
from pathlib import Path
from typing import List, Tuple

# Command mappings: module -> list of (command_name, decorator_name)
COMMAND_MAP = {
    "retrieval": [
        ("get_symbol", "get-symbol"),
        ("search", "search"),
        ("skeleton_file", "skeleton-file"),
        ("skeletonize_cmd", "skeletonize"),
        ("get_context", "get-context"),
    ],
    "symbolic": [
        ("deps", "deps"),
        ("calls_cmd", "calls"),
        ("references_cmd", "references"),
        ("resolution_stats_cmd", "resolution-stats"),
        ("inherit_tree_cmd", "inherit-tree"),
        ("descendants_cmd", "descendants"),
        ("overrides_cmd", "overrides"),
        ("call_graph_cmd", "call-graph"),
        ("smart_context_cmd", "smart-context"),
    ],
    "dogfood": [
        ("read", "read"),
        ("inspect", "inspect"),
        ("tree", "tree"),
        ("ls", "ls"),
        ("grep", "grep"),
    ],
}

def find_function_bounds(lines: List[str], func_name: str) -> Tuple[int, int]:
    """Find start and end line indices for a function."""
    start_idx = None
    func_def_idx = None

    # Find function definition
    for i, line in enumerate(lines):
        if f"def {func_name}(" in line:
            func_def_idx = i
            # Look backwards for @app.command decorator
            for j in range(i-1, max(0, i-10), -1):
                if "@app.command" in lines[j]:
                    start_idx = j
                    break
            if start_idx is None:
                start_idx = i
            break

    if start_idx is None or func_def_idx is None:
        return None, None

    # Find end of function: look for next @app.command, top-level def, or if __name__
    end_idx = len(lines)
    for i in range(func_def_idx + 1, len(lines)):
        line = lines[i]
        stripped = line.strip()

        # Skip blank lines
        if not stripped:
            continue

        # Function ends at next decorator, top-level function, or if __name__
        if (line.startswith("@app.command") or
            (line.startswith("def ") and not line.startswith("    ") and not line.startswith("\tdef")) or
            line.startswith("if __name__")):
            end_idx = i
            break

    return start_idx, end_idx

def extract_commands():
    """Extract commands from main.py to CLI modules."""
    main_py = Path("src/cerberus/main.py")
    cli_dir = Path("src/cerberus/cli")

    # Read main.py
    with open(main_py, 'r') as f:
        main_lines = f.readlines()

    # Common imports needed by all CLI modules
    common_imports = """import json
import typer
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.markup import escape

from cerberus.logging_config import logger
from cerberus.agent_session import record_operation
from cerberus.index import (
    load_index,
    find_symbol,
    read_range,
    semantic_search,
)

app = typer.Typer()
console = Console()

"""

    # Extract commands for each module
    for module_name, commands in COMMAND_MAP.items():
        print(f"Processing {module_name}.py...")

        module_file = cli_dir / f"{module_name}.py"
        extracted_functions = []

        for func_name, decorator_name in commands:
            print(f"  Extracting {func_name}...")
            start, end = find_function_bounds(main_lines, func_name)

            if start is None:
                print(f"    WARNING: Could not find {func_name}")
                continue

            # Extract function code
            func_code = ''.join(main_lines[start:end])
            extracted_functions.append(func_code)
            print(f"    Found at lines {start+1}-{end} ({end-start} lines)")

        if not extracted_functions:
            print(f"  No functions extracted for {module_name}")
            continue

        # Build module content
        docstring = f'''"""
CLI {module_name.title()} Commands

{", ".join([cmd[1] for cmd in commands])}
"""

'''

        module_content = docstring + common_imports + "\n\n".join(extracted_functions)

        # Write to file
        with open(module_file, 'w') as f:
            f.write(module_content)

        print(f"  Wrote {len(extracted_functions)} commands to {module_file}")

    print("\nExtraction complete!")
    print("Next step: Integrate the modules in main.py and remove duplicates.")

if __name__ == "__main__":
    extract_commands()
