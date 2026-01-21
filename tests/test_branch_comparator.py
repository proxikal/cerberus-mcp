"""
Tests for cross-branch symbol comparison.
"""

from pathlib import Path
import subprocess

from cerberus.analysis.branch_comparator import BranchComparator
from cerberus.index import build_index


def _run_git(repo: Path, *args: str) -> None:
    """Run a git command with basic config applied."""
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _init_repo(repo: Path) -> None:
    """Initialize a git repo with default user config."""
    init = subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if init.returncode != 0:
        _run_git(repo, "init")
        _run_git(repo, "checkout", "-b", "main")

    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test User")


def _build_index(repo: Path):
    """Build an index for the given repo path."""
    index_path = repo / "index.db"
    return build_index(repo, index_path)


def _write(repo: Path, relative: str, content: str) -> Path:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n")
    return path


def test_symbol_mapping(temp_dir):
    """Line ranges map to modified and added symbols."""
    repo = temp_dir / "branch_compare_repo"
    repo.mkdir()
    _init_repo(repo)

    _write(
        repo,
        "app.py",
        """
def login():
    return "ok"

def logout():
    return "bye"
        """,
    )
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "initial")

    _run_git(repo, "checkout", "-b", "feature/auth")
    _write(
        repo,
        "app.py",
        """
def login():
    updated = True
    return "changed" if updated else "ok"

def logout():
    return "bye"

def register(user):
    return f"registered {user}"
        """,
    )
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "feature changes")

    index = _build_index(repo)
    comparator = BranchComparator(repo, index)

    result = comparator.compare("main", "feature/auth")
    assert result.status == "success"

    changes_by_file = {c["file"]: c for c in result.changes}
    app_change = changes_by_file["app.py"]
    symbol_names = {s["name"]: s for s in app_change["symbols_changed"]}

    assert symbol_names["login"]["change_type"] == "modified"
    assert symbol_names["register"]["change_type"] == "added"
    assert result.symbols_changed >= 2


def test_focus_filtering(temp_dir):
    """Focus parameter filters to matching symbol."""
    repo = temp_dir / "branch_compare_focus"
    repo.mkdir()
    _init_repo(repo)

    _write(
        repo,
        "module.py",
        """
def alpha():
    return "a"

def beta():
    return "b"
        """,
    )
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "base")

    _run_git(repo, "checkout", "-b", "feature/focus")
    _write(
        repo,
        "module.py",
        """
def alpha():
    return "alpha updated"

def beta():
    return "b"

def gamma():
    return "g"
        """,
    )
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "update with gamma")

    index = _build_index(repo)
    comparator = BranchComparator(repo, index)

    filtered = comparator.compare("main", "feature/focus", focus="gamma")

    assert filtered.status == "success"
    assert filtered.files_changed == 1
    assert filtered.symbols_changed == 1
    assert filtered.available_symbols and filtered.available_symbols >= 2

    module_change = filtered.changes[0]
    assert module_change["symbols_changed"][0]["name"] == "gamma"


def test_risk_assessment_for_critical_paths(temp_dir):
    """Critical modules with many symbols are marked high risk."""
    repo = temp_dir / "branch_compare_risk"
    repo.mkdir()
    _init_repo(repo)

    _write(
        repo,
        "core/main.py",
        """
def one():
    return 1

def two():
    return 2

def three():
    return 3

def four():
    return 4

def five():
    return 5

def six():
    return 6
        """,
    )
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "initial core")

    _run_git(repo, "checkout", "-b", "feature/risk")
    _write(
        repo,
        "core/main.py",
        """
def one():
    return 101

def two():
    return 102

def three():
    return 103

def four():
    return 104

def five():
    return 105

def six():
    return 106
        """,
    )
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "modify core functions")

    index = _build_index(repo)
    comparator = BranchComparator(repo, index)

    result = comparator.compare("main", "feature/risk")

    assert result.status == "success"
    assert result.risk_assessment == "high"
    assert result.symbols_changed >= 6


def test_file_renames_are_reported(temp_dir):
    """Renamed files include old_path and symbol changes."""
    repo = temp_dir / "branch_compare_rename"
    repo.mkdir()
    _init_repo(repo)

    _write(
        repo,
        "legacy.py",
        """
def do_work():
    return "legacy"
        """,
    )
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "legacy commit")

    _run_git(repo, "checkout", "-b", "feature/rename")
    _run_git(repo, "mv", "legacy.py", "modern.py")
    _write(
        repo,
        "modern.py",
        """
def do_work():
    return "modernized"
        """,
    )
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "rename and update")

    index = _build_index(repo)
    comparator = BranchComparator(repo, index)

    result = comparator.compare("main", "feature/rename")
    assert result.status == "success"

    change = result.changes[0]
    assert change["file"] == "modern.py"
    assert change.get("old_path") == "legacy.py"
    assert change["change_type"] == "renamed"
    assert change["symbols_changed"][0]["change_type"] == "renamed"
