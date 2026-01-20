# Future Improvements for Cerberus MCP

**Focus**: Features that make Cerberus better for AI agents developing projects
**Scope**: Code understanding and navigation (NOT editing - that's covered by AI's native tooling)
**Date**: 2026-01-20

---

## 🎯 Top Tier Features (High Impact, Unique Value)

### 1. **Change Impact Analysis** ⭐⭐⭐⭐⭐

**What it does:**
Analyzes what would be affected if you modify a symbol.

**API:**
```python
cerberus.analyze_impact("ContextGenerator.generate_context")
```

**Returns:**
```json
{
  "direct_callers": 14,
  "transitive_callers": 47,
  "affected_tests": [
    "test_memory_integration.py::test_full_workflow",
    "test_memory_context.py::test_context_generation"
  ],
  "risk_score": "medium",
  "breaking_changes": [
    "Signature change would break 14 direct calls"
  ],
  "safe_to_modify": false,
  "recommendations": [
    "Consider deprecation path for signature changes",
    "Update tests in affected_tests list"
  ]
}
```

**Why this matters:**
- Right now AI agents have to manually trace call graphs
- This tells you "if you change this, here's what breaks"
- Makes refactoring safe and confident
- Prevents breaking changes

**Implementation:**
- Enhance existing call graph builder
- Map test files to implementation (parse test names)
- Calculate transitive dependencies
- Risk scoring based on caller count + test coverage
- **Difficulty**: 4-5 days

---

### 2. **Project Onboarding Summary** ⭐⭐⭐⭐⭐

**What it does:**
Generates a comprehensive project overview for AI agents starting a new session.

**API:**
```python
cerberus.project_summary()
```

**Returns:**
```json
{
  "tech_stack": ["Python 3.14", "FastMCP", "SQLite", "pytest"],
  "architecture": "MCP server with pluggable tools",
  "key_modules": {
    "mcp/": "MCP server and tool implementations",
    "retrieval/": "Symbol search and indexing",
    "memory/": "Session context management",
    "blueprint/": "Code structure visualization",
    "metrics/": "Efficiency tracking"
  },
  "entry_points": [
    "src/cerberus/mcp/server.py::create_server",
    "src/cerberus/index/index_builder.py::build_index"
  ],
  "coding_patterns": [
    "Use dataclasses for data structures",
    "Async/await for I/O operations",
    "Type hints required on all functions",
    "Docstrings use Google style"
  ],
  "dependencies": {
    "core": ["fastmcp", "tree-sitter"],
    "optional": ["ollama for summarization"]
  },
  "testing_approach": "pytest with fixtures in conftest.py",
  "token_estimate": 800
}
```

**Why this matters:**
- AI agents waste 5,000+ tokens exploring on every new session
- This gives the 80/20 in ~800 tokens
- Instant context on project structure and conventions
- Dramatically speeds up session startup

**Implementation:**
- Traverse index for file counts and module structure
- Parse pyproject.toml/requirements.txt for dependencies
- Extract patterns from existing code (imports, decorators, etc.)
- Identify main entry points
- Extract common coding patterns from git history
- **Difficulty**: 3-4 days

---

### 3. **Pattern Consistency Checker** ⭐⭐⭐⭐

**What it does:**
Checks if code follows established project patterns.

**API:**
```python
cerberus.check_pattern_consistency("dataclass usage")
cerberus.check_pattern_consistency("error handling")
cerberus.check_pattern_consistency("import style")
```

**Returns:**
```json
{
  "pattern": "dataclass for data structures",
  "conforming_files": 42,
  "violations": [
    {
      "file": "legacy.py",
      "line": 15,
      "issue": "Uses dict instead of dataclass",
      "suggestion": "Convert to @dataclass for consistency"
    },
    {
      "file": "old_module.py",
      "line": 89,
      "issue": "Uses tuple instead of dataclass",
      "suggestion": "Use NamedDataclass pattern"
    }
  ],
  "consistency_score": 0.87,
  "suggestion": "Convert 3 remaining files to dataclass pattern"
}
```

**Common patterns to check:**
- Dataclass vs dict vs tuple
- Error handling style (log_then_throw, etc.)
- Import organization (absolute vs relative)
- Docstring style
- Type annotation coverage
- Async/await vs sync
- Test naming conventions

**Why this matters:**
- Helps AI maintain project style without reading every file
- Catches inconsistencies before they spread
- Enables "show me examples of how this project does X"
- Ensures new code matches existing patterns

**Implementation:**
- Extract patterns from high-quality reference files
- Build pattern matchers (AST-based)
- Score files against patterns
- Generate suggestions
- **Difficulty**: 4-5 days

---

## 🚀 High Value Features

### 4. **Test Coverage Mapping**

**What it does:**
Maps implementation code to test coverage.

**API:**
```python
cerberus.test_coverage("generate_context")
```

**Returns:**
```json
{
  "symbol": "generate_context",
  "file": "src/cerberus/memory/context.py",
  "covered_by": [
    "test_memory_context.py::test_full_context",
    "test_memory_context.py::test_context_includes_decisions",
    "test_memory_integration.py::test_full_workflow"
  ],
  "coverage_percent": 87,
  "uncovered_branches": [
    "line 245: empty prompt case",
    "line 267: truncation path"
  ],
  "coverage_quality": "good",
  "safe_to_modify": true,
  "recommendations": [
    "Add test for empty prompt case",
    "Consider edge case testing for truncation"
  ]
}
```

**Why this matters:**
- Need to know if changes will break tests BEFORE making them
- Identifies gaps in test coverage
- Makes refactoring safer
- Helps prioritize which tests to run

**Implementation:**
- Parse test files for test-to-implementation mappings
- Build dependency graph from tests to implementation
- Calculate coverage based on call graph
- Identify uncovered branches
- **Difficulty**: 5-6 days

---

### 5. **Architecture Validation**

**What it does:**
Validates code against project-specific architectural rules.

**API:**
```python
cerberus.validate_architecture()
```

**Returns:**
```json
{
  "status": "violations_found",
  "violations": [
    {
      "rule": "MCP tools should use index_manager, not direct store access",
      "severity": "medium",
      "violators": [
        "old_tool.py:45: Direct SQLite store access"
      ],
      "fix": "Replace with get_index_manager().get_index()"
    },
    {
      "rule": "All public functions must have type hints",
      "severity": "high",
      "violators": [
        "utils.py:23: Missing return type"
      ],
      "fix": "Add -> ReturnType annotation"
    }
  ],
  "suggestions": [
    "3 files use deprecated patterns",
    "Consider updating to new index_manager pattern"
  ],
  "conformance_score": 0.92
}
```

**Configurable rules:**
- Layer separation (no direct store access)
- Required type hints
- Docstring requirements
- Async function patterns
- Error handling standards
- Import restrictions

**Why this matters:**
- Ensures AI follows project's own rules
- Catches architectural violations early
- Enforces consistency automatically
- Makes code reviews easier

**Implementation:**
- Define rule engine (plugin-based)
- Common rules as built-ins
- Custom rules from config file
- AST-based violation detection
- **Difficulty**: 4-5 days

---

### 6. **Semantic Code Search**

**What it does:**
Search by behavior/purpose, not just symbol names.

**API:**
```python
cerberus.search_by_behavior("functions that make HTTP calls")
cerberus.search_by_behavior("error handlers")
cerberus.search_by_behavior("database queries")
cerberus.search_by_behavior("file I/O operations")
```

**Returns:**
```json
{
  "query": "functions that make HTTP calls",
  "matches": [
    {
      "symbol": "fetch_remote_data",
      "file": "api/client.py",
      "line": 45,
      "confidence": 0.95,
      "reason": "Uses httpx.get()",
      "snippet": "async def fetch_remote_data(url: str)..."
    },
    {
      "symbol": "download_file",
      "file": "utils/downloader.py",
      "line": 23,
      "confidence": 0.88,
      "reason": "Uses requests.post()",
      "snippet": "def download_file(url: str, dest: Path)..."
    }
  ]
}
```

**Detection methods:**
- AST analysis (look for specific imports/calls)
- Pattern matching (try/except = error handler)
- Optional: LLM-based semantic understanding

**Why this matters:**
- Current search is symbol-based only
- Sometimes need "find all error handlers" which is semantic
- Enables "show me how this project does X"
- Better than grep for understanding patterns

**Implementation:**
- AST-based behavior detection
- Pattern library for common behaviors
- Optional LLM integration for complex queries
- **Difficulty**: 5-6 days (without LLM) or 8-10 days (with LLM)

---

## 💡 Nice to Have Features

### 7. **Cross-Branch Comparison**

**What it does:**
Compare code between branches with filtering.

**API:**
```python
cerberus.diff_branches("main", "feature", focus="authentication")
```

**Returns:**
```json
{
  "branch_a": "main",
  "branch_b": "feature",
  "focus": "authentication",
  "changes": [
    {
      "file": "auth/handlers.py",
      "type": "modified",
      "symbols_changed": ["login", "validate_token"],
      "lines_added": 45,
      "lines_removed": 23
    }
  ],
  "risk_assessment": "medium",
  "conflicts": []
}
```

**Difficulty**: 3-4 days

---

### 8. **Circular Dependency Detection**

**What it does:**
Finds circular import chains.

**API:**
```python
cerberus.find_circular_deps()
```

**Returns:**
```json
{
  "circular_chains": [
    {
      "chain": ["module_a", "module_b", "module_c", "module_a"],
      "severity": "high"
    }
  ]
}
```

**Difficulty**: 2-3 days

---

### 9. **Incremental Context** (HARD but powerful)

**What it does:**
Track what AI has already seen this session, only show what's NEW.

**API:**
```python
# First read
cerberus.get_symbol("MyClass")
# Returns full symbol

# Later in same session, file was modified
cerberus.get_new_changes_since_last_read("file.py")
# Only shows what changed since last read
```

**Why this is hard:**
- Requires session state management
- Need to track what was read when
- Need to diff against previous reads
- File change detection

**Difficulty**: 8-10 days

---

## 🎯 Recommended Implementation Priority

### Phase 1: Maximum Impact (2-3 weeks)
1. **Project Onboarding Summary** - Saves 5,000+ tokens EVERY session
2. **Change Impact Analysis** - Makes refactoring safe and confident
3. **Test Coverage Mapping** - Prevents breaking things

**Why these three:**
- Session startup: Fast (summary)
- Making changes: Safe (impact + coverage)
- Maintaining quality: Consistent

### Phase 2: Quality & Consistency (2-3 weeks)
4. **Pattern Consistency Checker**
5. **Architecture Validation**

### Phase 3: Advanced Search (2-3 weeks)
6. **Semantic Code Search**

### Phase 4: Nice to Haves (as needed)
7. Cross-Branch Comparison
8. Circular Dependency Detection
9. Incremental Context (if proven necessary)

---

## Implementation Notes

### Technical Considerations:

**For all features:**
- Build on existing index infrastructure
- Maintain token efficiency (all responses should be <2,000 tokens)
- Add to MCP tool registry
- Include token cost metadata
- Track usage in MCP metrics

**Testing:**
- Use Cerberus codebase itself for testing
- Dog-food each feature during development
- Measure actual token savings

**Documentation:**
- Add examples to each tool docstring
- Update global instructions with new workflows
- Create usage guides

---

## Success Metrics

### For each feature, measure:
1. **Token savings**: How much does this reduce exploration cost?
2. **Usage frequency**: How often do AI agents use this?
3. **Accuracy**: Does it provide correct information?
4. **User feedback**: Do developers find it helpful?

### Target metrics:
- Project summary: 80%+ token savings on session startup
- Change impact: 90%+ accuracy on affected files
- Test coverage: 85%+ accuracy on test mapping
- Pattern consistency: 75%+ accuracy on violation detection

---

## Conclusion

These features would transform Cerberus from a "better code search" tool into a "comprehensive project understanding system" for AI agents.

**Core value proposition:**
- Start sessions faster (onboarding summary)
- Make changes safely (impact analysis + test coverage)
- Maintain quality (pattern checking + architecture validation)
- Search smarter (semantic search)

All features leverage Cerberus's unique strengths:
- Existing index infrastructure
- Call graph capabilities
- Symbol relationship understanding
- Token efficiency focus

**Next steps:**
1. Validate assumptions with real usage
2. Prototype Phase 1 features
3. Measure actual token savings
4. Iterate based on feedback
