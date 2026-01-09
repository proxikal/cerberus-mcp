"""
Configuration for Phase 5: Symbolic Intelligence resolution.

Defines confidence thresholds, resolution strategies, and settings.
"""

# Resolution confidence thresholds
CONFIDENCE_THRESHOLDS = {
    "import_trace": 1.0,        # Direct import resolution (deterministic)
    "type_annotation": 0.9,     # Explicit type hints
    "class_instantiation": 0.85,  # Variable assignment to class constructor
    "parameter_inference": 0.7,   # Inferred from parameter usage patterns
    "heuristic": 0.5,           # Naming pattern heuristics
}

# Resolution strategies (in order of precedence)
RESOLUTION_STRATEGIES = [
    "import_trace",       # Follow import statements to definitions
    "type_annotation",    # Use explicit type hints
    "class_instantiation",  # Track class() assignments
    # Future strategies can be added here
]

# Symbol resolution settings
RESOLUTION_CONFIG = {
    "max_depth": 3,              # Maximum depth for recursive resolution
    "min_confidence": 0.5,       # Minimum confidence to store reference
    "resolve_external": False,   # Whether to attempt external library resolution
    "strict_mode": False,        # Fail on ambiguous resolutions vs. best-effort
}

# Module path normalization patterns
# Used to normalize import paths (e.g., relative imports)
MODULE_PATTERNS = {
    "relative_import": r"^\.+",  # Matches relative imports like ".module" or "..utils"
    "package_import": r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z0-9_]+)*$",  # Matches standard package paths
}
