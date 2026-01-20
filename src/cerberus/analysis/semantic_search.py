"""
Semantic Code Search.

Search code by behavior/purpose rather than just symbol names.
Uses AST analysis to detect behavioral patterns.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
import ast
import re


@dataclass
class BehaviorPattern:
    """Definition of a behavior pattern to detect."""

    name: str
    description: str
    keywords: List[str]  # Keywords in the query that trigger this pattern
    detector: Callable  # Function to detect this behavior in AST


@dataclass
class SemanticMatch:
    """A match for a semantic search query."""

    symbol: str  # Function/class name
    file: str  # File path
    line: int  # Line number
    confidence: float  # 0.0-1.0 confidence score
    reason: str  # Why this matches
    snippet: str  # Code snippet
    behavior: str  # Detected behavior type


@dataclass
class SemanticSearchResult:
    """Results of semantic search."""

    query: str
    matches: List[Dict[str, Any]] = field(default_factory=list)
    detected_patterns: List[str] = field(default_factory=list)
    total_files_scanned: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "matches": self.matches,
            "detected_patterns": self.detected_patterns,
            "total_files_scanned": self.total_files_scanned,
        }


class SemanticSearchEngine:
    """
    Searches code by behavior patterns using AST analysis.

    Detects:
    - HTTP calls (httpx, requests)
    - Error handlers (try/except)
    - Database queries (sqlite3, sqlalchemy)
    - File I/O operations (open, Path)
    - Async operations (async def, await)
    - Logging operations (logger calls)
    - Data validation (pydantic, dataclasses)
    """

    def __init__(self, project_root: Path):
        """
        Initialize semantic search engine.

        Args:
            project_root: Root directory of project
        """
        self.project_root = Path(project_root)
        self.patterns = self._build_behavior_patterns()

    def search(
        self,
        query: str,
        scope: Optional[str] = None,
        limit: int = 15
    ) -> SemanticSearchResult:
        """
        Search for code matching behavioral query.

        Args:
            query: Natural language behavior description
                   (e.g., "functions that make HTTP calls")
            scope: Optional path scope (file or directory)
            limit: Max matches to return

        Returns:
            SemanticSearchResult with matches
        """
        # Determine which patterns match the query
        matched_patterns = self._match_query_to_patterns(query)

        # Get files to search
        if scope:
            scope_path = self.project_root / scope
            if not scope_path.exists():
                scope_path = Path(scope)
        else:
            scope_path = self.project_root

        files = self._get_python_files(scope_path)

        # Search for matches
        all_matches = []
        for pattern_name in matched_patterns:
            pattern = self.patterns[pattern_name]
            matches = self._find_matches(pattern, files, limit - len(all_matches))
            all_matches.extend(matches)

            if len(all_matches) >= limit:
                break

        # Sort by confidence
        all_matches.sort(key=lambda m: m.confidence, reverse=True)

        return SemanticSearchResult(
            query=query,
            matches=[m.__dict__ for m in all_matches[:limit]],
            detected_patterns=matched_patterns,
            total_files_scanned=len(files)
        )

    def _build_behavior_patterns(self) -> Dict[str, BehaviorPattern]:
        """Build library of behavior patterns."""
        return {
            "http_calls": BehaviorPattern(
                name="http_calls",
                description="Functions that make HTTP requests",
                keywords=["http", "request", "api", "fetch", "download", "upload", "rest", "endpoint"],
                detector=self._detect_http_calls
            ),
            "error_handlers": BehaviorPattern(
                name="error_handlers",
                description="Functions with error handling",
                keywords=["error", "exception", "handle", "catch", "try", "except"],
                detector=self._detect_error_handlers
            ),
            "database_queries": BehaviorPattern(
                name="database_queries",
                description="Functions that query databases",
                keywords=["database", "query", "sql", "select", "insert", "update", "delete", "db"],
                detector=self._detect_database_queries
            ),
            "file_io": BehaviorPattern(
                name="file_io",
                description="Functions that perform file I/O",
                keywords=["file", "read", "write", "open", "save", "load", "i/o", "io"],
                detector=self._detect_file_io
            ),
            "async_operations": BehaviorPattern(
                name="async_operations",
                description="Async functions and operations",
                keywords=["async", "await", "asyncio", "concurrent", "parallel"],
                detector=self._detect_async_operations
            ),
            "logging": BehaviorPattern(
                name="logging",
                description="Functions that log information",
                keywords=["log", "logger", "logging", "debug", "info", "warn", "error"],
                detector=self._detect_logging
            ),
            "data_validation": BehaviorPattern(
                name="data_validation",
                description="Functions that validate data",
                keywords=["validate", "validation", "check", "verify", "dataclass", "pydantic"],
                detector=self._detect_data_validation
            ),
        }

    def _match_query_to_patterns(self, query: str) -> List[str]:
        """Match query to behavior patterns."""
        query_lower = query.lower()
        matched = []

        for pattern_name, pattern in self.patterns.items():
            # Check if any keywords appear in query
            if any(keyword in query_lower for keyword in pattern.keywords):
                matched.append(pattern_name)

        # If no patterns matched, try all patterns (fallback)
        if not matched:
            matched = list(self.patterns.keys())

        return matched

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

    def _find_matches(
        self,
        pattern: BehaviorPattern,
        files: List[Path],
        limit: int
    ) -> List[SemanticMatch]:
        """Find matches for a behavior pattern."""
        matches = []

        for file_path in files:
            if len(matches) >= limit:
                break

            try:
                content = file_path.read_text()
                tree = ast.parse(content)

                # Use pattern's detector function
                file_matches = pattern.detector(file_path, tree, content, pattern)
                matches.extend(file_matches[:limit - len(matches)])

            except Exception:
                continue

        return matches

    def _detect_http_calls(
        self,
        file_path: Path,
        tree: ast.AST,
        content: str,
        pattern: BehaviorPattern
    ) -> List[SemanticMatch]:
        """Detect HTTP calls in code."""
        matches = []

        # Check for HTTP library imports
        has_httpx = 'httpx' in content
        has_requests = 'requests' in content
        has_urllib = 'urllib' in content

        if not (has_httpx or has_requests or has_urllib):
            return matches

        # Find functions that use HTTP methods
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function body contains HTTP calls
                func_source = ast.get_source_segment(content, node)
                if not func_source:
                    continue

                confidence = 0.0
                reasons = []

                # Check for HTTP method calls
                if re.search(r'\.(get|post|put|delete|patch|head)\(', func_source):
                    confidence += 0.5
                    reasons.append("Uses HTTP methods (.get, .post, etc)")

                # Check for HTTP libraries
                if 'httpx' in func_source:
                    confidence += 0.3
                    reasons.append("Uses httpx")
                elif 'requests' in func_source:
                    confidence += 0.3
                    reasons.append("Uses requests")
                elif 'urllib' in func_source:
                    confidence += 0.2
                    reasons.append("Uses urllib")

                # Check for URL patterns
                if re.search(r'https?://', func_source):
                    confidence += 0.2
                    reasons.append("Contains URLs")

                if confidence > 0.4:
                    snippet = self._extract_snippet(content, node.lineno)
                    matches.append(SemanticMatch(
                        symbol=node.name,
                        file=str(file_path.relative_to(self.project_root)),
                        line=node.lineno,
                        confidence=min(1.0, confidence),
                        reason=", ".join(reasons),
                        snippet=snippet,
                        behavior="http_calls"
                    ))

        return matches

    def _detect_error_handlers(
        self,
        file_path: Path,
        tree: ast.AST,
        content: str,
        pattern: BehaviorPattern
    ) -> List[SemanticMatch]:
        """Detect error handling in code."""
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function contains try/except
                has_try_except = any(
                    isinstance(n, ast.Try)
                    for n in ast.walk(node)
                )

                if has_try_except:
                    func_source = ast.get_source_segment(content, node) or ""

                    # Count exception handlers
                    exception_count = func_source.count('except')
                    has_finally = 'finally' in func_source
                    has_logging = 'log' in func_source.lower()

                    confidence = 0.6  # Base confidence for having try/except
                    reasons = ["Contains try/except blocks"]

                    if exception_count > 1:
                        confidence += 0.2
                        reasons.append(f"Multiple exception handlers ({exception_count})")

                    if has_finally:
                        confidence += 0.1
                        reasons.append("Has finally block")

                    if has_logging:
                        confidence += 0.1
                        reasons.append("Logs errors")

                    snippet = self._extract_snippet(content, node.lineno)
                    matches.append(SemanticMatch(
                        symbol=node.name,
                        file=str(file_path.relative_to(self.project_root)),
                        line=node.lineno,
                        confidence=min(1.0, confidence),
                        reason=", ".join(reasons),
                        snippet=snippet,
                        behavior="error_handlers"
                    ))

        return matches

    def _detect_database_queries(
        self,
        file_path: Path,
        tree: ast.AST,
        content: str,
        pattern: BehaviorPattern
    ) -> List[SemanticMatch]:
        """Detect database queries in code."""
        matches = []

        # Check for database library imports
        has_sqlite = 'sqlite' in content
        has_sqlalchemy = 'sqlalchemy' in content
        has_sql = 'sql' in content.lower()

        if not (has_sqlite or has_sqlalchemy or has_sql):
            return matches

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_source = ast.get_source_segment(content, node) or ""

                confidence = 0.0
                reasons = []

                # Check for SQL keywords
                if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP)\b', func_source, re.IGNORECASE):
                    confidence += 0.5
                    reasons.append("Contains SQL keywords")

                # Check for .execute() calls
                if '.execute(' in func_source:
                    confidence += 0.3
                    reasons.append("Calls .execute()")

                # Check for database libraries
                if 'sqlite' in func_source:
                    confidence += 0.2
                    reasons.append("Uses sqlite")
                elif 'sqlalchemy' in func_source:
                    confidence += 0.2
                    reasons.append("Uses SQLAlchemy")

                if confidence > 0.4:
                    snippet = self._extract_snippet(content, node.lineno)
                    matches.append(SemanticMatch(
                        symbol=node.name,
                        file=str(file_path.relative_to(self.project_root)),
                        line=node.lineno,
                        confidence=min(1.0, confidence),
                        reason=", ".join(reasons),
                        snippet=snippet,
                        behavior="database_queries"
                    ))

        return matches

    def _detect_file_io(
        self,
        file_path: Path,
        tree: ast.AST,
        content: str,
        pattern: BehaviorPattern
    ) -> List[SemanticMatch]:
        """Detect file I/O operations in code."""
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_source = ast.get_source_segment(content, node) or ""

                confidence = 0.0
                reasons = []

                # Check for open() calls
                if re.search(r'\bopen\(', func_source):
                    confidence += 0.4
                    reasons.append("Uses open()")

                # Check for Path operations
                if re.search(r'\bPath\([^)]*\)\.(read_text|write_text|read_bytes|write_bytes)', func_source):
                    confidence += 0.5
                    reasons.append("Uses Path read/write methods")

                # Check for file methods
                if re.search(r'\.(read|write|readline|readlines)\(', func_source):
                    confidence += 0.3
                    reasons.append("Uses file read/write methods")

                # Check for with open pattern
                if 'with open' in func_source:
                    confidence += 0.2
                    reasons.append("Uses context manager for files")

                if confidence > 0.3:
                    snippet = self._extract_snippet(content, node.lineno)
                    matches.append(SemanticMatch(
                        symbol=node.name,
                        file=str(file_path.relative_to(self.project_root)),
                        line=node.lineno,
                        confidence=min(1.0, confidence),
                        reason=", ".join(reasons),
                        snippet=snippet,
                        behavior="file_io"
                    ))

        return matches

    def _detect_async_operations(
        self,
        file_path: Path,
        tree: ast.AST,
        content: str,
        pattern: BehaviorPattern
    ) -> List[SemanticMatch]:
        """Detect async operations in code."""
        matches = []

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                func_source = ast.get_source_segment(content, node) or ""

                confidence = 0.7  # Base confidence for being async
                reasons = ["Is async function"]

                # Check for await calls
                await_count = func_source.count('await')
                if await_count > 0:
                    confidence += min(0.3, await_count * 0.1)
                    reasons.append(f"Contains {await_count} await calls")

                snippet = self._extract_snippet(content, node.lineno)
                matches.append(SemanticMatch(
                    symbol=node.name,
                    file=str(file_path.relative_to(self.project_root)),
                    line=node.lineno,
                    confidence=min(1.0, confidence),
                    reason=", ".join(reasons),
                    snippet=snippet,
                    behavior="async_operations"
                ))

        return matches

    def _detect_logging(
        self,
        file_path: Path,
        tree: ast.AST,
        content: str,
        pattern: BehaviorPattern
    ) -> List[SemanticMatch]:
        """Detect logging operations in code."""
        matches = []

        # Check for logging imports
        has_logging = 'logging' in content or 'logger' in content

        if not has_logging:
            return matches

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_source = ast.get_source_segment(content, node) or ""

                confidence = 0.0
                reasons = []

                # Check for logger method calls
                log_methods = ['debug', 'info', 'warning', 'error', 'critical']
                found_methods = [m for m in log_methods if f'.{m}(' in func_source]

                if found_methods:
                    confidence += 0.5
                    reasons.append(f"Calls logger.{', '.join(found_methods)}")

                # Check for logging.* calls
                if re.search(r'logging\.(debug|info|warning|error|critical)', func_source):
                    confidence += 0.3
                    reasons.append("Uses logging module")

                if confidence > 0.3:
                    snippet = self._extract_snippet(content, node.lineno)
                    matches.append(SemanticMatch(
                        symbol=node.name,
                        file=str(file_path.relative_to(self.project_root)),
                        line=node.lineno,
                        confidence=min(1.0, confidence),
                        reason=", ".join(reasons),
                        snippet=snippet,
                        behavior="logging"
                    ))

        return matches

    def _detect_data_validation(
        self,
        file_path: Path,
        tree: ast.AST,
        content: str,
        pattern: BehaviorPattern
    ) -> List[SemanticMatch]:
        """Detect data validation in code."""
        matches = []

        # Check for validation-related imports
        has_dataclass = '@dataclass' in content
        has_pydantic = 'pydantic' in content
        has_validation = 'validate' in content.lower()

        if not (has_dataclass or has_pydantic or has_validation):
            return matches

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                func_source = ast.get_source_segment(content, node) or ""

                confidence = 0.0
                reasons = []

                # Check for dataclass decorator
                if '@dataclass' in func_source and isinstance(node, ast.ClassDef):
                    confidence += 0.5
                    reasons.append("Uses @dataclass")

                # Check for pydantic
                if 'BaseModel' in func_source:
                    confidence += 0.5
                    reasons.append("Inherits from Pydantic BaseModel")

                # Check for validation keywords
                if re.search(r'\b(validate|validator|validation)\b', func_source, re.IGNORECASE):
                    confidence += 0.3
                    reasons.append("Contains validation logic")

                if confidence > 0.4:
                    snippet = self._extract_snippet(content, node.lineno)
                    matches.append(SemanticMatch(
                        symbol=node.name,
                        file=str(file_path.relative_to(self.project_root)),
                        line=node.lineno,
                        confidence=min(1.0, confidence),
                        reason=", ".join(reasons),
                        snippet=snippet,
                        behavior="data_validation"
                    ))

        return matches

    def _extract_snippet(self, content: str, line_num: int, context: int = 2) -> str:
        """Extract code snippet around line number."""
        lines = content.split('\n')
        start = max(0, line_num - context - 1)
        end = min(len(lines), line_num + context)
        snippet = '\n'.join(lines[start:end])
        return snippet.strip()


def search_by_behavior(
    project_root: Path,
    query: str,
    scope: Optional[str] = None,
    limit: int = 15
) -> SemanticSearchResult:
    """
    Convenience function to search by behavior.

    Args:
        project_root: Root directory of project
        query: Natural language behavior description
        scope: Optional path scope
        limit: Max matches to return

    Returns:
        SemanticSearchResult object
    """
    engine = SemanticSearchEngine(project_root)
    return engine.search(query, scope, limit)
