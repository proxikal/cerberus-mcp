"""
Circular Dependency Detection.

Detects circular import chains in Python projects.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any, Set, Tuple
import ast


@dataclass
class CircularChain:
    """A detected circular dependency chain."""

    chain: List[str]  # Module names in the cycle
    severity: str  # "low", "medium", "high", "critical"
    length: int  # Number of modules in cycle
    description: str  # Human-readable description


@dataclass
class CircularDependencyResult:
    """Results of circular dependency detection."""

    total_modules: int = 0
    circular_chains: List[Dict[str, Any]] = field(default_factory=list)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_modules": self.total_modules,
            "circular_chains": self.circular_chains,
            "summary": self.summary,
        }


class CircularDependencyDetector:
    """
    Detects circular dependencies in Python projects.

    Uses depth-first search to find all circular import chains.
    """

    def __init__(self, project_root: Path):
        """
        Initialize circular dependency detector.

        Args:
            project_root: Root directory of project
        """
        self.project_root = Path(project_root)
        self.dependency_graph: Dict[str, Set[str]] = {}
        self.module_files: Dict[str, Path] = {}

    def detect(
        self,
        scope: Optional[str] = None,
        min_severity: str = "low"
    ) -> CircularDependencyResult:
        """
        Detect circular dependencies in project.

        Args:
            scope: Optional path scope (directory). None = entire project
            min_severity: Minimum severity to report ("low", "medium", "high", "critical")

        Returns:
            CircularDependencyResult with detected cycles
        """
        # Determine scope
        if scope:
            scope_path = self.project_root / scope
            if not scope_path.exists():
                scope_path = Path(scope)
        else:
            scope_path = self.project_root

        # Build dependency graph
        files = self._get_python_files(scope_path)
        self._build_dependency_graph(files)

        # Find circular chains using DFS
        circular_chains = self._find_circular_chains()

        # Filter by severity
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_severity_level = severity_order.get(min_severity, 0)

        filtered_chains = [
            chain for chain in circular_chains
            if severity_order.get(chain.severity, 0) >= min_severity_level
        ]

        # Generate summary
        summary = self._generate_summary(filtered_chains, len(self.dependency_graph))

        return CircularDependencyResult(
            total_modules=len(self.dependency_graph),
            circular_chains=[self._chain_to_dict(c) for c in filtered_chains],
            dependency_graph={k: list(v) for k, v in self.dependency_graph.items()},
            summary=summary
        )

    def _get_python_files(self, scope_path: Path) -> List[Path]:
        """Get all Python files in scope."""
        files = []

        if scope_path.is_file():
            if scope_path.suffix == '.py':
                files.append(scope_path)
        elif scope_path.is_dir():
            files.extend(scope_path.glob("**/*.py"))

        # Filter out non-code files
        files = [
            f for f in files
            if not any(part.startswith(('.', '__pycache__', 'venv', 'env'))
                      for part in f.parts)
        ]

        return files

    def _build_dependency_graph(self, files: List[Path]) -> None:
        """Build import dependency graph from files."""
        for file_path in files:
            try:
                content = file_path.read_text()
                tree = ast.parse(content)

                module_name = self._get_module_name(file_path)
                self.module_files[module_name] = file_path

                # Extract imports
                imports = self._extract_imports(tree)

                # Add to graph
                if module_name not in self.dependency_graph:
                    self.dependency_graph[module_name] = set()

                for imported in imports:
                    self.dependency_graph[module_name].add(imported)

            except Exception:
                continue

    def _get_module_name(self, file_path: Path) -> str:
        """Get module name from file path."""
        try:
            rel_path = file_path.relative_to(self.project_root)
        except ValueError:
            # File is outside project root
            rel_path = file_path

        parts = list(rel_path.parts)

        # Remove .py extension
        if parts[-1].endswith('.py'):
            parts[-1] = parts[-1][:-3]

        # Remove __init__
        if parts[-1] == '__init__':
            parts = parts[:-1]

        # Skip empty parts
        parts = [p for p in parts if p]

        return '.'.join(parts)

    def _extract_imports(self, tree: ast.AST) -> Set[str]:
        """Extract all imports from AST."""
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)

        return imports

    def _find_circular_chains(self) -> List[CircularChain]:
        """Find all circular dependency chains using DFS."""
        chains = []
        visited_cycles = set()

        for module in self.dependency_graph.keys():
            # Run DFS from each module
            cycles = self._dfs_find_cycles(module, [module], set([module]))

            for cycle in cycles:
                # Normalize cycle (start from lexicographically smallest)
                normalized = self._normalize_cycle(cycle)
                cycle_key = tuple(normalized)

                if cycle_key not in visited_cycles:
                    visited_cycles.add(cycle_key)

                    # Create CircularChain
                    severity = self._calculate_severity(normalized)
                    description = " → ".join(normalized) + " → " + normalized[0]

                    chains.append(CircularChain(
                        chain=normalized,
                        severity=severity,
                        length=len(normalized),
                        description=description
                    ))

        # Sort by severity and length
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        chains.sort(key=lambda c: (severity_order.get(c.severity, 4), c.length))

        return chains

    def _dfs_find_cycles(
        self,
        current: str,
        path: List[str],
        visited: Set[str]
    ) -> List[List[str]]:
        """DFS to find cycles from current node."""
        cycles = []

        # Get dependencies
        dependencies = self.dependency_graph.get(current, set())

        for neighbor in dependencies:
            # Skip if not in our module graph
            if neighbor not in self.dependency_graph:
                continue

            if neighbor in visited:
                # Found a cycle!
                # Extract the cycle from path
                try:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:]
                    cycles.append(cycle)
                except ValueError:
                    continue
            else:
                # Continue DFS
                new_path = path + [neighbor]
                new_visited = visited | {neighbor}
                cycles.extend(self._dfs_find_cycles(neighbor, new_path, new_visited))

        return cycles

    def _normalize_cycle(self, cycle: List[str]) -> List[str]:
        """Normalize cycle to start from lexicographically smallest module."""
        if not cycle:
            return cycle

        min_idx = cycle.index(min(cycle))
        return cycle[min_idx:] + cycle[:min_idx]

    def _calculate_severity(self, chain: List[str]) -> str:
        """Calculate severity of circular dependency."""
        length = len(chain)

        # Check if any modules are core/critical
        critical_prefixes = ['__init__', 'main', 'app', 'server', 'core']
        has_critical = any(
            any(module.startswith(prefix) or prefix in module for prefix in critical_prefixes)
            for module in chain
        )

        if length == 2:
            # Direct circular dependency
            if has_critical:
                return "high"
            return "medium"
        elif length == 3:
            # Three-way cycle
            if has_critical:
                return "high"
            return "medium"
        elif length >= 4:
            # Long cycle chain
            if has_critical:
                return "critical"
            return "high"
        else:
            return "low"

    def _chain_to_dict(self, chain: CircularChain) -> Dict[str, Any]:
        """Convert CircularChain to dict."""
        return {
            "chain": chain.chain,
            "severity": chain.severity,
            "length": chain.length,
            "description": chain.description,
        }

    def _generate_summary(self, chains: List[CircularChain], total_modules: int) -> str:
        """Generate summary message."""
        if not chains:
            return f"✓ No circular dependencies found ({total_modules} modules analyzed)"

        # Count by severity
        by_severity = {}
        for chain in chains:
            by_severity[chain.severity] = by_severity.get(chain.severity, 0) + 1

        parts = []
        for severity in ["critical", "high", "medium", "low"]:
            if severity in by_severity:
                parts.append(f"{by_severity[severity]} {severity}")

        severity_desc = ", ".join(parts)
        return f"⚠️  Found {len(chains)} circular dependency chain(s) ({severity_desc})"


def find_circular_dependencies(
    project_root: Path,
    scope: Optional[str] = None,
    min_severity: str = "low"
) -> CircularDependencyResult:
    """
    Convenience function to find circular dependencies.

    Args:
        project_root: Root directory of project
        scope: Optional path scope
        min_severity: Minimum severity to report

    Returns:
        CircularDependencyResult object
    """
    detector = CircularDependencyDetector(project_root)
    return detector.detect(scope, min_severity)
