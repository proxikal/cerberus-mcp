# Phase 2: Context Synthesis & Compaction - Design Document

## Overview
Phase 2 transforms Cerberus from a "search and retrieve" engine into a **Deep Context Synthesis** system. It builds on Phase 1's dependency intelligence to deliver compact, perfectly-scoped context payloads.

## Goals
1. **Advanced Skeletonization:** AST-aware pruning to keep signatures/docstrings while removing implementation ✅ **CORE FEATURE**
2. **Payload Synthesis:** Intelligent merging of target code + skeleton context + resolved imports ✅ **CORE FEATURE**
3. **Auto-Summarization:** Local LLM integration for summarizing large files and architectural layers ⚠️ **LOW PRIORITY - FUTURE DEVELOPMENT**

**Note:** Cerberus is designed to provide context TO AI agents (Claude, Codex), not to use LLMs itself. Summarization features (3) are implemented but considered optional and low priority since the AI agents receiving context can perform their own analysis.

## Architecture Design

### 1. New Packages (Self-Similarity Mandate)

#### `cerberus/synthesis/`
Context synthesis and skeletonization logic.

**Files:**
- `facade.py` - Public API for synthesis operations
- `skeletonizer.py` - AST-aware code pruning
- `payload.py` - Payload assembly logic
- `config.py` - Synthesis configuration (padding, rules)
- `__init__.py` - Public exports

**API:**
```python
from cerberus.synthesis import skeletonize_file, build_payload

# Skeletonize a file (keep signatures, remove bodies)
skeleton = skeletonize_file(file_path, keep_docstrings=True)

# Build context payload for a symbol
payload = build_payload(
    target_symbol="process_user_data",
    index=index,
    include_callers=True,
    skeleton_depth=2
)
```

#### `cerberus/summarization/` ⚠️ **LOW PRIORITY - FUTURE DEVELOPMENT**
Local LLM-based summarization for large context.

**Note:** This module is implemented but marked as low priority. Cerberus's primary purpose is to provide context to AI agents, not to run its own LLMs. Most users will not need this feature.

**Files:**
- `facade.py` - Public API for summarization
- `local_llm.py` - Local LLM integration (ollama, llama.cpp)
- `config.py` - LLM configuration (model, parameters)
- `__init__.py` - Public exports

**API:**
```python
from cerberus.summarization import summarize_file, summarize_architecture

# Summarize a large file
summary = summarize_file(file_path, focus="data processing logic")

# Summarize architectural layer
summary = summarize_architecture(
    files=["auth/*.py", "middleware/*.py"],
    index=index
)
```

### 2. New Schemas

#### `SkeletonizedCode`
Represents code with implementation bodies removed.

```python
class SkeletonizedCode(BaseModel):
    """Code with implementation removed, preserving structure."""
    file_path: str
    original_lines: int
    skeleton_lines: int
    content: str  # Skeletonized source code
    preserved_symbols: List[str]  # Symbols with full implementation kept
    pruned_symbols: List[str]  # Symbols that were skeletonized
    compression_ratio: float  # skeleton_lines / original_lines
```

#### `ContextPayload`
Complete context package for a target symbol.

```python
class ContextPayload(BaseModel):
    """Synthesized context payload for a target symbol."""
    target_symbol: CodeSymbol
    target_implementation: str  # Full implementation of target
    skeleton_context: List[SkeletonizedCode]  # Surrounding skeletons
    resolved_imports: List[CodeSymbol]  # Imported symbols with implementations
    call_graph: Optional[CallGraphResult]  # Recursive call graph
    type_context: List[TypeInfo]  # Relevant type definitions
    total_lines: int
    estimated_tokens: int  # Rough token count
    metadata: Dict[str, Any]  # Additional context metadata
```

#### `CodeSummary`
LLM-generated summary of code or architecture.

```python
class CodeSummary(BaseModel):
    """AI-generated summary of code."""
    target: str  # File path or symbol name
    summary_type: Literal["file", "symbol", "architecture", "layer"]
    summary_text: str  # Natural language summary
    key_points: List[str]  # Bullet points of key functionality
    dependencies: List[str]  # Major dependencies identified
    complexity_score: Optional[int]  # 1-10 complexity rating
    generated_at: float  # Timestamp
    model_used: str  # LLM model identifier
```

### 3. Implementation Strategy

#### 3.1 Advanced Skeletonization

**Tree-Sitter Integration:**
- Use tree-sitter for accurate AST parsing
- Support Python, TypeScript, JavaScript, Go initially
- Extend to other languages incrementally

**Pruning Rules:**
- **Keep:** Function/method signatures, docstrings, type annotations, class definitions
- **Remove:** Function bodies (replace with `...` or `pass`), complex expressions
- **Preserve:** Constants, type definitions, important comments

**Example:**
```python
# Original
def process_user_data(user_id: int, data: Dict[str, Any]) -> UserProfile:
    """Process and validate user data, creating a profile."""
    validated_data = validate_schema(data)
    if not validated_data:
        raise ValidationError("Invalid data")
    profile = UserProfile(**validated_data)
    profile.user_id = user_id
    db.save(profile)
    return profile

# Skeletonized
def process_user_data(user_id: int, data: Dict[str, Any]) -> UserProfile:
    """Process and validate user data, creating a profile."""
    ...
```

#### 3.2 Payload Synthesis

**Context Assembly Algorithm:**
1. **Target Extraction:** Get full implementation of requested symbol
2. **Scope Analysis:** Identify surrounding class/module context
3. **Skeleton Generation:** Skeletonize the containing file (except target)
4. **Import Resolution:** Resolve and fetch imported symbols used by target
5. **Dependency Pruning:** Use Phase 1 call graph to include only relevant callers
6. **Assembly:** Merge all components into a single payload

**Smart Padding:**
- Include N lines before/after target for immediate context
- Skeletonize rest of the file
- Include docstrings of sibling methods in same class

**Token Budget Management:**
- Track estimated token count during assembly
- Prioritize: target > imports > callers > skeleton
- Truncate/summarize if exceeding budget

#### 3.3 Auto-Summarization

**Local LLM Integration:**
- Support ollama (recommended for local deployment)
- Support llama.cpp for direct model loading
- Fallback to API-based models if configured

**Summarization Use Cases:**
1. **File Summary:** Summarize a large file's purpose and key functions
2. **Symbol Summary:** Explain what a function/class does
3. **Architecture Summary:** Describe a subsystem or layer
4. **Dependency Summary:** Explain a module's dependencies and their roles

**Summarization Prompt Template:**
```
Analyze the following code and provide a concise summary.

Code:
{code_content}

Provide:
1. Primary purpose (1-2 sentences)
2. Key functions/classes (bullet points)
3. Major dependencies
4. Complexity assessment (1-10)
```

### 4. CLI Integration

#### New Commands

**`cerberus skeletonize`**
```bash
# Skeletonize a file
cerberus skeletonize path/to/file.py --output skeleton.py

# Skeletonize with exceptions (preserve specific functions)
cerberus skeletonize file.py --preserve "main,setup" --json

# Skeletonize entire directory
cerberus skeletonize src/ --output-dir skeletons/
```

**`cerberus get-context`** (Enhanced get-symbol)
```bash
# Get synthesized context payload
cerberus get-context --symbol process_data --index project.json

# With token budget
cerberus get-context --symbol MyClass --max-tokens 2000 --json

# Include call graph
cerberus get-context --symbol handler --include-callers --depth 2
```

**`cerberus summarize`** ⚠️ **LOW PRIORITY - FUTURE DEVELOPMENT**
```bash
# Summarize a file (requires ollama - optional feature)
cerberus summarize src/auth/service.py

# Summarize a symbol
cerberus summarize --symbol AuthService --index project.json

# Summarize architecture layer
cerberus summarize --pattern "api/**/*.py" --type architecture
```

**Note:** Summarization is a low-priority feature. Most users will not need this as AI agents can analyze context themselves.

#### Enhanced Existing Commands

**`cerberus get-symbol`**
Add `--skeleton-context` flag to include skeletonized surrounding code.

**`cerberus search`**
Add `--with-context` flag to return synthesized payloads instead of raw snippets.

### 5. Configuration

**`synthesis/config.py`**
```python
SKELETONIZATION_CONFIG = {
    "keep_docstrings": True,
    "keep_type_annotations": True,
    "keep_decorators": True,
    "replace_body_with": "...",  # Python: "...", JS: "/* ... */"
    "preserve_constants": True,
    "max_body_preview_lines": 2,  # Keep first N lines as preview
}

PAYLOAD_CONFIG = {
    "default_padding_lines": 5,
    "default_max_tokens": 4000,
    "include_sibling_methods": True,
    "skeleton_depth": 1,  # How many levels of imports to skeletonize
    "prioritize_callers": True,
}
```

**`summarization/config.py`**
```python
LLM_CONFIG = {
    "backend": "ollama",  # "ollama", "llamacpp", "api"
    "model": "llama2:7b",
    "temperature": 0.2,
    "max_tokens": 500,
    "timeout": 30,
}

SUMMARIZATION_CONFIG = {
    "chunk_size": 2000,  # Lines to summarize at once
    "min_lines_for_summary": 100,  # Don't summarize small files
    "include_complexity_score": True,
}
```

### 6. Testing Strategy

**Unit Tests (`tests/test_phase2.py`):**
- `TestSkeletonization` - AST pruning, signature preservation
- `TestPayloadSynthesis` - Context assembly, token budgeting
- `TestSummarization` - LLM integration (mocked)

**Integration Tests (`tests/test_phase2_integration.py`):**
- Full pipeline: index → skeletonize → synthesize
- CLI command tests
- Real file processing

**Test Data:**
- `tests/test_files/phase2_test.py` - Complex Python file for skeletonization
- `tests/test_files/phase2_test.ts` - TypeScript class for context synthesis

### 7. Dependencies

**New Dependencies:**
```
tree-sitter>=0.20.0
tree-sitter-python>=0.20.0
tree-sitter-javascript>=0.20.0
tree-sitter-typescript>=0.20.0
tree-sitter-go>=0.20.0
ollama-python>=0.1.0  # Optional, for local LLM
```

**Update `requirements.txt`:**
```bash
# Phase 2: Context Synthesis
tree-sitter>=0.20.0
tree-sitter-python>=0.20.0
tree-sitter-javascript>=0.20.0
tree-sitter-typescript>=0.20.0
tree-sitter-go>=0.20.0

# Phase 2: Summarization (Optional)
ollama-python>=0.1.0
```

### 8. Rollout Plan

#### Milestone 2.1: Skeletonization Foundation
- [ ] Set up tree-sitter integration
- [ ] Implement Python skeletonizer
- [ ] Add TypeScript/JavaScript skeletonizer
- [ ] CLI command: `cerberus skeletonize`
- [ ] Unit tests for skeletonization

#### Milestone 2.2: Payload Synthesis
- [ ] Implement payload assembly algorithm
- [ ] Add token budget management
- [ ] Integrate with Phase 1 call graphs and type resolution
- [ ] CLI command: `cerberus get-context`
- [ ] Integration tests for payload synthesis

#### Milestone 2.3: Auto-Summarization ⚠️ **LOW PRIORITY - FUTURE DEVELOPMENT**
**Note:** This milestone is implemented but marked as low priority. Cerberus is designed to provide context TO AI agents, not to use LLMs itself.

- [ ] Integrate ollama client
- [ ] Implement summarization prompt templates
- [ ] Add summarization for files, symbols, architecture
- [ ] CLI command: `cerberus summarize`
- [ ] Tests with mocked LLM responses

### 9. Success Criteria

Phase 2 is complete when:
1. ✅ Skeletonization reduces file size by 60-80% while preserving structure
2. ✅ Context payloads fit within configurable token budgets
3. ✅ Synthesized payloads include target + skeleton + resolved imports
4. ✅ Local LLM summarization works for files and symbols
5. ✅ All new commands support `--json` output
6. ✅ Comprehensive tests pass (unit + integration)
7. ✅ Documentation is complete
8. ✅ Cerberus can synthesize context for its own codebase (dogfooding)

### 10. Aegis Robustness Compliance

**Logging:**
- Structured logs for synthesis operations
- Performance tracing for skeletonization and LLM calls
- Agent-friendly JSON logs in `cerberus_agent.log`

**Error Handling:**
- `SkeletonizationError` - AST parsing failures
- `PayloadAssemblyError` - Context synthesis issues
- `SummarizationError` - LLM integration failures

**Doctor Integration:**
- Check tree-sitter installation: `cerberus doctor --check-treesitter`
- Check LLM availability: `cerberus doctor --check-llm`
- Validate Phase 2 index compatibility

---

**Date:** 2026-01-08
**Status:** Design Complete, Ready for Implementation
**Next Step:** Milestone 2.1 - Skeletonization Foundation
