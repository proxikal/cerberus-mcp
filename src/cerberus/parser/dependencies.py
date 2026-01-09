import re
from pathlib import Path
from typing import List

from cerberus.schemas import CallReference, ImportReference, ImportLink, MethodCall

# Basic regex patterns for imports and calls. These are intentionally lightweight to keep context small.
PY_IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z0-9_.]+)\s+import|import\s+([A-Za-z0-9_.]+))", re.MULTILINE)
JS_IMPORT_RE = re.compile(r"^\s*import\s+.*?from\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
GO_IMPORT_RE = re.compile(r'^\s*import\s+"([^"]+)"', re.MULTILINE)
CALL_RE = re.compile(r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)

# Phase 1.3: Enhanced import patterns for symbol tracking
PY_FROM_IMPORT_SYMBOLS = re.compile(r"^\s*from\s+([A-Za-z0-9_.]+)\s+import\s+(.+)", re.MULTILINE)
PY_IMPORT_AS = re.compile(r"^\s*import\s+([A-Za-z0-9_.]+)(?:\s+as\s+([A-Za-z_][A-Za-z0-9_]*))?", re.MULTILINE)
TS_NAMED_IMPORTS = re.compile(r"^\s*import\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
TS_DEFAULT_IMPORT = re.compile(r"^\s*import\s+([A-Za-z_][A-Za-z0-9_]*)\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
GO_IMPORT_ALIAS = re.compile(r'^\s*import\s+(?:([A-Za-z_][A-Za-z0-9_]*)\s+)?"([^"]+)"', re.MULTILINE)

# Phase 5.1: Method call extraction patterns
# Matches: obj.method(), self.method(), instance.attr.method(), etc.
# Captures receiver (everything before last dot) and method name
METHOD_CALL_RE = re.compile(
    r"(?P<receiver>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\.(?P<method>[A-Za-z_][A-Za-z0-9_]*)\s*\(",
    re.MULTILINE
)


def extract_imports(file_path: Path, content: str) -> List[ImportReference]:
    imports: List[ImportReference] = []
    if file_path.suffix == ".py":
        for match in PY_IMPORT_RE.finditer(content):
            module = match.group(1) or match.group(2)
            line_number = content.count("\n", 0, match.start()) + 1
            imports.append(ImportReference(module=module, file_path=str(file_path), line=line_number))
    elif file_path.suffix in {".js", ".ts"}:
        for match in JS_IMPORT_RE.finditer(content):
            module = match.group(1)
            line_number = content.count("\n", 0, match.start()) + 1
            imports.append(ImportReference(module=module, file_path=str(file_path), line=line_number))
    elif file_path.suffix == ".go":
        for match in GO_IMPORT_RE.finditer(content):
            module = match.group(1)
            line_number = content.count("\n", 0, match.start()) + 1
            imports.append(ImportReference(module=module, file_path=str(file_path), line=line_number))
    return imports


def extract_calls(file_path: Path, content: str) -> List[CallReference]:
    """
    Very lightweight call detection: captures function-like tokens followed by '('.
    Excludes def/class/interface/enum signatures to reduce false positives.
    """
    calls: List[CallReference] = []
    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        # skip signature/definition lines
        if re.match(r"\s*(def |class |interface |enum |export |func )", line):
            continue
        for match in CALL_RE.finditer(line):
            callee = match.group("name")
            calls.append(CallReference(caller_file=str(file_path), callee=callee, line=idx))
    return calls


def extract_import_links(file_path: Path, content: str) -> List[ImportLink]:
    """
    Extract detailed import information including specific symbols imported.

    Phase 1.3: Import Linkage Enhancement.

    Args:
        file_path: Path to the file.
        content: File content as string.

    Returns:
        List of ImportLink objects with detailed symbol information.
    """
    import_links: List[ImportLink] = []
    file_str = str(file_path)

    if file_path.suffix == ".py":
        # from X import Y, Z
        for match in PY_FROM_IMPORT_SYMBOLS.finditer(content):
            module = match.group(1)
            symbols_str = match.group(2)
            line_num = content.count("\n", 0, match.start()) + 1

            # Parse imported symbols (handle 'as' aliases and multiple imports)
            symbols = []
            for part in symbols_str.split(','):
                part = part.strip()
                if ' as ' in part:
                    symbol = part.split(' as ')[0].strip()
                else:
                    symbol = part
                if symbol and symbol != '(':
                    symbols.append(symbol)

            import_links.append(ImportLink(
                importer_file=file_str,
                imported_module=module,
                imported_symbols=symbols,
                import_line=line_num,
            ))

        # import X as Y
        for match in PY_IMPORT_AS.finditer(content):
            module = match.group(1)
            line_num = content.count("\n", 0, match.start()) + 1

            import_links.append(ImportLink(
                importer_file=file_str,
                imported_module=module,
                imported_symbols=[],  # Full module import
                import_line=line_num,
            ))

    elif file_path.suffix in {".js", ".ts", ".tsx"}:
        # import { A, B } from 'module'
        for match in TS_NAMED_IMPORTS.finditer(content):
            symbols_str = match.group(1)
            module = match.group(2)
            line_num = content.count("\n", 0, match.start()) + 1

            symbols = [s.strip().split(' as ')[0].strip() for s in symbols_str.split(',')]

            import_links.append(ImportLink(
                importer_file=file_str,
                imported_module=module,
                imported_symbols=symbols,
                import_line=line_num,
            ))

        # import X from 'module'
        for match in TS_DEFAULT_IMPORT.finditer(content):
            symbol = match.group(1)
            module = match.group(2)
            line_num = content.count("\n", 0, match.start()) + 1

            import_links.append(ImportLink(
                importer_file=file_str,
                imported_module=module,
                imported_symbols=[symbol],
                import_line=line_num,
            ))

    elif file_path.suffix == ".go":
        # import alias "package/path"
        for match in GO_IMPORT_ALIAS.finditer(content):
            alias = match.group(1)
            module = match.group(2)
            line_num = content.count("\n", 0, match.start()) + 1

            import_links.append(ImportLink(
                importer_file=file_str,
                imported_module=module,
                imported_symbols=[alias] if alias else [],
                import_line=line_num,
            ))

    return import_links


def extract_method_calls(file_path: Path, content: str) -> List[MethodCall]:
    """
    Extract method calls with receiver information.

    Phase 5.1: Method Call Extraction.

    Captures patterns like:
    - obj.method()
    - self.method()
    - instance.attr.method()  (chained)
    - module.Class.method()

    Args:
        file_path: Path to the file.
        content: File content as string.

    Returns:
        List of MethodCall objects with receiver and method information.
    """
    method_calls: List[MethodCall] = []
    file_str = str(file_path)

    # Process line by line to get accurate line numbers
    lines = content.splitlines()
    for line_idx, line in enumerate(lines, start=1):
        # Skip definition/signature lines (same as extract_calls)
        if re.match(r"\s*(def |class |interface |enum |export |func )", line):
            continue

        # Find all method calls on this line
        for match in METHOD_CALL_RE.finditer(line):
            receiver = match.group("receiver")
            method = match.group("method")

            # For chained calls like "obj.attr.method()", we want just the immediate receiver
            # For now, keep the full chain as receiver
            method_calls.append(MethodCall(
                caller_file=file_str,
                line=line_idx,
                receiver=receiver,
                method=method,
            ))

    return method_calls
