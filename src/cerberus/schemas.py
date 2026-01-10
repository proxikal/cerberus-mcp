from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal, Any

class FileObject(BaseModel):
    """
    Represents a file found in the codebase.
    """
    path: str
    abs_path: str
    size: int
    last_modified: float

class CodeSymbol(BaseModel):
    """
    Represents a code symbol (function, class, etc.) extracted from a file.
    """
    name: str
    type: Literal["function", "class", "method", "variable", "interface", "enum", "struct"]
    file_path: str
    start_line: int
    end_line: int
    signature: Optional[str] = None
    # Phase 1.2: Type-aware resolution
    return_type: Optional[str] = None  # Return type annotation/hint
    parameters: Optional[List[str]] = None  # Parameter names
    parent_class: Optional[str] = None  # For methods, the containing class

class ImportReference(BaseModel):
    """
    Represents an import statement in a file.
    """
    module: str
    file_path: str
    line: int

class CallReference(BaseModel):
    """
    Represents a function call within a file.
    """
    caller_file: str
    callee: str
    line: int

class CodeSnippet(BaseModel):
    """
    Represents a slice of code around a symbol with padding for context.
    """
    file_path: str
    start_line: int
    end_line: int
    content: str

class SymbolEmbedding(BaseModel):
    """
    Represents a precomputed embedding for a symbol.
    """
    name: str
    file_path: str
    vector: List[float]

class ScanResult(BaseModel):
    """
    Summary of a scan operation.
    """
    total_files: int
    files: List[FileObject]
    scan_duration: float
    symbols: List[CodeSymbol] = Field(default_factory=list)
    embeddings: List[SymbolEmbedding] = Field(default_factory=list)
    imports: List[ImportReference] = Field(default_factory=list)
    calls: List[CallReference] = Field(default_factory=list)
    # Phase 1.2: Type information
    type_infos: List["TypeInfo"] = Field(default_factory=list)
    # Phase 1.3: Import linkage
    import_links: List["ImportLink"] = Field(default_factory=list)
    # Phase 5: Symbolic intelligence
    method_calls: List["MethodCall"] = Field(default_factory=list)
    symbol_references: List["SymbolReference"] = Field(default_factory=list)
    # Phase 3: Metadata (git commit, etc.)
    project_root: str = ""  # Root path of project
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Additional metadata (git_commit, etc.)

class IndexStats(BaseModel):
    """
    Aggregate statistics for an index.
    """
    total_files: int
    total_symbols: int
    symbol_types: Dict[str, int] = Field(default_factory=dict)
    average_symbols_per_file: float


class SearchResult(BaseModel):
    """
    Represents a semantic search hit.
    """
    symbol: CodeSymbol
    score: float
    snippet: CodeSnippet


# Phase 1: Advanced Dependency Intelligence Schemas

class TypeInfo(BaseModel):
    """
    Represents type information for a symbol (variable, parameter, return type).
    """
    name: str  # Variable or parameter name
    type_annotation: Optional[str] = None  # The type hint/annotation
    inferred_type: Optional[str] = None  # Inferred from assignments
    file_path: str
    line: int


class ImportLink(BaseModel):
    """
    Represents an explicit link between an import statement and the symbols it provides.
    """
    importer_file: str  # File that imports
    imported_module: str  # Module being imported
    imported_symbols: List[str] = Field(default_factory=list)  # Specific symbols imported (e.g., from X import Y)
    import_line: int
    # Optional: link to definition location if internal to project
    definition_file: Optional[str] = None
    definition_symbol: Optional[str] = None


class CallGraphNode(BaseModel):
    """
    Represents a node in the recursive call graph.
    """
    symbol_name: str
    file_path: str
    line: int
    depth: int = 0  # Depth in the call graph (0 = target symbol, 1 = direct caller, etc.)
    callers: List["CallGraphNode"] = Field(default_factory=list)  # Recursive structure


class CallGraphResult(BaseModel):
    """
    Complete call graph starting from a target symbol.
    """
    target_symbol: str
    max_depth: int
    root_node: Optional[CallGraphNode] = None
    total_nodes: int = 0


# Enable forward references for recursive CallGraphNode
CallGraphNode.model_rebuild()


# Phase 2: Context Synthesis & Compaction Schemas

class SkeletonizedCode(BaseModel):
    """
    Represents code with implementation removed, preserving structure.
    """
    file_path: str
    original_lines: int
    skeleton_lines: int
    content: str  # Skeletonized source code
    preserved_symbols: List[str] = Field(default_factory=list)  # Symbols with full implementation kept
    pruned_symbols: List[str] = Field(default_factory=list)  # Symbols that were skeletonized
    compression_ratio: float  # skeleton_lines / original_lines


class ContextPayload(BaseModel):
    """
    Synthesized context payload for a target symbol.
    Complete context package with target implementation, skeleton context, and resolved imports.
    """
    target_symbol: CodeSymbol
    target_implementation: str  # Full implementation of target
    skeleton_context: List[SkeletonizedCode] = Field(default_factory=list)  # Surrounding skeletons
    resolved_imports: List[CodeSymbol] = Field(default_factory=list)  # Imported symbols with implementations
    call_graph: Optional[CallGraphResult] = None  # Recursive call graph
    type_context: List[TypeInfo] = Field(default_factory=list)  # Relevant type definitions
    total_lines: int = 0
    estimated_tokens: int = 0  # Rough token count
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Additional context metadata


class CodeSummary(BaseModel):
    """
    LLM-generated summary of code or architecture.
    """
    target: str  # File path or symbol name
    summary_type: Literal["file", "symbol", "architecture", "layer"]
    summary_text: str  # Natural language summary
    key_points: List[str] = Field(default_factory=list)  # Bullet points of key functionality
    dependencies: List[str] = Field(default_factory=list)  # Major dependencies identified
    complexity_score: Optional[int] = None  # 1-10 complexity rating
    generated_at: float = 0.0  # Timestamp
    model_used: str = "unknown"  # LLM model identifier


# Phase 3: Operational Excellence Schemas

class LineRange(BaseModel):
    """
    Represents a range of modified lines in a file.
    """
    start: int
    end: int
    change_type: Literal["added", "modified", "deleted"]


class ModifiedFile(BaseModel):
    """
    Represents a file that was modified with line ranges.
    """
    path: str
    changed_lines: List[LineRange] = Field(default_factory=list)
    affected_symbols: List[str] = Field(default_factory=list)  # Symbols that need re-parsing


class FileChange(BaseModel):
    """
    Represents detected changes from git diff or filesystem monitoring.
    """
    added: List[str] = Field(default_factory=list)  # New files
    modified: List[ModifiedFile] = Field(default_factory=list)  # Changed files with line ranges
    deleted: List[str] = Field(default_factory=list)  # Removed files
    timestamp: float  # When changes were detected


class IncrementalUpdateResult(BaseModel):
    """
    Result of an incremental index update.
    """
    updated_symbols: List[CodeSymbol] = Field(default_factory=list)  # Symbols that were updated
    removed_symbols: List[str] = Field(default_factory=list)  # Symbols that were removed
    affected_callers: List[str] = Field(default_factory=list)  # Callers that were re-analyzed
    files_reparsed: int = 0
    elapsed_time: float = 0.0
    strategy: Literal["full_reparse", "surgical", "incremental", "failed"] = "incremental"


class WatcherStatus(BaseModel):
    """
    Status of the background watcher daemon.
    """
    running: bool
    pid: Optional[int] = None
    watching: Optional[str] = None  # Project path being watched
    index_path: Optional[str] = None
    uptime: Optional[float] = None  # Seconds since start
    last_update: Optional[float] = None  # Timestamp of last index update
    events_processed: int = 0  # Total filesystem events handled
    updates_triggered: int = 0  # Number of index updates triggered


class HybridSearchResult(BaseModel):
    """
    Search result with hybrid BM25 + Vector ranking.
    """
    symbol: CodeSymbol
    bm25_score: float  # Keyword relevance (0-1)
    vector_score: float  # Semantic similarity (0-1)
    hybrid_score: float  # Combined score (0-1)
    rank: int  # Final ranking position
    match_type: Literal["keyword", "semantic", "both"]


# Phase 5: Symbolic Intelligence Schemas

class MethodCall(BaseModel):
    """
    Represents a method call on an object/instance.
    Phase 5.1: Extract method calls with receiver information.
    """
    caller_file: str  # File containing the call
    line: int  # Line number of the call
    receiver: str  # Object/variable name (e.g., 'optimizer')
    method: str  # Method name (e.g., 'step')
    receiver_type: Optional[str] = None  # Resolved class name (populated later)


class SymbolReference(BaseModel):
    """
    Represents a resolved reference from a symbol usage to its definition.
    Phase 5.2+: Track instance→definition relationships.
    """
    source_file: str  # File containing the reference
    source_line: int  # Line of the reference
    source_symbol: str  # Variable/receiver name
    reference_type: Literal["method_call", "instance_of", "inherits", "type_annotation", "return_type"]
    target_file: Optional[str] = None  # Resolved definition file
    target_symbol: Optional[str] = None  # Resolved symbol name
    target_type: Optional[str] = None  # Class/type name
    confidence: float = 1.0  # Resolution confidence (0.0-1.0)
    resolution_method: Optional[str] = None  # How it was resolved: "import_trace", "type_annotation", "inference"


# Phase 11: Symbolic Editing (Mutation) Schemas

class SymbolLocation(BaseModel):
    """
    Precise AST-based symbol location with byte ranges.
    Phase 11: Enable surgical edits by symbol name.
    """
    file_path: str
    symbol_name: str
    symbol_type: str  # "function", "class", "method", etc.
    start_byte: int  # Exact byte offset where symbol starts
    end_byte: int  # Exact byte offset where symbol ends
    start_line: int  # Line number (1-indexed)
    end_line: int  # Line number (1-indexed)
    indentation_level: int  # Number of indentation units
    language: str  # "python", "javascript", "typescript"
    parent_class: Optional[str] = None  # For methods, the containing class


class MutationResult(BaseModel):
    """
    Result of a mutation operation (edit/insert/delete).
    Phase 11: Track write efficiency and validation status.
    Phase 12: Add diff output for agent feedback.
    """
    success: bool
    operation: Literal["edit", "insert", "delete"]
    file_path: str
    symbol_name: str
    lines_changed: int  # Number of lines modified
    lines_total: int  # Total lines in file
    write_efficiency: float  # lines_changed / lines_total
    tokens_saved: int  # Estimated tokens saved vs full rewrite
    validation_passed: bool  # Did syntax/semantic validation pass
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    backup_path: Optional[str] = None  # Path to backup file if created
    diff: Optional[str] = None  # Phase 12: Unified diff output


class DiffMetric(BaseModel):
    """
    Write efficiency tracking metric for mutation operations.
    Phase 11: Measure token savings and edit precision.
    """
    timestamp: float
    operation: str  # "edit", "insert", "delete"
    file_path: str
    lines_changed: int
    lines_total: int
    write_efficiency: float  # lines_changed / lines_total
    tokens_saved: int  # vs full file rewrite


# Phase 12: Batch Editing Schemas
class EditOperation(BaseModel):
    """
    A single edit operation in a batch.
    Phase 12: Atomic multi-edit transactions.
    Phase 13.2: Symbol Guard integration with force override.
    """
    operation: Literal["edit", "insert", "delete"]
    file_path: str
    symbol_name: str
    new_code: Optional[str] = None  # Required for edit/insert
    symbol_type: Optional[str] = None
    parent_class: Optional[str] = None
    parent_symbol: Optional[str] = None  # For insert operations
    after_symbol: Optional[str] = None  # For insert operations
    before_symbol: Optional[str] = None  # For insert operations
    auto_format: bool = True
    auto_imports: bool = True
    force: bool = False  # Phase 13.2: Bypass Symbol Guard protection


class BatchEditResult(BaseModel):
    """
    Result of a batch edit operation.
    Phase 12: Atomic transaction results with rollback capability.
    """
    success: bool
    operations_completed: int
    operations_total: int
    results: List[MutationResult]
    errors: List[str] = Field(default_factory=list)
    rolled_back: bool = False  # True if transaction was rolled back
