# Cerberus MCP

**Model Context Protocol (MCP) server for intelligent code exploration and analysis**

Cerberus is an MCP server that enables AI agents to efficiently navigate and understand codebases through AST-based parsing, symbol indexing, and advanced analysis tools.

[![Version: 2.0.0](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/proxikal/cerberus-mcp)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Server-green.svg)](https://modelcontextprotocol.io)

---

## Table of Contents

- [What is Cerberus?](#what-is-cerberus)
- [Installation](#installation)
- [Features](#features)
- [Available MCP Tools](#available-mcp-tools)
- [Supported Languages](#supported-languages)
- [Quick Start](#quick-start)
- [Example Workflows](#example-workflows)
- [Advanced Features](#advanced-features)
- [Session Memory System](#session-memory-system)
- [Token Efficiency](#token-efficiency)
- [Requirements](#requirements)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Links](#links)

---

## What is Cerberus?

Cerberus is a **Model Context Protocol (MCP) server** that provides AI agents with powerful code exploration capabilities:

- **Symbol-level navigation** - Find functions, classes, and interfaces instantly without reading entire files
- **AST-aware skeletonization** - Get function signatures without bodies (90%+ token reduction)
- **Architectural blueprints** - Understand project structure before diving into code
- **Advanced analysis** - Impact analysis, test coverage mapping, circular dependency detection
- **Session memory** - Persist patterns, decisions, and corrections across sessions
- **AI-powered summarization** - Generate natural language summaries of code (requires local Ollama)

---

## Installation

### MCP Server (Recommended for Claude Desktop)

1. **Install the package:**

```bash
pip install git+https://github.com/proxikal/cerberus-mcp.git
```

2. **Configure Claude Desktop:**

Add to your `claude_desktop_config.json`:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cerberus": {
      "command": "cerberus-mcp"
    }
  }
}
```

3. **Restart Claude Desktop**

The MCP server will start automatically when Claude Desktop launches.

### CLI Usage (Optional)

While Cerberus is primarily an MCP server, you can also run it as a CLI tool for testing:

```bash
# Install in development mode
git clone https://github.com/proxikal/cerberus-mcp.git
cd cerberus-mcp
pip install -e .

# Run the MCP server directly
cerberus-mcp
```

---

## Features

### 🔍 Code Exploration

- **Symbol search** - Find functions, classes, interfaces across your entire codebase
- **Get symbol details** - Retrieve full source code with context
- **Read line ranges** - Read specific sections of files efficiently
- **Skeletonization** - Get signatures and structure without implementation details
- **Blueprints** - Generate ASCII tree views of code architecture

### 🧠 Advanced Analysis

- **Impact analysis** - Understand ripple effects before refactoring
- **Test coverage mapping** - Find what tests exist for your code
- **Circular dependency detection** - Identify problematic import cycles
- **Pattern consistency checking** - Verify code follows project conventions
- **Architecture validation** - Enforce structural rules and boundaries
- **Cross-branch comparison** - Summarize branch diffs at symbol level
- **Related changes** - Suggest other files that might need updating

### 📊 Project Intelligence

- **Project summary** - Get 80/20 overview of new codebases
- **Behavioral search** - Find code by what it does, not just what it's named
- **Call graph analysis** - Understand caller/callee relationships
- **Dependency mapping** - Visualize how code depends on each other

### 💾 Session Memory

- **Pattern learning** - Record architectural decisions and coding patterns
- **Corrections** - Remember common mistakes to avoid
- **Git history extraction** - Automatically learn from commit patterns
- **Memory export/import** - Share knowledge between machines

### 📈 Metrics & Quality

- **Style checking** - Detect code style violations
- **Auto-fixing** - Automatically fix common style issues
- **MCP usage tracking** - Monitor tool usage patterns
- **Efficiency metrics** - Optimize your workflow

---

## Available MCP Tools

Cerberus provides **43 MCP tools** organized into these categories:

### Search & Discovery
- `search` - Search for symbols across codebase (keyword + semantic)
- `search_behavior` - Find code by what it does (natural language)
- `get_symbol` - Get full source code for a symbol
- `read_range` - Read specific line ranges from files

### Code Structure
- `blueprint` - Generate architectural overview of files/directories
- `skeletonize` - Get function signatures without bodies
- `skeletonize_directory` - Skeletonize all files in a directory

### Context Assembly
- `context` - Get complete context for a symbol (code + dependencies + callers)

### Analysis
- `deps` - Get callers and callees for a symbol
- `call_graph` - Build recursive call graph
- `analyze_impact` - Analyze impact of changing a symbol
- `diff_branches` - Symbol-level diff between two git branches
- `test_coverage` - Map test coverage for code
- `find_circular_deps` - Detect circular dependency chains
- `related_changes` - Suggest related files to update

### Quality & Validation
- `check_pattern` - Verify code follows project patterns
- `validate_architecture` - Enforce architectural rules
- `style_check` - Check for style violations
- `style_fix` - Auto-fix style issues

### Project Understanding
- `project_summary` - Generate comprehensive project overview
- `summarize` - AI-powered file summaries (requires Ollama)
- `summarize_architecture` - Summarize module architecture (requires Ollama)
- `summarize_status` - Check AI summarization availability

### Index Management
- `index_build` - Build or rebuild the code index
- `index_status` - Get index health and statistics
- `index_watcher` - File watcher status
- `index_auto_update` - Enable/disable auto-indexing
- `smart_update` - Incremental index update based on git changes

### Session Memory
- `memory_learn` - Store patterns, decisions, corrections
- `memory_show` - View stored memory
- `memory_context` - Get formatted context for AI session
- `memory_stats` - Memory storage statistics
- `memory_export` - Export memory for backup
- `memory_import` - Import memory from backup
- `memory_forget` - Remove memory entries
- `memory_extract` - Learn patterns from git history

### Metrics
- `metrics_report` - Efficiency metrics and patterns
- `metrics_status` - Metrics collection status
- `metrics_clear` - Reset metrics
- `mcp_metrics_session` - Session-level MCP usage
- `mcp_metrics_tool` - Per-tool MCP usage
- `mcp_metrics_export` - Export MCP metrics
- `mcp_metrics_reset` - Reset MCP metrics

### Diagnostics
- `health_check` - Server health and status

---

## Supported Languages

Cerberus supports AST parsing for:

| Language | Extensions | Symbol Types |
|----------|-----------|--------------|
| **Python** | `.py` | Functions, classes, methods |
| **JavaScript** | `.js` | Functions, classes, methods |
| **TypeScript** | `.ts` | Functions, classes, interfaces, enums, methods, variables |
| **Go** | `.go` | Functions, structs, interfaces |
| **Markdown** | `.md` | Section headings |

---

## Quick Start

### 1. Index Your Project

After installing, Claude Desktop will have access to Cerberus tools. In your conversation:

```
"Use Cerberus to index my project at /path/to/project"
```

Claude will call:
```python
index_build(path="/path/to/project", extensions=[".py", ".ts", ".js", ".go"])
```

### 2. Search for Code

```
"Find all authentication-related functions"
```

Claude will call:
```python
search(query="authenticate", limit=10)
```

### 3. Understand Structure

```
"Show me the architecture of the src/auth directory"
```

Claude will call:
```python
blueprint(path="src/auth")
```

### 4. Analyze Impact

```
"What would break if I change the validateToken function?"
```

Claude will call:
```python
analyze_impact(symbol_name="validateToken")
```

### 5. Get Complete Context

```
"Give me everything I need to understand the UserService class"
```

Claude will call:
```python
context(symbol_name="UserService", include_bases=True, include_deps=True)
```

---

## Example Workflows

### For AI Agents

**Exploring a New Codebase:**
```python
# 1. Load session memory (patterns from previous sessions)
memory_context(compact=True)

# 2. Get project overview
project_summary()

# 3. Search for specific functionality
search(query="authentication", limit=10)

# 4. Get complete context for a symbol
context(symbol_name="authenticate", include_bases=True, include_deps=True)

# 5. Understand what tests exist
test_coverage(symbol_name="authenticate")
```

**Before Refactoring:**
```python
# 1. Analyze impact
analyze_impact(symbol_name="processPayment")

# 2. Check test coverage
test_coverage(symbol_name="processPayment")

# 3. Find related code that might need updating
related_changes(file_path="src/payments/processor.py", symbol_name="processPayment")

# 4. Make changes safely
edit_symbol(symbol_name="processPayment", new_code="...")
```

**Learning from a Project:**
```python
# 1. Extract patterns from git history
memory_extract(path=".", lookback_days=30)

# 2. Check how project handles specific patterns
check_pattern(pattern="error_handling", show_examples=True)

# 3. Validate architecture rules
validate_architecture(rules=["layer_separation", "type_coverage"])

# 4. Store what you learned
memory_learn(category="decision", content="Uses JWT with 1hr expiry for auth")
```

### For Developers

**Quick Navigation:**
```python
# See what's in a file without opening it
blueprint(path="src/components/Button.tsx")

# Get just the function signatures
skeletonize(path="src/lib/api.ts")

# Find where a function is defined
search(query="handleSubmit")
```

**Code Quality:**
```python
# Check for circular dependencies
find_circular_deps(scope="src/", min_severity="medium")

# Check code style
style_check(path="src/", fix_preview=True)

# Auto-fix issues
style_fix(path="src/", dry_run=False)
```

---

## Advanced Features

### AI-Powered Summarization

Cerberus can generate natural language summaries using local LLMs via Ollama:

```python
# Check if summarization is available
summarize_status()

# Summarize a file
summarize(path="src/auth/service.py", focus="error handling")

# Summarize an architecture
summarize_architecture(
    name="authentication system",
    paths=["src/auth/service.py", "src/auth/middleware.py", "src/auth/tokens.py"]
)
```

**Requirements:**
- [Ollama](https://ollama.ai) installed and running locally
- A model pulled (e.g., `ollama pull llama2`)

### Circular Dependency Detection

Find problematic import cycles before they cause issues:

```python
find_circular_deps(
    scope="src/",           # Optional: limit to directory
    min_severity="medium"   # low, medium, high, critical
)
```

**Returns:**
```json
{
  "total_modules": 178,
  "circular_chains": [
    {
      "chain": ["module_a", "module_b", "module_c"],
      "severity": "high",
      "length": 3,
      "description": "module_a → module_b → module_c → module_a"
    }
  ],
  "summary": "⚠️  Found 1 circular dependency chain (1 high)"
}
```

### Smart Incremental Updates

Instead of rebuilding the entire index, use surgical updates:

```python
# Update based on git changes (10x faster than full rebuild)
smart_update(force_full=False)
```

Cerberus detects:
- Modified files
- Deleted files
- New files
- Only re-parses what changed

---

## Session Memory System

Cerberus has a powerful **dual-layer memory system** that allows AI agents to learn and remember across sessions. This is one of Cerberus's most unique features.

### Two Types of Memory

#### 🌍 **Global Memory** (Cross-Project)
Stored in `~/.cerberus/memory/` - applies to **all projects**

- **Preferences** (`preference` category)
  - Your coding style preferences
  - Tool preferences
  - General patterns you follow everywhere
  - Example: "Use async/await for all database operations"

- **Corrections** (`correction` category)
  - Common mistakes you've made before
  - Patterns to avoid
  - Lessons learned
  - Example: "Remember to await Prisma client calls"

#### 📁 **Project-Specific Memory** (Per-Project)
Stored in `.cerberus/memory/` within each project - applies **only to that project**

- **Decisions** (`decision` category)
  - Architectural choices for this project
  - Tech stack decisions
  - Project-specific conventions
  - Example: "This project uses JWT auth with 1hr expiry"

### Storage Locations

```
Global Memory:
~/.cerberus/memory/
├── profile.json         # Your global preferences
├── corrections.json     # Mistakes to avoid globally
└── prompts/             # Effective prompts by task type

Project Memory:
/your/project/.cerberus/memory/
└── decisions.json       # This project's architectural decisions
```

### How to Use Memory

#### Store Knowledge

```python
# Global preference (applies everywhere)
memory_learn(
    category="preference",
    content="Use early returns over nested conditionals"
)

# Project-specific decision (only for this project)
memory_learn(
    category="decision",
    content="All API routes require authentication middleware",
    project="my-app"  # Auto-detected if omitted
)

# Global correction (remember mistakes)
memory_learn(
    category="correction",
    content="Always validate user input at API boundaries"
)
```

#### Retrieve Memory

```python
# Load all memory for current session
memory_context(compact=True)
# Returns: Global preferences + Global corrections + Project decisions
```

#### Advanced Memory Operations

```python
# View what's stored
memory_show(category="preferences")  # or "decisions", "corrections"

# Get statistics
memory_stats()

# Export for backup
memory_export(output_path="backup.json")

# Import from backup
memory_import(input_path="backup.json", merge=True)

# Remove specific memory
memory_forget(category="preference", identifier="some preference")

# Learn from git history (auto-extract patterns from commits)
memory_extract(path=".", lookback_days=30)
```

### Why This Matters

**Without Memory:**
- AI starts from zero every session
- Repeats the same mistakes
- Asks the same questions
- Doesn't learn your style

**With Memory:**
- AI remembers your preferences across all projects
- Learns from corrections and won't repeat mistakes
- Understands project-specific decisions
- Gets smarter over time

### Example Session Flow

```python
# 🌍 Session 1 (New Project)
# AI loads your global preferences automatically
memory_context()
# → "Use async/await, early returns, type hints"

# You work, AI learns project decisions
memory_learn(category="decision", content="Uses PostgreSQL with Prisma ORM")
memory_learn(category="decision", content="Error responses follow RFC 7807")

# 🌍 Session 2 (Same Project, Next Day)
memory_context()
# → "Use async/await, early returns" (global)
# → "PostgreSQL + Prisma, RFC 7807 errors" (this project)
# AI already knows your style AND project architecture

# 🌍 Session 3 (Different Project)
memory_context()
# → "Use async/await, early returns" (global preferences carry over)
# → No project decisions (clean slate for new project)
```

### Memory Categories Explained

| Category | Scope | Storage | Example Use Case |
|----------|-------|---------|------------------|
| `preference` | **Global** | `~/.cerberus/memory/profile.json` | Coding style, tool choices, general patterns |
| `decision` | **Project** | `.cerberus/memory/decisions.json` | Architecture choices, tech stack, project conventions |
| `correction` | **Global** | `~/.cerberus/memory/corrections.json` | Mistakes to avoid, lessons learned |

### Auto-Learning from Git History

Cerberus can automatically extract patterns from your git commits:

```python
memory_extract(path=".", lookback_days=30)
```

This analyzes commit messages and changes to learn:
- Naming conventions you follow
- Common patterns in your commits
- Architectural decisions evident from code changes
- Testing patterns

### Token Efficiency

Memory is incredibly token-efficient:
- **Loading memory**: ~200-500 tokens (vs 0 knowledge)
- **Benefit**: AI understands context immediately
- **Result**: Fewer questions, fewer corrections, better code

---

## Token Efficiency

Cerberus is designed for minimal token usage:

| Operation | Traditional Approach | Cerberus | Savings |
|-----------|---------------------|----------|---------|
| Understanding a file | Read full 500 lines (~5,000 tokens) | `skeletonize` (~400 tokens) | **92%** |
| Finding a symbol | Read multiple files | `search` + `get_symbol` (~200 tokens) | **95%+** |
| Getting context | Read symbol + deps + callers (10,000+ tokens) | `context` (~1,500 tokens) | **85%** |
| Project overview | Manual exploration (20,000+ tokens) | `project_summary` (~800 tokens) | **96%** |

---

## Requirements

### Core Dependencies
- **Python**: 3.10 or higher
- **Dependencies** (auto-installed):
  - `fastmcp` - MCP server framework
  - `rich` - Terminal formatting
  - `pydantic` - Data validation
  - `loguru` - Logging
  - `watchdog` - File watching
  - `rank-bm25` - Keyword search
  - `sentence-transformers` - Semantic search
  - `numpy` - Numerical operations
  - `tree-sitter` - AST parsing
  - `psutil` - System utilities
  - `requests` - HTTP requests

### Optional Dependencies
- **Ollama** - For AI-powered summarization (`summarize`, `summarize_architecture`)
  - Install from [ollama.ai](https://ollama.ai)
  - Pull a model: `ollama pull llama2`

---

## Architecture

### How It Works

1. **Indexing**
   - Scans project for supported file types
   - Parses each file into an Abstract Syntax Tree (AST)
   - Extracts symbols (functions, classes, etc.) with line numbers
   - Stores in SQLite database (`.cerberus/index.db`)

2. **Search**
   - BM25 keyword ranking on symbol names
   - Optional semantic search using sentence transformers
   - Returns ranked results with file paths and line numbers

3. **Context Assembly**
   - Retrieves symbol code
   - Skeletonizes base classes (inheritance chain)
   - Finds callers and callees
   - Combines into single payload

4. **Memory System**
   - Stores patterns per-project in `~/.config/cerberus/memory/<project>/`
   - JSON files for decisions, preferences, corrections
   - Context generation formats for AI consumption

### Project Structure

```
cerberus-mcp/
├── src/cerberus/
│   ├── mcp/              # MCP server and tools
│   │   ├── server.py     # FastMCP server setup
│   │   └── tools/        # 47 MCP tools
│   ├── analysis/         # Advanced analysis (impact, circular deps, etc.)
│   ├── blueprint/        # Architectural blueprints
│   ├── index/            # Symbol indexing
│   ├── memory/           # Session memory system
│   ├── parser/           # AST parsers for each language
│   ├── resolution/       # Call graph and dependency resolution
│   ├── retrieval/        # Search and ranking
│   ├── storage/          # SQLite storage layer
│   └── mutation/         # Code editing
├── tests/                # Test suite
└── pyproject.toml        # Package configuration
```

---

## Troubleshooting

### MCP Server Not Appearing in Claude Desktop

1. Check the config file path is correct
2. Ensure `cerberus-mcp` command is in your PATH: `which cerberus-mcp`
3. Restart Claude Desktop completely
4. Check Claude Desktop logs:
   - macOS: `~/Library/Logs/Claude/mcp*.log`
   - Windows: `%APPDATA%\Claude\logs\mcp*.log`

### Index Issues

```python
# Check index status
health_check()

# Rebuild index
index_build(path=".", extensions=[".py", ".ts", ".js"])
```

### Summarization Not Working

```python
# Check if Ollama is running
summarize_status()
```

Ensure Ollama is installed and running:
```bash
ollama serve
```

---

## Contributing

Contributions are welcome! This project is in active development.

### Development Setup

```bash
# Clone repository
git clone https://github.com/proxikal/cerberus-mcp.git
cd cerberus-mcp

# Install in development mode
pip install -e .

# Run tests
pytest tests/ -v

# Run specific test
pytest tests/test_circular_dependency_detector.py -v
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=cerberus --cov-report=html

# Specific module
pytest tests/test_mcp/ -v
```

---

## Roadmap

### Phase 4 (In Progress)
- ✅ Circular dependency detection
- ⏳ Cross-branch comparison
- ⏳ Incremental context tracking

### Future Enhancements
- Multi-language call graph analysis
- Visualization of dependencies
- Integration with language servers (LSP)
- Browser-based UI for exploration

---

## Links

- **GitHub Repository**: https://github.com/proxikal/cerberus-mcp
- **Issues**: https://github.com/proxikal/cerberus-mcp/issues
- **Model Context Protocol**: https://modelcontextprotocol.io

---

**Cerberus v2.0.0** - MCP Server for Intelligent Code Exploration

Built with [FastMCP](https://github.com/jlowin/fastmcp) | Powered by AST analysis | Token-optimized for AI agents
