"""
Configuration for context synthesis and skeletonization.
"""

# Skeletonization configuration
SKELETONIZATION_CONFIG = {
    "keep_docstrings": True,
    "keep_type_annotations": True,
    "keep_decorators": True,
    "keep_imports": True,
    "keep_class_attributes": True,
    "replace_body_with": "...",  # Python: "...", JS: "/* ... */", Go: "// ..."
    "preserve_constants": True,
    "max_body_preview_lines": 0,  # Keep first N lines of body as preview (0 = none)
    "min_lines_to_skeletonize": 3,  # Don't skeletonize very small functions
}

# Body replacement markers by language
BODY_REPLACEMENTS = {
    "python": "...",
    "javascript": "/* ... */",
    "typescript": "/* ... */",
    "go": "// ...",
}

# Payload synthesis configuration
PAYLOAD_CONFIG = {
    "default_padding_lines": 5,
    "default_max_tokens": 4000,
    "include_sibling_methods": True,
    "skeleton_depth": 1,  # How many levels of imports to skeletonize
    "prioritize_callers": True,
    "include_type_definitions": True,
    "estimate_tokens_per_line": 4,  # Rough token estimation
}

# Token budget priorities
TOKEN_PRIORITY = [
    "target_implementation",  # Always include the target
    "resolved_imports",       # Imported symbols
    "call_graph",            # Recursive call graph
    "skeleton_context",      # Surrounding skeletons
    "type_context",          # Type definitions
]
