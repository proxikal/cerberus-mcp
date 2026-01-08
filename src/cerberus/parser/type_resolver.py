"""
Type resolution and extraction for cross-file type tracking.

Part of Phase 1.2: Type-Aware Resolution.
"""

import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from cerberus.logging_config import logger
from cerberus.schemas import TypeInfo


# Python type extraction patterns
PYTHON_FUNCTION_WITH_RETURN = re.compile(
    r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*->\s*([^:]+):",
    re.MULTILINE
)
PYTHON_FUNCTION_PARAMS = re.compile(
    r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)",
    re.MULTILINE
)
PYTHON_VARIABLE_ANNOTATION = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_\[\],\s\.]+)\s*=",
    re.MULTILINE
)
PYTHON_CLASS_INSTANCE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z_][A-Za-z0-9_\.]+)\(",
    re.MULTILINE
)

# TypeScript type extraction patterns
TS_FUNCTION_WITH_RETURN = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*:\s*([^{]+)\s*\{",
    re.MULTILINE
)
TS_VARIABLE_ANNOTATION = re.compile(
    r"^\s*(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_<>,\[\]\s\.]+)\s*=",
    re.MULTILINE
)
TS_CLASS_INSTANCE = re.compile(
    r"^\s*(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*new\s+([A-Za-z_][A-Za-z0-9_\.]+)\(",
    re.MULTILINE
)

# Go type extraction patterns
GO_FUNCTION_WITH_RETURN = re.compile(
    r"^\s*func\s+(?:\([^)]+\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s+([^{]+)\s*\{",
    re.MULTILINE
)
GO_VARIABLE_DECLARATION = re.compile(
    r"^\s*var\s+([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_\.\*\[\]]+)",
    re.MULTILINE
)
GO_SHORT_VAR_DECLARATION = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:=\s*([A-Za-z_][A-Za-z0-9_\.]+)\{",
    re.MULTILINE
)


def extract_python_types(file_path: Path, content: str) -> List[TypeInfo]:
    """
    Extract type information from Python code.

    Extracts:
    - Function return types (from -> annotations)
    - Variable type hints (from : annotations)
    - Class instantiations (from = ClassName() patterns)

    Args:
        file_path: Path to the Python file.
        content: File content as string.

    Returns:
        List of TypeInfo objects.
    """
    type_infos: List[TypeInfo] = []

    # Function return types
    for match in PYTHON_FUNCTION_WITH_RETURN.finditer(content):
        func_name = match.group(1)
        return_type = match.group(3).strip()
        line_num = content.count('\n', 0, match.start()) + 1

        type_infos.append(
            TypeInfo(
                name=func_name,
                type_annotation=return_type,
                file_path=str(file_path),
                line=line_num,
            )
        )

    # Variable type annotations
    for match in PYTHON_VARIABLE_ANNOTATION.finditer(content):
        var_name = match.group(1)
        var_type = match.group(2).strip()
        line_num = content.count('\n', 0, match.start()) + 1

        type_infos.append(
            TypeInfo(
                name=var_name,
                type_annotation=var_type,
                file_path=str(file_path),
                line=line_num,
            )
        )

    # Class instantiations (inferred types)
    for match in PYTHON_CLASS_INSTANCE.finditer(content):
        var_name = match.group(1)
        class_name = match.group(2)
        line_num = content.count('\n', 0, match.start()) + 1

        type_infos.append(
            TypeInfo(
                name=var_name,
                inferred_type=class_name,
                file_path=str(file_path),
                line=line_num,
            )
        )

    logger.debug(f"Extracted {len(type_infos)} type hints from Python file {file_path}")
    return type_infos


def extract_typescript_types(file_path: Path, content: str) -> List[TypeInfo]:
    """
    Extract type information from TypeScript code.

    Extracts:
    - Function return types
    - Variable type annotations
    - Class instantiations

    Args:
        file_path: Path to the TypeScript file.
        content: File content as string.

    Returns:
        List of TypeInfo objects.
    """
    type_infos: List[TypeInfo] = []

    # Function return types
    for match in TS_FUNCTION_WITH_RETURN.finditer(content):
        func_name = match.group(1)
        return_type = match.group(3).strip()
        line_num = content.count('\n', 0, match.start()) + 1

        type_infos.append(
            TypeInfo(
                name=func_name,
                type_annotation=return_type,
                file_path=str(file_path),
                line=line_num,
            )
        )

    # Variable type annotations
    for match in TS_VARIABLE_ANNOTATION.finditer(content):
        var_name = match.group(1)
        var_type = match.group(2).strip()
        line_num = content.count('\n', 0, match.start()) + 1

        type_infos.append(
            TypeInfo(
                name=var_name,
                type_annotation=var_type,
                file_path=str(file_path),
                line=line_num,
            )
        )

    # Class instantiations
    for match in TS_CLASS_INSTANCE.finditer(content):
        var_name = match.group(1)
        class_name = match.group(2)
        line_num = content.count('\n', 0, match.start()) + 1

        type_infos.append(
            TypeInfo(
                name=var_name,
                inferred_type=class_name,
                file_path=str(file_path),
                line=line_num,
            )
        )

    logger.debug(f"Extracted {len(type_infos)} type hints from TypeScript file {file_path}")
    return type_infos


def extract_go_types(file_path: Path, content: str) -> List[TypeInfo]:
    """
    Extract type information from Go code.

    Extracts:
    - Function return types
    - Variable declarations
    - Short variable declarations

    Args:
        file_path: Path to the Go file.
        content: File content as string.

    Returns:
        List of TypeInfo objects.
    """
    type_infos: List[TypeInfo] = []

    # Function return types
    for match in GO_FUNCTION_WITH_RETURN.finditer(content):
        func_name = match.group(1)
        return_type = match.group(3).strip()
        line_num = content.count('\n', 0, match.start()) + 1

        type_infos.append(
            TypeInfo(
                name=func_name,
                type_annotation=return_type,
                file_path=str(file_path),
                line=line_num,
            )
        )

    # Variable declarations
    for match in GO_VARIABLE_DECLARATION.finditer(content):
        var_name = match.group(1)
        var_type = match.group(2).strip()
        line_num = content.count('\n', 0, match.start()) + 1

        type_infos.append(
            TypeInfo(
                name=var_name,
                type_annotation=var_type,
                file_path=str(file_path),
                line=line_num,
            )
        )

    # Short variable declarations (inferred from struct initialization)
    for match in GO_SHORT_VAR_DECLARATION.finditer(content):
        var_name = match.group(1)
        struct_type = match.group(2)
        line_num = content.count('\n', 0, match.start()) + 1

        type_infos.append(
            TypeInfo(
                name=var_name,
                inferred_type=struct_type,
                file_path=str(file_path),
                line=line_num,
            )
        )

    logger.debug(f"Extracted {len(type_infos)} type hints from Go file {file_path}")
    return type_infos


def extract_types_from_file(file_path: Path, content: str) -> List[TypeInfo]:
    """
    Extract type information from a file based on its extension.

    Args:
        file_path: Path to the file.
        content: File content as string.

    Returns:
        List of TypeInfo objects.
    """
    ext = file_path.suffix.lower()

    if ext == ".py":
        return extract_python_types(file_path, content)
    elif ext in [".ts", ".tsx"]:
        return extract_typescript_types(file_path, content)
    elif ext == ".go":
        return extract_go_types(file_path, content)
    else:
        logger.debug(f"Type extraction not supported for {ext} files")
        return []


def build_type_map(type_infos: List[TypeInfo]) -> Dict[str, List[TypeInfo]]:
    """
    Build a mapping from variable/function names to their type information.

    Args:
        type_infos: List of TypeInfo objects.

    Returns:
        Dictionary mapping name -> list of TypeInfo (can have multiple definitions).
    """
    type_map: Dict[str, List[TypeInfo]] = {}

    for info in type_infos:
        if info.name not in type_map:
            type_map[info.name] = []
        type_map[info.name].append(info)

    return type_map


def resolve_type(
    var_name: str,
    file_path: str,
    type_map: Dict[str, List[TypeInfo]]
) -> Optional[str]:
    """
    Resolve the type of a variable in a given file.

    Args:
        var_name: Variable name to resolve.
        file_path: File where the variable is used.
        type_map: Map of variable names to their type information.

    Returns:
        The resolved type as a string, or None if not found.
    """
    candidates = type_map.get(var_name, [])

    # Prefer types from the same file
    for candidate in candidates:
        if candidate.file_path == file_path:
            return candidate.type_annotation or candidate.inferred_type

    # Fallback to any match
    for candidate in candidates:
        type_str = candidate.type_annotation or candidate.inferred_type
        if type_str:
            return type_str

    return None
