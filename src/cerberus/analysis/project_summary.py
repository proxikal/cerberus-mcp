"""
Project Onboarding Summary Generator.

Generates comprehensive project overviews for AI agents starting new sessions.
Aims for 80/20 value in ~800 tokens instead of 5,000+ token exploration.
"""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import re
import subprocess

PROJECT_MARKERS = {
    "go": ["go.mod", "go.sum"],
    "javascript": ["package.json", "node_modules"],
    "typescript": ["tsconfig.json", "package.json"],
    "rust": ["Cargo.toml", "Cargo.lock"],
    "python": ["pyproject.toml", "setup.py", "requirements.txt"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "csharp": [".csproj", ".sln"],
    "php": ["composer.json"],
    "ruby": ["Gemfile", "Gemfile.lock"],
}

EXTENSION_TO_LANGUAGE = {
    ".go": "go",
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".rs": "rust",
    ".java": "java",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
}

ENTRY_POINT_PATTERNS = {
    "go": ["main.go", "cmd/*/main.go", "*/main.go"],
    "python": ["main.py", "__main__.py", "cli.py", "app.py"],
    "javascript": ["index.js", "main.js", "app.js", "server.js"],
    "typescript": ["index.ts", "main.ts", "app.ts", "server.ts"],
    "rust": ["main.rs", "lib.rs"],
    "java": ["Main.java", "Application.java"],
}


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

    def _detect_languages(self) -> List[str]:
        """Detect languages present using markers and file extensions."""
        counts = Counter()
        counts.update(self._detect_languages_by_markers())
        counts.update(self._detect_languages_by_files())

        if not counts:
            return []

        languages = [lang for lang, _ in counts.most_common()]

        if "typescript" in languages and "javascript" in languages:
            languages = [lang for lang in languages if lang != "javascript"]

        return languages

    def _detect_languages_by_markers(self) -> Dict[str, int]:
        """Detect languages based on project marker files."""
        markers: Dict[str, int] = {}

        for language, files in PROJECT_MARKERS.items():
            for marker in files:
                if (self.project_root / marker).exists():
                    markers[language] = markers.get(language, 0) + 1

        return markers

    def _detect_languages_by_files(self) -> Dict[str, int]:
        """Count files by extension to infer languages."""
        counts: Dict[str, int] = {}

        for ext, language in EXTENSION_TO_LANGUAGE.items():
            matches = list(self.project_root.rglob(f"*{ext}"))
            if matches:
                counts[language] = counts.get(language, 0) + len(matches)

        return counts

    def _detect_tech_stack(self) -> List[str]:
        """Detect technologies used in project."""
        stack = []

        languages = self._detect_languages()
        if not languages:
            return stack

        for language in languages:
            if language == "python":
                stack.extend(self._detect_python_stack())
            elif language == "go":
                stack.extend(self._detect_go_stack())
            elif language in ("javascript", "typescript"):
                stack.extend(self._detect_js_stack())
            elif language == "rust":
                stack.extend(self._detect_rust_stack())
            elif language == "java":
                stack.extend(self._detect_java_stack())

        seen = set()
        deduped = []
        for item in stack:
            if item not in seen:
                deduped.append(item)
                seen.add(item)

        return deduped

    def _detect_python_stack(self) -> List[str]:
        """Detect Python-specific technologies."""
        stack = []
        pyproject = self.project_root / "pyproject.toml"

        if pyproject.exists():
            content = pyproject.read_text()
            if match := re.search(r'python\s*=\s*["\']([^"\']+)["\']', content):
                stack.append(f"Python {match.group(1)}")
            elif match := re.search(
                r'requires-python\s*=\s*["\']([^"\']+)["\']', content
            ):
                stack.append(f"Python {match.group(1)}")

        requirements_files = [
            self.project_root / "requirements.txt",
            pyproject,
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

        db_files = list(self.project_root.glob("*.db"))
        if db_files and "SQLite" not in stack:
            stack.append("SQLite")

        return stack

    def _detect_go_stack(self) -> List[str]:
        """Detect Go-specific technologies."""
        stack = []
        go_mod = self.project_root / "go.mod"

        if not go_mod.exists():
            return stack

        content = go_mod.read_text()
        if match := re.search(r"go (\d+\.\d+)", content):
            stack.append(f"Go {match.group(1)}")

        go_packages = {
            "chi": "Chi (HTTP router)",
            "gin": "Gin (Web framework)",
            "echo": "Echo (Web framework)",
            "fiber": "Fiber (Web framework)",
            "templ": "Templ (Templating)",
            "htmx": "htmx",
            "pgx": "PostgreSQL",
            "sqlc": "sqlc (SQL generator)",
            "gorm": "GORM (ORM)",
            "cobra": "Cobra (CLI framework)",
        }

        lower_content = content.lower()
        for pkg, name in go_packages.items():
            if pkg in lower_content and name not in stack:
                stack.append(name)

        return stack

    def _detect_js_stack(self) -> List[str]:
        """Detect JavaScript/TypeScript technologies."""
        stack = []
        package_json = self.project_root / "package.json"

        if not package_json.exists():
            return stack

        try:
            data = json.loads(package_json.read_text())
            deps = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
            }
        except Exception:
            deps = {}
            content = package_json.read_text().lower()
            for key in ("next", "react", "express", "vue", "svelte"):
                if key in content:
                    deps[key] = "unknown"

        framework_map = {
            "next": "Next.js",
            "react": "React",
            "express": "Express.js",
            "vue": "Vue",
            "svelte": "Svelte",
            "vite": "Vite",
            "typescript": "TypeScript",
        }

        for pkg, name in framework_map.items():
            if pkg in deps and name not in stack:
                stack.append(name)

        return stack

    def _detect_rust_stack(self) -> List[str]:
        """Detect Rust technologies."""
        stack = []
        cargo = self.project_root / "Cargo.toml"
        if not cargo.exists():
            return stack

        content = cargo.read_text().lower()
        if "edition" in content:
            stack.append("Rust")

        frameworks = {
            "tokio": "Tokio",
            "axum": "Axum",
            "rocket": "Rocket",
            "serde": "Serde",
        }
        for pkg, name in frameworks.items():
            if pkg in content and name not in stack:
                stack.append(name)

        return stack

    def _detect_java_stack(self) -> List[str]:
        """Detect Java technologies."""
        stack = []
        pom = self.project_root / "pom.xml"
        gradle = self.project_root / "build.gradle"
        gradle_kts = self.project_root / "build.gradle.kts"

        for file in (pom, gradle, gradle_kts):
            if not file.exists():
                continue
            content = file.read_text().lower()
            if "spring" in content and "Spring" not in stack:
                stack.append("Spring")
            if "quarkus" in content and "Quarkus" not in stack:
                stack.append("Quarkus")

        if stack:
            stack.insert(0, "Java")

        return stack

    def _detect_project_type(self) -> str:
        """Detect the type of project."""
        languages = self._detect_languages()
        if not languages:
            return "Unknown Project"

        primary = languages[0]
        project_type = f"{primary.title()} Project"

        if primary == "go":
            go_mod = self.project_root / "go.mod"
            if go_mod.exists():
                content = go_mod.read_text().lower()
                if "cobra" in content:
                    project_type = "Go CLI Application"
                if any(web in content for web in ("chi", "gin", "echo", "fiber")):
                    project_type = "Go Web Application"
                elif project_type == f"{primary.title()} Project":
                    project_type = "Go Project"
            else:
                project_type = "Go Project"

        elif primary in ("javascript", "typescript"):
            package_json = self.project_root / "package.json"
            if package_json.exists():
                content = package_json.read_text().lower()
                if "next" in content:
                    project_type = "Next.js Application"
                elif "express" in content:
                    project_type = "Express.js Application"
                elif "react" in content:
                    project_type = "React Application"
                else:
                    project_type = f"{primary.title()} Project"
            else:
                project_type = f"{primary.title()} Project"

        elif primary == "python":
            if (self.project_root / "pyproject.toml").exists():
                content = (self.project_root / "pyproject.toml").read_text()
                lower_content = content.lower()
                if "fastmcp" in lower_content:
                    project_type = "MCP Server"
                elif "fastapi" in lower_content:
                    project_type = "FastAPI Application"
                elif "django" in lower_content:
                    project_type = "Django Application"
                elif "flask" in lower_content:
                    project_type = "Flask Application"
                elif "[tool.poetry]" in content:
                    project_type = "Python Library"
                else:
                    project_type = "Python Project"

            if (self.project_root / "setup.py").exists():
                project_type = "Python Package"

        if len(languages) > 1:
            lang_str = " + ".join(lang.title() for lang in languages[:3])
            return f"Multi-Language Project ({lang_str})"

        return project_type

    def _infer_architecture(self) -> str:
        """Infer project architecture from structure."""
        directories = [d.name for d in self.project_root.glob("*") if d.is_dir()]
        languages = self._detect_languages()
        primary_lang = languages[0] if languages else "Unknown"

        if "mcp" in directories or "server" in directories:
            return f"MCP server ({primary_lang.title()})"
        if "api" in directories and "models" in directories:
            return f"REST API ({primary_lang.title()})"
        if "app" in directories and "templates" in directories:
            return f"Web application ({primary_lang.title()})"
        if "cli" in directories or "cmd" in directories:
            return f"CLI application ({primary_lang.title()})"
        if "web" in directories or "static" in directories:
            return f"Web application ({primary_lang.title()})"
        if "lib" in directories or "src" in directories:
            return (
                f"Library with modular components ({primary_lang.title()})"
            )

        if len(languages) > 1:
            joined = " + ".join(lang.title() for lang in languages)
            return f"Multi-language application ({joined})"

        return f"Modular {primary_lang.title()} application"

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
        entry_points: List[str] = []
        languages = self._detect_languages() or ["python"]

        for language in languages:
            patterns = ENTRY_POINT_PATTERNS.get(language, [])
            for pattern in patterns:
                for match in self.project_root.rglob(pattern):
                    if match.is_file():
                        rel_path = match.relative_to(self.project_root)
                        entry_points.append(str(rel_path))

        seen = set()
        deduped = []
        for entry in entry_points:
            if entry not in seen:
                deduped.append(entry)
                seen.add(entry)

        return deduped[:5]

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
