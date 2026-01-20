"""
Architecture Validation.

Validates code against project-specific architectural rules.
Enforces structural boundaries, interfaces, and design constraints.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
import ast
import re


@dataclass
class ArchitectureRule:
    """Definition of an architecture rule."""

    name: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    check_function: Optional[Callable] = None  # Custom check function
    scope: Optional[str] = None  # File pattern to apply rule to
    forbid_patterns: List[str] = field(default_factory=list)  # Patterns that violate rule
    require_patterns: List[str] = field(default_factory=list)  # Required patterns
    suggestion_template: str = ""


@dataclass
class ArchitectureViolation:
    """A single architecture violation."""

    rule: str
    severity: str
    file: str
    line: int
    issue: str
    snippet: str
    suggestion: str


@dataclass
class ArchitectureValidationResult:
    """Results of architecture validation."""

    rules_checked: List[str] = field(default_factory=list)
    total_files: int = 0
    violations: List[Dict[str, Any]] = field(default_factory=list)
    conformance_score: float = 1.0  # 1.0 = perfect, 0.0 = many violations
    status: str = "pass"  # "pass", "warnings", "fail"
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rules_checked": self.rules_checked,
            "total_files": self.total_files,
            "violations": self.violations,
            "conformance_score": self.conformance_score,
            "status": self.status,
            "summary": self.summary,
        }


class ArchitectureValidator:
    """
    Validates code against architectural rules.

    Enforces:
    - Layer separation
    - Type annotation coverage
    - Docstring coverage
    - Async/sync boundaries
    - Import restrictions
    """

    def __init__(self, project_root: Path):
        """
        Initialize architecture validator.

        Args:
            project_root: Root directory of project
        """
        self.project_root = Path(project_root)
        self.rules = self._build_rules()

    def validate(
        self,
        rules: Optional[List[str]] = None,
        scope: Optional[str] = None,
        limit: int = 30
    ) -> ArchitectureValidationResult:
        """
        Validate architecture against rules.

        Args:
            rules: List of rule names to check. None = all rules
            scope: Optional path scope (file or directory). None = entire project
            limit: Maximum violations to return (default: 30)

        Returns:
            ArchitectureValidationResult with violations and score
        """
        # Determine which rules to check
        rules_to_check = rules or list(self.rules.keys())
        rules_to_check = [r for r in rules_to_check if r in self.rules]

        # Determine scope
        if scope:
            scope_path = self.project_root / scope
            if not scope_path.exists():
                scope_path = Path(scope)
        else:
            scope_path = self.project_root

        # Get all Python files in scope
        files = self._get_python_files(scope_path)

        # Check each rule
        all_violations = []
        for rule_name in rules_to_check:
            rule = self.rules[rule_name]
            violations = self._check_rule(rule, files, limit - len(all_violations))
            all_violations.extend(violations)

            if len(all_violations) >= limit:
                break

        # Calculate conformance score
        conformance_score = self._calculate_conformance(all_violations, len(files))

        # Determine status
        status = self._determine_status(all_violations)

        # Generate summary
        summary = self._generate_summary(rules_to_check, all_violations, conformance_score)

        return ArchitectureValidationResult(
            rules_checked=rules_to_check,
            total_files=len(files),
            violations=[v.__dict__ for v in all_violations],
            conformance_score=conformance_score,
            status=status,
            summary=summary
        )

    def _build_rules(self) -> Dict[str, ArchitectureRule]:
        """Build built-in architecture rules."""
        return {
            "layer_separation": ArchitectureRule(
                name="layer_separation",
                description="MCP tools should use index_manager, not direct store access",
                severity="high",
                scope="src/cerberus/mcp/tools/*.py",
                forbid_patterns=[
                    r"from cerberus\.storage\.sqlite import",
                    r"from cerberus\.storage import",
                    r"SQLiteSymbolStore\(",
                ],
                require_patterns=[],
                suggestion_template="Use get_index_manager().get_index() instead of direct store access"
            ),
            "type_coverage": ArchitectureRule(
                name="type_coverage",
                description="All public functions must have type hints",
                severity="medium",
                check_function=self._check_type_coverage,
                suggestion_template="Add type hints to function signature: def func(arg: Type) -> ReturnType"
            ),
            "docstring_coverage": ArchitectureRule(
                name="docstring_coverage",
                description="All public classes and functions must have docstrings",
                severity="medium",
                check_function=self._check_docstring_coverage,
                suggestion_template="Add docstring explaining purpose, args, and return value"
            ),
            "async_boundaries": ArchitectureRule(
                name="async_boundaries",
                description="MCP tools must be async functions",
                severity="high",
                scope="src/cerberus/mcp/tools/*.py",
                forbid_patterns=[r"@mcp\.tool\(\)\s+def "],  # Non-async MCP tool
                suggestion_template="MCP tools should be async: @mcp.tool() async def ..."
            ),
            "import_restrictions": ArchitectureRule(
                name="import_restrictions",
                description="No circular imports between modules",
                severity="high",
                check_function=self._check_import_restrictions,
                suggestion_template="Refactor to remove circular dependency"
            ),
        }

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

    def _check_rule(
        self,
        rule: ArchitectureRule,
        files: List[Path],
        limit: int
    ) -> List[ArchitectureViolation]:
        """Check a single rule across files."""
        violations = []

        # If rule has custom check function, use it
        if rule.check_function:
            return rule.check_function(rule, files, limit)

        # Otherwise, use pattern-based checking
        for file_path in files:
            if len(violations) >= limit:
                break

            # Check if file matches rule scope
            if rule.scope and not self._matches_scope(file_path, rule.scope):
                continue

            try:
                content = file_path.read_text()
                lines = content.split('\n')

                # Check for forbidden patterns
                for pattern in rule.forbid_patterns:
                    for line_num, line in enumerate(lines, 1):
                        if len(violations) >= limit:
                            break

                        if re.search(pattern, line):
                            # Extract context
                            start = max(0, line_num - 2)
                            end = min(len(lines), line_num + 1)
                            snippet = '\n'.join(lines[start:end])

                            violations.append(ArchitectureViolation(
                                rule=rule.name,
                                severity=rule.severity,
                                file=str(file_path.relative_to(self.project_root)),
                                line=line_num,
                                issue=self._describe_violation(rule, pattern, line),
                                snippet=snippet.strip(),
                                suggestion=rule.suggestion_template
                            ))

            except Exception:
                continue

        return violations

    def _check_type_coverage(
        self,
        rule: ArchitectureRule,
        files: List[Path],
        limit: int
    ) -> List[ArchitectureViolation]:
        """Check for type annotation coverage on public functions."""
        violations = []

        for file_path in files:
            if len(violations) >= limit:
                break

            try:
                content = file_path.read_text()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if len(violations) >= limit:
                        break

                    # Check functions and methods
                    if isinstance(node, ast.FunctionDef):
                        # Skip private functions
                        if node.name.startswith('_'):
                            continue

                        # Check if function has type hints
                        has_return_hint = node.returns is not None
                        has_arg_hints = all(
                            arg.annotation is not None
                            for arg in node.args.args
                            if arg.arg != 'self'
                        )

                        if not (has_return_hint and has_arg_hints):
                            # Extract snippet
                            lines = content.split('\n')
                            start = max(0, node.lineno - 1)
                            end = min(len(lines), node.lineno + 2)
                            snippet = '\n'.join(lines[start:end])

                            violations.append(ArchitectureViolation(
                                rule=rule.name,
                                severity=rule.severity,
                                file=str(file_path.relative_to(self.project_root)),
                                line=node.lineno,
                                issue=f"Public function '{node.name}' missing type hints",
                                snippet=snippet.strip(),
                                suggestion=rule.suggestion_template
                            ))

            except Exception:
                continue

        return violations

    def _check_docstring_coverage(
        self,
        rule: ArchitectureRule,
        files: List[Path],
        limit: int
    ) -> List[ArchitectureViolation]:
        """Check for docstring coverage on public classes and functions."""
        violations = []

        for file_path in files:
            if len(violations) >= limit:
                break

            try:
                content = file_path.read_text()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if len(violations) >= limit:
                        break

                    # Check classes and functions
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        # Skip private items
                        if node.name.startswith('_') and not node.name.startswith('__'):
                            continue

                        # Check if has docstring
                        has_docstring = (
                            ast.get_docstring(node) is not None
                        )

                        if not has_docstring:
                            # Extract snippet
                            lines = content.split('\n')
                            start = max(0, node.lineno - 1)
                            end = min(len(lines), node.lineno + 2)
                            snippet = '\n'.join(lines[start:end])

                            item_type = "class" if isinstance(node, ast.ClassDef) else "function"
                            violations.append(ArchitectureViolation(
                                rule=rule.name,
                                severity=rule.severity,
                                file=str(file_path.relative_to(self.project_root)),
                                line=node.lineno,
                                issue=f"Public {item_type} '{node.name}' missing docstring",
                                snippet=snippet.strip(),
                                suggestion=rule.suggestion_template
                            ))

            except Exception:
                continue

        return violations

    def _check_import_restrictions(
        self,
        rule: ArchitectureRule,
        files: List[Path],
        limit: int
    ) -> List[ArchitectureViolation]:
        """Check for circular imports (simplified detection)."""
        violations = []

        # Build import graph
        import_graph = {}
        for file_path in files:
            try:
                content = file_path.read_text()
                tree = ast.parse(content)

                module_name = self._get_module_name(file_path)
                imports = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)

                import_graph[module_name] = imports

            except Exception:
                continue

        # Detect circular imports (simplified - only direct circles)
        for module, imports in import_graph.items():
            if len(violations) >= limit:
                break

            for imported in imports:
                # Check if imported module imports us back
                if imported in import_graph:
                    if module in import_graph[imported]:
                        # Find the file for this module
                        file_path = self._find_file_for_module(module, files)
                        if file_path:
                            violations.append(ArchitectureViolation(
                                rule=rule.name,
                                severity=rule.severity,
                                file=str(file_path.relative_to(self.project_root)),
                                line=1,
                                issue=f"Circular import: {module} ↔ {imported}",
                                snippet=f"# Circular dependency detected\nimport {imported}",
                                suggestion=rule.suggestion_template
                            ))

        return violations

    def _matches_scope(self, file_path: Path, scope_pattern: str) -> bool:
        """Check if file matches scope pattern."""
        rel_path = str(file_path.relative_to(self.project_root))
        # Convert glob pattern to regex
        pattern = scope_pattern.replace('*', '.*').replace('?', '.')
        return re.match(pattern, rel_path) is not None

    def _get_module_name(self, file_path: Path) -> str:
        """Get module name from file path."""
        rel_path = file_path.relative_to(self.project_root)
        parts = list(rel_path.parts)

        # Remove .py extension
        if parts[-1].endswith('.py'):
            parts[-1] = parts[-1][:-3]

        # Remove __init__
        if parts[-1] == '__init__':
            parts = parts[:-1]

        return '.'.join(parts)

    def _find_file_for_module(self, module_name: str, files: List[Path]) -> Optional[Path]:
        """Find file path for module name."""
        for file_path in files:
            if self._get_module_name(file_path) == module_name:
                return file_path
        return None

    def _describe_violation(self, rule: ArchitectureRule, pattern: str, line: str) -> str:
        """Generate human-readable violation description."""
        if rule.name == "layer_separation":
            return "Direct storage import instead of using index_manager"
        elif rule.name == "async_boundaries":
            return "MCP tool is not async"
        else:
            return f"Violates {rule.name} rule"

    def _calculate_conformance(self, violations: List[ArchitectureViolation], total_files: int) -> float:
        """Calculate conformance score based on violations."""
        if total_files == 0:
            return 1.0

        # Weight by severity
        severity_weights = {
            "low": 0.1,
            "medium": 0.3,
            "high": 0.5,
            "critical": 1.0,
        }

        total_weight = sum(
            severity_weights.get(v.severity, 0.5)
            for v in violations
        )

        # Normalize by file count
        penalty = total_weight / (total_files * 2)  # Max 2 violations per file expected
        score = max(0.0, 1.0 - penalty)

        return round(score, 2)

    def _determine_status(self, violations: List[ArchitectureViolation]) -> str:
        """Determine overall status based on violations."""
        if not violations:
            return "pass"

        # Check for critical violations
        critical = any(v.severity == "critical" for v in violations)
        if critical:
            return "fail"

        # Check for high severity violations
        high = any(v.severity == "high" for v in violations)
        if high:
            return "fail"

        # Medium or low violations
        return "warnings"

    def _generate_summary(
        self,
        rules_checked: List[str],
        violations: List[ArchitectureViolation],
        score: float
    ) -> str:
        """Generate summary message."""
        if not violations:
            return f"✓ All {len(rules_checked)} architectural rules passed"

        by_severity = {}
        for v in violations:
            by_severity[v.severity] = by_severity.get(v.severity, 0) + 1

        parts = []
        for severity in ["critical", "high", "medium", "low"]:
            if severity in by_severity:
                parts.append(f"{by_severity[severity]} {severity}")

        violations_desc = ", ".join(parts)
        return f"⚠️  Found {len(violations)} violations ({violations_desc}). Conformance: {score:.0%}"


def validate_architecture(
    project_root: Path,
    rules: Optional[List[str]] = None,
    scope: Optional[str] = None,
    limit: int = 30
) -> ArchitectureValidationResult:
    """
    Convenience function to validate architecture.

    Args:
        project_root: Root directory of project
        rules: List of rule names to check. None = all rules
        scope: Optional path scope
        limit: Max violations to return

    Returns:
        ArchitectureValidationResult object
    """
    validator = ArchitectureValidator(project_root)
    return validator.validate(rules, scope, limit)
