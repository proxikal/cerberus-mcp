"""Syntax validation utilities."""
import ast
from typing import Optional, Tuple


def validate_syntax(code: str, file_extension: str = ".py") -> Tuple[bool, Optional[str]]:
    """
    Validate code syntax for common languages.

    Args:
        code: Code to validate
        file_extension: File type for language detection

    Returns:
        (is_valid, error_message)
    """
    if file_extension in [".py", ""]:
        return _validate_python(code)
    if file_extension in [".js", ".jsx"]:
        return _validate_javascript(code)
    if file_extension in [".ts", ".tsx"]:
        return _validate_typescript(code)

    # Unknown language - assume valid
    return True, None


def _validate_python(code: str) -> Tuple[bool, Optional[str]]:
    """Validate Python syntax using AST."""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"


def _validate_javascript(code: str) -> Tuple[bool, Optional[str]]:
    """Basic JavaScript syntax check via balanced delimiters."""
    try:
        braces = parens = brackets = 0
        in_string = False
        string_char = None

        for char in code:
            if in_string:
                if char == string_char:
                    in_string = False
            else:
                if char in '"\'`':
                    in_string = True
                    string_char = char
                elif char == "{":
                    braces += 1
                elif char == "}":
                    braces -= 1
                elif char == "(":
                    parens += 1
                elif char == ")":
                    parens -= 1
                elif char == "[":
                    brackets += 1
                elif char == "]":
                    brackets -= 1

        if braces != 0 or parens != 0 or brackets != 0:
            return False, "Unbalanced brackets/braces/parentheses"

        return True, None
    except Exception as e:
        return False, str(e)


def _validate_typescript(code: str) -> Tuple[bool, Optional[str]]:
    """Basic TypeScript syntax check (same heuristic as JS)."""
    return _validate_javascript(code)
