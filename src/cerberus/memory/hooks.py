"""
Phase 16: Integration Specification - Hook Implementation

PRIMARY MEMORY COLLECTION SYSTEM - Batch Processing at Session End

This is WHERE ALL MEMORY COLLECTION HAPPENS.

CRITICAL ARCHITECTURE:
- Session START: MCP tool `memory_context()` auto-called (injects previous memories)
- Session END: Bash hook calls `cerberus memory propose` (collects NEW memories)

Integration Flow:
1. Session starts → MCP injects previous session context (if exists)
2. During session → User works, NO automatic memory collection
3. Session ends → Bash hook triggers → propose_hook() runs:
   - Reads ENTIRE transcript file
   - Extracts semantic codes (done:, next:, impl:)
   - Detects correction patterns ("don't do X")
   - Clusters → Proposes → CLI approval → Storage

WHY BATCH PROCESSING AT END:
- ✅ Full conversation context
- ✅ Multi-turn patterns (User → AI → User correction)
- ✅ Tool results in context
- ✅ Delayed corrections (2-3 turns later)
- ✅ More accurate than real-time

SessionContextCapture is for OPTIONAL manual tracking, NOT automatic collection.
"""

import json
import os
import subprocess
import uuid
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# Language extension mapping
LANGUAGE_EXTENSIONS = {
    "python": "py",
    "javascript": "js",
    "typescript": "ts",
    "go": "go",
    "rust": "rs",
    "java": "java",
    "cpp": "cpp",
    "c": "c",
    "ruby": "rb",
    "php": "php",
}

# Hook directory mapping for different CLI tools
HOOK_DIRS = {
    "claude-code": "~/.claude/hooks",
    "codex-cli": "~/.codex/hooks",
    "gemini-cli": "~/.gemini/hooks",
}


@dataclass
class HookContext:
    """Context passed to hooks."""
    session_id: str
    working_directory: str
    git_repo: Optional[str]
    project_name: Optional[str]
    language: Optional[str]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class ProposalResult:
    """Result from propose hook."""
    proposals: List[Any]  # List[MemoryProposal]
    approved_ids: List[str]
    stored_count: int
    session_stats: Dict[str, int]  # {"candidates": 15, "clusters": 4, "proposals": 8}


# ============================================================================
# Context Detection
# ============================================================================

def detect_context() -> HookContext:
    """
    Detect session context for hook execution.

    Strategy:
    1. Get working directory (from PWD or CLI arg)
    2. Detect git repo (walk up to find .git)
    3. Infer project name (from git remote or directory name)
    4. Infer language (from file extensions in cwd)

    Returns:
        HookContext with detected values
    """
    # Working directory
    cwd = os.getcwd()

    # Git repo detection
    git_repo = _find_git_repo(cwd)

    # Project name
    if git_repo:
        # Try git remote
        try:
            remote = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=git_repo,
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
            # "git@github.com:user/project.git" → "project"
            project_name = remote.split("/")[-1].replace(".git", "")
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to directory name
            project_name = Path(git_repo).name
    else:
        project_name = Path(cwd).name

    # Language detection
    language = _detect_language(cwd)

    return HookContext(
        session_id=_generate_session_id(),
        working_directory=cwd,
        git_repo=git_repo,
        project_name=project_name,
        language=language,
        timestamp=datetime.now()
    )


def _find_git_repo(start_path: str) -> Optional[str]:
    """
    Walk up directory tree to find .git.

    Args:
        start_path: Starting directory path

    Returns:
        Path to git repo root, or None if not found
    """
    path = Path(start_path).resolve()

    while path != path.parent:
        if (path / ".git").exists():
            return str(path)
        path = path.parent

    return None


def _detect_language(cwd: str) -> Optional[str]:
    """
    Detect primary language from file extensions.

    Strategy:
    1. Count files by extension in cwd (non-recursive)
    2. Return most common extension

    Args:
        cwd: Current working directory

    Returns:
        Language name (e.g., "python", "go"), or None if not detected
    """
    extensions = Counter()

    try:
        for file in Path(cwd).iterdir():
            if file.is_file():
                ext = file.suffix.lstrip(".")
                if ext in LANGUAGE_EXTENSIONS.values():
                    extensions[ext] += 1
    except (PermissionError, OSError):
        return None

    if extensions:
        most_common_ext = extensions.most_common(1)[0][0]
        # Reverse lookup: ext → language
        for lang, ext in LANGUAGE_EXTENSIONS.items():
            if ext == most_common_ext:
                return lang

    return None


def _generate_session_id() -> str:
    """Generate unique session ID."""
    return f"session-{uuid.uuid4().hex[:12]}"


# ============================================================================
# Session Tracking (SQLite-based via session_cli module)
# ============================================================================
#
# CRITICAL: Session tracking now uses SQLite exclusively via:
# - session_cli.py: start_session(), end_session(), update_session_activity()
# - session_continuity.py: SessionContextCapture (writes to ~/.cerberus/memory.db)
#
# NO file-based tracking (.cerberus-session.json) - all data in memory.db
#
# For session operations, use:
#   from cerberus.memory.session_cli import start_session, end_session
#


# ============================================================================
# Proposal Hook (Session End)
# ============================================================================

def propose_hook(interactive: bool = True, batch_threshold: float = 0.9) -> ProposalResult:
    """
    CLI entrypoint for session end hook.

    Runs full pipeline: detect → cluster → propose → approve → store

    CRITICAL: This is called by bash hook at session end.
    MCP is shutting down, so we can't use MCP tools - only CLI.

    Args:
        interactive: Whether to use interactive CLI approval (default: True)
        batch_threshold: Auto-approval threshold for batch mode (default: 0.9)

    Returns:
        ProposalResult with statistics

    Raises:
        ImportError: If required modules are not available
        Exception: For any pipeline errors (caught by error_handling wrapper)
    """
    from cerberus.memory.session_analyzer import SessionAnalyzer
    from cerberus.memory.semantic_analyzer import SemanticAnalyzer
    from cerberus.memory.proposal_engine import ProposalEngine
    from cerberus.memory.approval_cli import ApprovalCLI
    from cerberus.memory.storage import MemoryStorage

    print("\n🧠 Analyzing session for learning opportunities...\n")

    # Save session context (work summary) to SQLite
    from cerberus.memory.session_analyzer import save_session_context_to_db
    save_session_context_to_db()

    # Phase 1: Detect corrections from transcript
    from cerberus.memory.session_analyzer import analyze_session_from_transcript
    candidates = analyze_session_from_transcript()

    if not candidates:
        print("✓ No corrections detected this session.")
        return ProposalResult(
            proposals=[],
            approved_ids=[],
            stored_count=0,
            session_stats={"candidates": 0, "clusters": 0, "proposals": 0}
        )

    print(f"✓ Detected {len(candidates)} correction(s)")

    # Phase 2: Cluster
    semantic = SemanticAnalyzer()
    analyzed = semantic.cluster_corrections(candidates)
    clusters = analyzed.clusters

    print(f"✓ Clustered into {len(clusters)} pattern(s)")

    # Phase 3: Generate proposals
    engine = ProposalEngine()
    session_summary = engine.generate_proposals(clusters)
    proposals = session_summary.proposals

    print(f"✓ Generated {len(proposals)} proposal(s)\n")

    if not proposals:
        print("✓ No proposals generated.")
        return ProposalResult(
            proposals=[],
            approved_ids=[],
            stored_count=0,
            session_stats={
                "candidates": len(candidates),
                "clusters": len(clusters),
                "proposals": 0
            }
        )

    # Phase 4/18: CLI approval (with Phase 18 optimization)
    cli = ApprovalCLI(auto_approve_threshold=batch_threshold)
    result = cli.run(proposals, interactive=interactive, optimize=True)

    # Extract approved IDs from result
    approved_ids = result.approved_ids

    # Phase 5: Store
    storage = MemoryStorage()
    approved = [p for p in proposals if p.id in approved_ids]
    storage.store_batch(approved)

    print(f"\n✓ Stored {len(approved)} memory/memories\n")

    return ProposalResult(
        proposals=proposals,
        approved_ids=approved_ids,
        stored_count=len(approved),
        session_stats={
            "candidates": len(candidates),
            "clusters": len(clusters),
            "proposals": len(proposals)
        }
    )


def propose_hook_with_error_handling(interactive: bool = True, batch_threshold: float = 0.9) -> None:
    """
    Safe proposal hook with fallback.

    Checks user config before running. If disabled, exits silently.
    If proposal fails, skip silently (don't block session end).

    Args:
        interactive: Whether to use interactive CLI approval
        batch_threshold: Auto-approval threshold for batch mode
    """
    # Check if batch memory learning is enabled in config
    try:
        from cerberus.user_config import get_user_config
        config = get_user_config()

        # Check learning mode
        learning_mode = config.get("memory.learning_mode", "batch")
        if learning_mode not in ["batch", "both"]:
            # Batch mode not enabled - exit silently
            return

        # Check if batch is explicitly disabled
        if not config.get("memory.batch.enabled", True):
            return

        # Override interactive/batch_threshold from memory config
        interactive = config.get("memory.batch.interactive", interactive)
        batch_threshold = config.get("memory.batch.threshold", batch_threshold)

        # Legacy: Also check session_hooks for backward compatibility
        if not config.get("session_hooks.enabled", True):
            return
        interactive = config.get("session_hooks.interactive", interactive)
        batch_threshold = config.get("session_hooks.batch_threshold", batch_threshold)
    except Exception as e:
        # If config fails to load, proceed with defaults
        pass

    try:
        propose_hook(interactive=interactive, batch_threshold=batch_threshold)
    except KeyboardInterrupt:
        print("\n\n✗ Memory proposal cancelled by user.")
    except Exception as e:
        # Log error
        print(f"\n✗ Memory proposal failed: {e}")
        print("  Continuing without storing memories.")


# ============================================================================
# Hook Installation
# ============================================================================

def install_hooks(cli_name: str, verbose: bool = True) -> bool:
    """
    Install session end hook for CLI tool.

    CRITICAL: Do NOT create a session-start hook.
    The agent handles startup context via MCP.
    Only session END needs bash hook (MCP shutting down).

    Args:
        cli_name: CLI tool name ("claude-code", "codex-cli", "gemini-cli")
        verbose: Print installation messages (default: True)

    Returns:
        True if installation successful, False otherwise

    Raises:
        ValueError: If cli_name is not recognized
    """
    if cli_name not in HOOK_DIRS:
        raise ValueError(
            f"Unknown CLI: {cli_name}. "
            f"Supported: {', '.join(HOOK_DIRS.keys())}"
        )

    hook_dir = Path(HOOK_DIRS[cli_name]).expanduser()

    try:
        hook_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        if verbose:
            print(f"✗ Failed to create hook directory: {e}")
        return False

    # Session end hook (only hook needed)
    end_hook = hook_dir / "session-end.sh"

    hook_content = """#!/bin/bash
# Cerberus memory proposal hook
# Runs after CLI exits (MCP shutting down)
cerberus memory propose --interactive
"""

    try:
        end_hook.write_text(hook_content)
        end_hook.chmod(0o755)
    except OSError as e:
        if verbose:
            print(f"✗ Failed to write hook file: {e}")
        return False

    if verbose:
        print(f"✓ Installed session-end hook for {cli_name}")
        print(f"  Location: {end_hook}")
        print("\n  Hook will run automatically when CLI session ends.")

    return True


def uninstall_hooks(cli_name: str, verbose: bool = True) -> bool:
    """
    Uninstall session end hook for CLI tool.

    Args:
        cli_name: CLI tool name ("claude-code", "codex-cli", "gemini-cli")
        verbose: Print uninstallation messages (default: True)

    Returns:
        True if uninstallation successful, False otherwise

    Raises:
        ValueError: If cli_name is not recognized
    """
    if cli_name not in HOOK_DIRS:
        raise ValueError(
            f"Unknown CLI: {cli_name}. "
            f"Supported: {', '.join(HOOK_DIRS.keys())}"
        )

    hook_dir = Path(HOOK_DIRS[cli_name]).expanduser()
    end_hook = hook_dir / "session-end.sh"

    if not end_hook.exists():
        if verbose:
            print(f"✓ No hook installed for {cli_name}")
        return True

    try:
        end_hook.unlink()
        if verbose:
            print(f"✓ Uninstalled session-end hook for {cli_name}")
        return True
    except OSError as e:
        if verbose:
            print(f"✗ Failed to uninstall hook: {e}")
        return False


def verify_hooks(cli_name: str) -> bool:
    """
    Verify hook installation for CLI tool.

    Args:
        cli_name: CLI tool name ("claude-code", "codex-cli", "gemini-cli")

    Returns:
        True if hooks are properly installed, False otherwise
    """
    if cli_name not in HOOK_DIRS:
        print(f"✗ Unknown CLI: {cli_name}")
        return False

    hook_dir = Path(HOOK_DIRS[cli_name]).expanduser()
    end_hook = hook_dir / "session-end.sh"

    # Check directory
    if not hook_dir.exists():
        print(f"✗ Hook directory does not exist: {hook_dir}")
        return False

    print(f"✓ Hook directory exists: {hook_dir}")

    # Check session-end hook
    if not end_hook.exists():
        print(f"✗ Session-end hook not found: {end_hook}")
        return False

    print(f"✓ Session-end hook exists: {end_hook}")

    # Check executable
    if not os.access(end_hook, os.X_OK):
        print(f"✗ Session-end hook is not executable")
        return False

    print(f"✓ Session-end hook is executable")

    # Check content
    try:
        content = end_hook.read_text()
        if "cerberus memory propose" not in content:
            print(f"✗ Session-end hook does not call 'cerberus memory propose'")
            return False
        print(f"✓ Session-end hook calls 'cerberus memory propose'")
    except OSError as e:
        print(f"✗ Failed to read hook content: {e}")
        return False

    print(f"\n✓ All hooks properly installed for {cli_name}")
    return True
