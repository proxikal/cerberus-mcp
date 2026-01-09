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

# Phase 6: Inheritance Resolution Configuration
INHERITANCE_CONFIG = {
    "max_mro_depth": 50,         # Maximum depth for method resolution order
    "track_multiple_inheritance": True,  # Support multiple inheritance (Python, C++)
    "resolve_mixins": True,      # Attempt to resolve mixin classes
    "confidence_direct": 1.0,    # Direct inheritance in same file
    "confidence_imported": 0.95,  # Inherited from imported class
    "confidence_external": 0.7,   # Inherited from external library
}

# Phase 6: Call Graph Configuration
CALL_GRAPH_CONFIG = {
    "max_depth": 10,             # Maximum recursion depth for call graphs
    "include_external": False,    # Include external library calls
    "track_dynamic_calls": True,  # Track dynamic method calls
}

# Phase 6: Context Assembly Configuration
CONTEXT_ASSEMBLY_CONFIG = {
    "include_base_classes": True,     # Include base class definitions
    "include_overridden_methods": True,  # Show methods that override base
    "max_inheritance_depth": 3,       # How many levels up to include
    "skeletonize_bases": True,        # Skeletonize base class bodies
}
