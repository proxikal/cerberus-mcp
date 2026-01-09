"""
Resolution package for Phase 5 & 6: Symbolic Intelligence.

Provides import resolution, type tracking, inheritance resolution,
and symbol reference resolution.
"""

from .facade import (
    resolve_imports,
    resolve_types,
    resolve_inheritance,
    get_resolution_stats,
    compute_class_mro,
    get_class_descendants,
    get_overridden_methods,
    build_call_graph,
    infer_type,
    assemble_context,
)
from .resolver import ImportResolver
from .type_tracker import TypeTracker
from .inheritance_resolver import InheritanceResolver
from .mro_calculator import MROCalculator, InheritanceNode
from .call_graph_builder import CallGraphBuilder, CallGraph
from .type_inference import TypeInference, InferredType
from .context_assembler import ContextAssembler, AssembledContext
from .config import (
    CONFIDENCE_THRESHOLDS,
    RESOLUTION_CONFIG,
    INHERITANCE_CONFIG,
    CALL_GRAPH_CONFIG,
    CONTEXT_ASSEMBLY_CONFIG,
)

__all__ = [
    "resolve_imports",
    "resolve_types",
    "resolve_inheritance",
    "get_resolution_stats",
    "compute_class_mro",
    "get_class_descendants",
    "get_overridden_methods",
    "build_call_graph",
    "infer_type",
    "assemble_context",
    "ImportResolver",
    "TypeTracker",
    "InheritanceResolver",
    "MROCalculator",
    "InheritanceNode",
    "CallGraphBuilder",
    "CallGraph",
    "TypeInference",
    "InferredType",
    "ContextAssembler",
    "AssembledContext",
    "CONFIDENCE_THRESHOLDS",
    "RESOLUTION_CONFIG",
    "INHERITANCE_CONFIG",
    "CALL_GRAPH_CONFIG",
    "CONTEXT_ASSEMBLY_CONFIG",
]
