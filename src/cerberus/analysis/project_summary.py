"""
Project Onboarding Summary Generator.

Generates comprehensive project overviews for AI agents starting new sessions.
Aims for 80/20 value in ~800 tokens instead of 5,000+ token exploration.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import re
import subprocess


@dataclass
class ProjectSummary:
    """Complete project summary for AI agent onboarding."""

    tech_stack: List[str] = field(default_factory=list)
    architecture: str = ""
    key_modules: Dict[str, str] = field(default_factory=dict)
    entry_points: List[str] = field(default_factory=list)
    coding_patterns: List[str] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    testing_approach: str = ""
    project_type: str = ""
    token_estimate: int = 800

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tech_stack": self.tech_stack,
            "architecture": self.architecture,
            "key_modules": self.key_modules,
            "entry_points": self.entry_points,
            "coding_patterns": self.coding_patterns,
            "dependencies": self.dependencies,
            "testing_approach": self.testing_approach,
            "project_type": self.project_type,
            "token_estimate": self.token_estimate,
        }


class ProjectSummaryAnalyzer:
    """
    Analyzes project structure and generates onboarding summaries.

    Uses existing index + file system analysis to build a comprehensive
    but token-efficient project overview.
    """

    def __init__(self, project_root: Path, store: Optional[Any] = None):
        """
        Initialize analyzer.

        Args:
            project_root: Root directory of project
            store: Optional SQLite store (will detect if not provided)
        """
        self.project_root = Path(project_root)
        self.store = store

    def generate_summary(self) -> ProjectSummary:
        """
        Generate complete project summary.

        Returns:
            ProjectSummary with all fields populated
        """
        summary = ProjectSummary()

        # Detect tech stack
        summary.tech_stack = self._detect_tech_stack()

        # Detect project type
        summary.project_type = self._detect_project_type()

        # Analyze architecture
        summary.architecture = self._infer_architecture()

        # Map key modules
        summary.key_modules = self._map_key_modules()

        # Find entry points
        summary.entry_points = self._find_entry_points()

        # Extract coding patterns
        summary.coding_patterns = self._extract_coding_patterns()

        # Parse dependencies
        summary.dependencies = self._parse_dependencies()

        # Detect testing approach
        summary.testing_approach = self._detect_testing_approach()

        return summary

    def _detect_tech_stack(self) -> List[str]:
        """Detect technologies used in project."""
        stack = []

        # Check for Python version
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            # Extract Python version
            if match := re.search(r'python\s*=\s*["\']([^"\']+)["\']', content):
                stack.append(f"Python {match.group(1)}")
            elif match := re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', content):
                stack.append(f"Python {match.group(1)}")

        # Check for common frameworks/libraries
        requirements_files = [
            self.project_root / "requirements.txt",
            self.project_root / "pyproject.toml",
        ]

        key_packages = {
            "fastapi": "FastAPI",
            "django": "Django",
            "flask": "Flask",
            "fastmcp": "FastMCP",
            "anthropic": "Anthropic SDK",
            "openai": "OpenAI SDK",
            "pytest": "pytest",
            "sqlalchemy": "SQLAlchemy",
            "tree-sitter": "Tree-sitter",
        }

        for req_file in requirements_files:
            if req_file.exists():
                content = req_file.read_text().lower()
                for pkg, name in key_packages.items():
                    if pkg in content and name not in stack:
                        stack.append(name)

        # Check for databases
        if (self.project_root / "*.db").exists() or "sqlite" in str(self.project_root):
            if "SQLite" not in stack:
                stack.append("SQLite")

        return stack

    def _detect_project_type(self) -> str:
        """Detect the type of project."""
        # Check for common project indicators
        if (self.project_root / "pyproject.toml").exists():
            content = (self.project_root / "pyproject.toml").read_text()
            if "fastmcp" in content.lower():
                return "MCP Server"
            elif "fastapi" in content.lower():
                return "FastAPI Application"
            elif "django" in content.lower():
                return "Django Application"
            elif "flask" in content.lower():
                return "Flask Application"
            elif "[tool.poetry]" in content:
                return "Python Library"

        if (self.project_root / "setup.py").exists():
            return "Python Package"

        return "Python Project"

    def _infer_architecture(self) -> str:
        """Infer project architecture from structure."""
        # Check common architecture patterns
        directories = [d.name for d in self.project_root.glob("*") if d.is_dir()]

        if "mcp" in directories or "server" in directories:
            return "MCP server with pluggable tools"
        elif "api" in directories and "models" in directories:
            return "REST API with models and routes"
        elif "app" in directories and "templates" in directories:
            return "Web application with template rendering"
        elif "cli" in directories:
            return "Command-line interface application"
        elif "lib" in directories or "src" in directories:
            return "Library with modular components"

        return "Modular Python application"

    def _map_key_modules(self) -> Dict[str, str]:
        """Map key modules to their purposes."""
        modules = {}

        # Scan src/ or lib/ directories
        src_dirs = [
            self.project_root / "src",
            self.project_root / "lib",
            self.project_root,
        ]

        for src_dir in src_dirs:
            if not src_dir.exists():
                continue

            # Find main package directories
            for item in src_dir.iterdir():
                if not item.is_dir() or item.name.startswith((".", "_")):
                    continue

                # Skip common non-code directories
                if item.name in ("tests", "docs", "scripts", "tools", "build", "dist"):
                    continue

                # Infer purpose from directory name and contents
                purpose = self._infer_module_purpose(item)
                if purpose:
                    modules[f"{item.name}/"] = purpose

        return modules

    def _infer_module_purpose(self, module_dir: Path) -> str:
        """Infer the purpose of a module from its name and contents."""
        name = module_dir.name.lower()

        # Common module purpose patterns
        purpose_map = {
            "api": "REST API endpoints and routes",
            "cli": "Command-line interface",
            "mcp": "MCP server and tool implementations",
            "server": "Server implementation",
            "client": "Client library",
            "models": "Data models and schemas",
            "database": "Database layer",
            "db": "Database layer",
            "storage": "Data storage and persistence",
            "retrieval": "Symbol search and indexing",
            "search": "Search functionality",
            "index": "Indexing system",
            "parser": "Code parsing",
            "scanner": "File scanning",
            "analysis": "Code analysis",
            "blueprint": "Code structure visualization",
            "memory": "Session context management",
            "metrics": "Efficiency tracking",
            "utils": "Utility functions",
            "helpers": "Helper functions",
            "core": "Core business logic",
            "services": "Business services",
            "controllers": "Request controllers",
            "views": "View rendering",
            "templates": "Template files",
            "static": "Static assets",
            "tests": "Test suite",
            "docs": "Documentation",
        }

        if name in purpose_map:
            return purpose_map[name]

        # Check if it contains specific indicators
        init_file = module_dir / "__init__.py"
        if init_file.exists():
            content = init_file.read_text()
            # Check for docstrings
            if match := re.search(r'"""([^"]+)"""', content):
                doc = match.group(1).strip()
                if doc and len(doc) < 100:
                    return doc

        return "Module"

    def _find_entry_points(self) -> List[str]:
        """Find main entry points of the application."""
        entry_points = []

        # Common entry point patterns
        entry_patterns = [
            ("**/main.py", "main"),
            ("**/server.py", "create_server"),
            ("**/server.py", "start_server"),
            ("**/app.py", "create_app"),
            ("**/__main__.py", "main"),
            ("**/cli.py", "cli"),
            ("**/cli.py", "main"),
        ]

        for pattern, func_name in entry_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    # Check if function exists
                    content = file_path.read_text()
                    if f"def {func_name}" in content or f"async def {func_name}" in content:
                        # Make path relative
                        rel_path = file_path.relative_to(self.project_root)
                        entry_points.append(f"{rel_path}::{func_name}")

        return entry_points[:5]  # Limit to top 5

    def _extract_coding_patterns(self) -> List[str]:
        """Extract common coding patterns from the codebase."""
        patterns = []

        # Check for dataclass usage
        if self._check_pattern(r'@dataclass'):
            patterns.append("Use dataclasses for data structures")

        # Check for async/await
        if self._check_pattern(r'async def'):
            patterns.append("Async/await for I/O operations")

        # Check for type hints
        if self._check_pattern(r'def \w+\([^)]*:\s*\w+'):
            patterns.append("Type hints required on functions")

        # Check for docstring style
        py_files = list(self.project_root.glob("**/*.py"))
        if py_files:
            sample_file = py_files[0]
            content = sample_file.read_text()
            if '"""' in content and "Args:" in content:
                patterns.append("Docstrings use Google style")
            elif '"""' in content and ":param" in content:
                patterns.append("Docstrings use Sphinx style")

        # Check for error handling
        if self._check_pattern(r'try:'):
            patterns.append("Use try/except for error handling")

        return patterns[:7]  # Limit to top 7

    def _check_pattern(self, regex: str) -> bool:
        """Check if a pattern exists in Python files."""
        for py_file in self.project_root.glob("**/*.py"):
            if py_file.is_file():
                try:
                    content = py_file.read_text()
                    if re.search(regex, content):
                        return True
                except:
                    continue
        return False

    def _parse_dependencies(self) -> Dict[str, List[str]]:
        """Parse project dependencies."""
        deps = {"core": [], "dev": [], "optional": []}

        # Parse pyproject.toml
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()

            # Extract dependencies section
            if match := re.search(r'\[project\.dependencies\](.*?)(?:\[|$)', content, re.DOTALL):
                dep_section = match.group(1)
                # Extract package names
                for line in dep_section.split('\n'):
                    line = line.strip().strip(',').strip('"\'')
                    if line and not line.startswith('#'):
                        pkg = line.split('=')[0].split('>')[0].split('<')[0].strip()
                        if pkg:
                            deps["core"].append(pkg)

            # Extract optional dependencies
            if "optional-dependencies" in content:
                if match := re.search(r'\[project\.optional-dependencies\](.*?)(?:\[|$)', content, re.DOTALL):
                    opt_section = match.group(1)
                    for line in opt_section.split('\n'):
                        line = line.strip().strip(',').strip('"\'')
                        if line and not line.startswith(('#', '[')):
                            pkg = line.split('=')[0].split('>')[0].split('<')[0].strip()
                            if pkg:
                                deps["optional"].append(pkg)

        # Parse requirements.txt
        requirements = self.project_root / "requirements.txt"
        if requirements.exists() and not deps["core"]:
            for line in requirements.read_text().split('\n'):
                line = line.strip().split('#')[0].strip()
                if line:
                    pkg = line.split('=')[0].split('>')[0].split('<')[0].strip()
                    deps["core"].append(pkg)

        # Limit to top packages
        deps["core"] = deps["core"][:10]
        deps["optional"] = deps["optional"][:5]

        return deps

    def _detect_testing_approach(self) -> str:
        """Detect testing framework and approach."""
        # Check for pytest
        if (self.project_root / "pytest.ini").exists() or \
           (self.project_root / "pyproject.toml").exists() and "pytest" in (self.project_root / "pyproject.toml").read_text():

            # Check for conftest
            if (self.project_root / "tests" / "conftest.py").exists() or \
               (self.project_root / "conftest.py").exists():
                return "pytest with fixtures in conftest.py"
            return "pytest"

        # Check for unittest
        test_files = list(self.project_root.glob("**/test_*.py"))
        if test_files:
            sample = test_files[0].read_text()
            if "import unittest" in sample:
                return "unittest"

        return "No testing framework detected"


def generate_project_summary(project_root: Path, store: Optional[Any] = None) -> ProjectSummary:
    """
    Convenience function to generate project summary.

    Args:
        project_root: Root directory of project
        store: Optional SQLite store

    Returns:
        ProjectSummary object
    """
    analyzer = ProjectSummaryAnalyzer(project_root, store)
    return analyzer.generate_summary()
