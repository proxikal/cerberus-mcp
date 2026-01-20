"""
Pattern Consistency Checker.

Checks if code follows established project patterns.
Helps AI agents maintain consistency when writing new code.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any, Set
import ast
import re


@dataclass
class PatternDefinition:
    """Definition of a pattern to check."""

    name: str
    description: str
    positive_indicators: List[str]  # What to look for (regex or AST patterns)
    negative_indicators: List[str]  # What indicates violation
    suggestion_template: str  # How to fix violations


@dataclass
class PatternViolation:
    """A single pattern violation."""

    file: str
    line: int
    issue: str
    snippet: str  # Code snippet showing the violation
    suggestion: str  # How to fix it


@dataclass
class PatternExample:
    """An example of correct pattern usage."""

    file: str
    line: int
    snippet: str
    description: str


@dataclass
class PatternCheckResult:
    """Results of pattern consistency check."""

    pattern: str
    description: str
    conforming_files: int
    total_files: int
    violations: List[Dict[str, Any]] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    consistency_score: float = 0.0
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern,
            "description": self.description,
            "conforming_files": self.conforming_files,
            "total_files": self.total_files,
            "violations": self.violations,
            "examples": self.examples,
            "consistency_score": self.consistency_score,
            "suggestion": self.suggestion,
        }


class PatternChecker:
    """
    Checks code for pattern consistency.

    Analyzes codebase to:
    - Find which files follow patterns
    - Identify violations with context
    - Provide examples of correct usage
    - Score consistency across project
    """

    # Built-in pattern definitions
    PATTERNS = {
        "dataclass": PatternDefinition(
            name="dataclass",
            description="Use dataclasses for data structures instead of dicts or tuples",
            positive_indicators=[r"@dataclass", r"from dataclasses import"],
            negative_indicators=[r"^\s*class\s+\w+.*:\s*$"],  # Class without dataclass
            suggestion_template="Convert to @dataclass for consistency"
        ),
        "type_hints": PatternDefinition(
            name="type_hints",
            description="Type hints required on function parameters and returns",
            positive_indicators=[r"def \w+\([^)]*:\s*\w+", r"->\s*\w+:"],
            negative_indicators=[r"def \w+\([^)]*\)(?!\s*->)"],  # Function without return type
            suggestion_template="Add type hints to function signature"
        ),
        "async_await": PatternDefinition(
            name="async_await",
            description="Use async/await for I/O operations",
            positive_indicators=[r"async def", r"await "],
            negative_indicators=[],  # This is more about consistency than violations
            suggestion_template="Consider using async/await for I/O operations"
        ),
        "error_handling": PatternDefinition(
            name="error_handling",
            description="Use try/except for error handling with proper logging",
            positive_indicators=[r"try:", r"except \w+"],
            negative_indicators=[r"except:\s*$", r"except\s+Exception:\s*pass"],  # Bare except or silent catch
            suggestion_template="Use specific exception types and log errors"
        ),
        "import_style": PatternDefinition(
            name="import_style",
            description="Use absolute imports over relative imports",
            positive_indicators=[r"^from \w+", r"^import \w+"],
            negative_indicators=[r"^from \.", r"^from \.\."],  # Relative imports
            suggestion_template="Use absolute imports for consistency"
        ),
        "docstring_style": PatternDefinition(
            name="docstring_style",
            description="Use Google-style docstrings",
            positive_indicators=[r'""".*Args:', r'""".*Returns:'],
            negative_indicators=[r'"""\s*:param', r'"""\s*:return'],  # Sphinx style
            suggestion_template="Use Google-style docstrings (Args:, Returns:)"
        ),
    }

    def __init__(self, project_root: Path, extensions: Optional[List[str]] = None):
        """
        Initialize pattern checker.

        Args:
            project_root: Root directory of project
            extensions: File extensions to check (default: ['.py'])
        """
        self.project_root = Path(project_root)
        self.extensions = extensions or ['.py']

    def check_pattern(
        self,
        pattern_name: str,
        scope: Optional[str] = None,
        show_examples: bool = True,
        limit: int = 20
    ) -> PatternCheckResult:
        """
        Check pattern consistency across codebase.

        Args:
            pattern_name: Name of pattern to check (see PATTERNS keys)
            scope: Optional path to check (file or directory). None = entire project
            show_examples: Whether to include examples of correct usage
            limit: Maximum violations to return (default: 20)

        Returns:
            PatternCheckResult with analysis
        """
        # Get pattern definition
        pattern = self._get_pattern_definition(pattern_name)
        if not pattern:
            return PatternCheckResult(
                pattern=pattern_name,
                description=f"Unknown pattern: {pattern_name}",
                conforming_files=0,
                total_files=0,
                suggestion=f"Available patterns: {', '.join(self.PATTERNS.keys())}"
            )

        # Determine scope
        if scope:
            scope_path = self.project_root / scope
            if not scope_path.exists():
                scope_path = Path(scope)
        else:
            scope_path = self.project_root

        # Get all files in scope
        files = self._get_files_in_scope(scope_path)

        # Find conforming and violating files
        conforming_files = self._find_conforming_files(pattern, files)
        violations = self._find_violations(pattern, files, limit)

        # Calculate consistency score
        total_files = len(files)
        conforming_count = len(conforming_files)
        consistency_score = conforming_count / total_files if total_files > 0 else 0.0

        # Extract examples if requested
        examples = []
        if show_examples and conforming_files:
            examples = self._extract_examples(pattern, conforming_files[:3])

        # Generate suggestion
        suggestion = self._generate_suggestion(
            pattern,
            conforming_count,
            len(violations),
            consistency_score
        )

        return PatternCheckResult(
            pattern=pattern.name,
            description=pattern.description,
            conforming_files=conforming_count,
            total_files=total_files,
            violations=[v.__dict__ for v in violations],
            examples=[e.__dict__ for e in examples],
            consistency_score=round(consistency_score, 2),
            suggestion=suggestion
        )

    def _get_pattern_definition(self, pattern_name: str) -> Optional[PatternDefinition]:
        """Get pattern definition by name."""
        return self.PATTERNS.get(pattern_name)

    def _get_files_in_scope(self, scope_path: Path) -> List[Path]:
        """Get all relevant files in scope."""
        files = []

        if scope_path.is_file():
            if scope_path.suffix in self.extensions:
                files.append(scope_path)
        elif scope_path.is_dir():
            for ext in self.extensions:
                files.extend(scope_path.glob(f"**/*{ext}"))

        # Filter out test files, migrations, and other non-code files
        files = [
            f for f in files
            if not any(part.startswith(('.', '__pycache__', 'venv', 'env'))
                      for part in f.parts)
        ]

        return files

    def _find_conforming_files(
        self,
        pattern: PatternDefinition,
        files: List[Path]
    ) -> List[Path]:
        """Find files that conform to the pattern."""
        conforming = []

        for file_path in files:
            try:
                content = file_path.read_text()

                # Check for positive indicators
                has_pattern = any(
                    re.search(indicator, content, re.MULTILINE)
                    for indicator in pattern.positive_indicators
                )

                if has_pattern:
                    conforming.append(file_path)

            except Exception:
                continue

        return conforming

    def _find_violations(
        self,
        pattern: PatternDefinition,
        files: List[Path],
        limit: int
    ) -> List[PatternViolation]:
        """Find pattern violations."""
        violations = []

        for file_path in files:
            if len(violations) >= limit:
                break

            try:
                content = file_path.read_text()
                lines = content.split('\n')

                # Check for negative indicators
                for indicator in pattern.negative_indicators:
                    for line_num, line in enumerate(lines, 1):
                        if len(violations) >= limit:
                            break

                        if re.search(indicator, line):
                            # Extract context (3 lines around violation)
                            start = max(0, line_num - 2)
                            end = min(len(lines), line_num + 1)
                            snippet = '\n'.join(lines[start:end])

                            # Determine issue description
                            issue = self._describe_issue(pattern, line, indicator)

                            violations.append(PatternViolation(
                                file=str(file_path.relative_to(self.project_root)),
                                line=line_num,
                                issue=issue,
                                snippet=snippet.strip(),
                                suggestion=pattern.suggestion_template
                            ))

            except Exception:
                continue

        return violations

    def _describe_issue(
        self,
        pattern: PatternDefinition,
        line: str,
        indicator: str
    ) -> str:
        """Generate human-readable issue description."""
        if pattern.name == "dataclass":
            return "Class without @dataclass decorator"
        elif pattern.name == "type_hints":
            return "Missing type hints"
        elif pattern.name == "error_handling":
            if "except:" in line:
                return "Bare except clause"
            elif "pass" in line:
                return "Silent exception handling"
            return "Improper exception handling"
        elif pattern.name == "import_style":
            return "Relative import instead of absolute"
        elif pattern.name == "docstring_style":
            return "Sphinx-style docstring instead of Google-style"
        else:
            return f"Does not follow {pattern.name} pattern"

    def _extract_examples(
        self,
        pattern: PatternDefinition,
        conforming_files: List[Path]
    ) -> List[PatternExample]:
        """Extract examples of correct pattern usage."""
        examples = []

        for file_path in conforming_files[:3]:  # Max 3 examples
            try:
                content = file_path.read_text()
                lines = content.split('\n')

                # Find first occurrence of pattern
                for indicator in pattern.positive_indicators:
                    for line_num, line in enumerate(lines, 1):
                        if re.search(indicator, line):
                            # Extract context (5 lines around match)
                            start = max(0, line_num - 2)
                            end = min(len(lines), line_num + 3)
                            snippet = '\n'.join(lines[start:end])

                            examples.append(PatternExample(
                                file=str(file_path.relative_to(self.project_root)),
                                line=line_num,
                                snippet=snippet.strip(),
                                description=f"Correct {pattern.name} usage"
                            ))
                            break

                    if examples:
                        break

            except Exception:
                continue

        return examples

    def _generate_suggestion(
        self,
        pattern: PatternDefinition,
        conforming: int,
        violations: int,
        score: float
    ) -> str:
        """Generate actionable suggestion based on results."""
        if score >= 0.9:
            return f"✓ Excellent consistency ({score:.0%}) - project follows {pattern.name} pattern"
        elif score >= 0.7:
            return f"Good consistency ({score:.0%}) - consider updating {violations} file(s)"
        elif score >= 0.5:
            return f"Moderate consistency ({score:.0%}) - {violations} violations found"
        elif score > 0:
            return f"Low consistency ({score:.0%}) - pattern not widely adopted"
        else:
            return f"Pattern not found in project - no {pattern.name} usage detected"


def check_pattern_consistency(
    project_root: Path,
    pattern_name: str,
    scope: Optional[str] = None,
    show_examples: bool = True,
    limit: int = 20
) -> PatternCheckResult:
    """
    Convenience function to check pattern consistency.

    Args:
        project_root: Root directory of project
        pattern_name: Name of pattern to check
        scope: Optional path to scope check to
        show_examples: Whether to include examples
        limit: Max violations to return

    Returns:
        PatternCheckResult object
    """
    checker = PatternChecker(project_root)
    return checker.check_pattern(pattern_name, scope, show_examples, limit)
