from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal

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
    type: Literal["function", "class", "method", "variable"]
    file_path: str
    start_line: int
    end_line: int
    signature: Optional[str] = None

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
