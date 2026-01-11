"""
Protocol Content (Phase 19.7)

Pre-defined protocol summaries at various detail levels.
Optimized for minimal token usage while maintaining essential rules.

Levels:
- light: ~150 tokens - Critical rules only
- rules: ~300 tokens - Tool selection + core rules
- full: ~1500 tokens - Complete CERBERUS.md reload
"""

from pathlib import Path
from typing import Optional

PROTOCOL_VERSION = "0.19.9"


def get_protocol_light() -> str:
    """
    Ultra-light protocol summary (~150 tokens).

    Critical rules only - use when context is very limited.
    """
    return """CERBERUS PROTOCOL v{version} - CRITICAL RULES

TOOL SELECTION:
  blueprint: file structure (77-95% savings)
  search: find symbols (98% savings)
  references: who calls what (90% savings)
  Direct Read: actual code for editing

FORBIDDEN: get-symbol for code retrieval (1100% overhead)
REQUIRED: --verify on all mutations
WORKFLOW: blueprint -> search -> Direct Read -> Edit

VIOLATIONS: Stop -> Acknowledge -> Redo with Cerberus -> Continue
""".format(version=PROTOCOL_VERSION)


def get_protocol_rules() -> str:
    """
    Tool selection + core rules (~300 tokens).

    Standard refresh - covers most needs.
    """
    return """CERBERUS PROTOCOL v{version} - RULES REFRESH

TOOL SELECTION TABLE:
| TASK                      | REQUIRED TOOL                     |
|---------------------------|-----------------------------------|
| Understand file structure | cerberus blueprint (77-95% save)  |
| Find symbol locations     | cerberus search (98% savings)     |
| Track who calls what      | cerberus references (90% save)    |
| Get code for editing      | Direct Read tool with line nums   |
| Edit/write code           | Direct Edit/Write tool            |
| Read .md/.txt files       | Direct Read tool (not indexed)    |
| Git/Build/Test            | Bash tool                         |

FORBIDDEN: get-symbol for code retrieval (1100% overhead)
PERMITTED: get-symbol --snippet --exact (sparingly, AST context only)

CORE RULES:
1. EXPLORE>EXTRACT: Blueprint/search for exploration, Direct Read for code
2. VERIFY_WRITES: All mutations MUST use --verify
3. STRICT_RESOLUTION: No auto-correct on mutations. Ambiguity = Error
4. MAP_FIRST: Blueprint first, THEN direct Read for specific lines
5. DEPS_CHECK: Never delete/edit referenced symbols without checking deps

VIOLATION PROTOCOL:
ON_DETECT: Stop -> Acknowledge violation -> Redo with Cerberus -> Continue
ON_ERROR: Try alt Cerberus cmd -> Report to user -> NEVER silent fallback

COMMANDS:
  cerberus go <file>           # Blueprint + read suggestions
  cerberus orient [dir]        # Project overview
  cerberus blueprint <file>    # Structure with line numbers
  cerberus search "<query>"    # Find symbols
  cerberus refresh             # This command (re-read protocol)
""".format(version=PROTOCOL_VERSION)


def get_protocol_full(cerberus_md_path: Optional[Path] = None) -> str:
    """
    Full CERBERUS.md content (~1500+ tokens).

    Complete protocol reload - use when completely lost or after compaction.

    Args:
        cerberus_md_path: Path to CERBERUS.md (auto-detected if None)
    """
    # Try to find CERBERUS.md
    if cerberus_md_path is None:
        # Check common locations
        candidates = [
            Path.cwd() / "CERBERUS.md",
            Path.cwd().parent / "CERBERUS.md",
            Path(__file__).parent.parent.parent.parent / "CERBERUS.md",
        ]
        for candidate in candidates:
            if candidate.exists():
                cerberus_md_path = candidate
                break

    if cerberus_md_path is None or not cerberus_md_path.exists():
        # Fallback to embedded summary
        return get_protocol_rules() + """

ADDITIONAL CONTEXT (CERBERUS.md not found):

ARCHITECTURE:
  Index: SQLite (symbols) + FAISS (embeddings) in .cerberus/
  Daemon: Background server for zero-latency queries
  Watcher: File system monitor, auto-reindex on changes

BLOAT PROTECTION (Phase 19.6):
  Defaults: 1MB file, 500 symbols/file, 100K total symbols
  Override: CERBERUS_MAX_TOTAL_SYMBOLS=500000 cerberus index .

WORKFLOW:
  1. cerberus start              # Initialize session
  2. cerberus orient [dir]       # Understand project
  3. cerberus go <file>          # Analyze file, get line numbers
  4. Direct Read lines X-Y       # Get actual code
  5. Direct Edit                 # Make changes
  6. cerberus mutations --verify # Verify changes

Run: cerberus refresh --full (with CERBERUS.md present) for complete protocol.
"""

    # Read and return full CERBERUS.md
    try:
        content = cerberus_md_path.read_text(encoding="utf-8")
        return f"CERBERUS PROTOCOL v{PROTOCOL_VERSION} - FULL REFRESH\n\n{content}"
    except Exception as e:
        return get_protocol_rules() + f"\n\nError reading CERBERUS.md: {e}"


def get_protocol_json() -> dict:
    """
    Protocol as structured JSON for machine parsing.

    Returns dict with tool_selection, rules, violations, commands.
    """
    return {
        "version": PROTOCOL_VERSION,
        "tool_selection": {
            "file_structure": {"command": "cerberus blueprint", "savings": "77-95%"},
            "find_symbols": {"command": "cerberus search", "savings": "98%"},
            "track_callers": {"command": "cerberus references", "savings": "90%"},
            "get_code": {"command": "Direct Read with line numbers", "savings": "N/A"},
            "edit_code": {"command": "Direct Edit/Write", "savings": "N/A"},
            "read_docs": {"command": "Direct Read (not indexed)", "savings": "N/A"},
            "git_build": {"command": "Bash tool", "savings": "N/A"},
        },
        "forbidden": [
            {"pattern": "get-symbol for code retrieval", "overhead": "1100%"},
        ],
        "core_rules": [
            "EXPLORE>EXTRACT: Blueprint/search for exploration, Direct Read for code",
            "VERIFY_WRITES: All mutations MUST use --verify",
            "STRICT_RESOLUTION: No auto-correct on mutations. Ambiguity = Error",
            "MAP_FIRST: Blueprint first, THEN direct Read for specific lines",
            "DEPS_CHECK: Never delete/edit referenced symbols without checking deps",
        ],
        "violation_protocol": {
            "on_detect": "Stop -> Acknowledge -> Redo with Cerberus -> Continue",
            "on_error": "Try alt Cerberus cmd -> Report to user -> NEVER silent fallback",
        },
        "quick_commands": [
            "cerberus go <file>",
            "cerberus orient [dir]",
            "cerberus blueprint <file>",
            "cerberus search '<query>'",
            "cerberus refresh",
        ],
    }
