# Cerberus: The Autonomous Context Engine

**Cerberus** is an intelligent "Context Management Layer" that bridges the gap between autonomous AI agents and massive software engineering projects. It solves the **"Context Wall"** problem by pre-processing, indexing, and serving only the most relevant, compacted context to agents on-demand.

[![Status: Production](https://img.shields.io/badge/status-production-green.svg)](#)
[![Tests: 34/34 Passing](https://img.shields.io/badge/tests-34%2F34%20passing-brightgreen.svg)](#)
[![Phase: 3 Complete](https://img.shields.io/badge/phase-3%20complete-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](#)

---

## 🚨 The Problem: The Context Wall

Autonomous AI agents face a critical limitation when working with large codebases:

- **Context Limits:** Projects often exceed LLM context windows, causing agents to "forget" architecture
- **Token Waste:** Reading entire files to find a single function burns through tokens (150K+ tokens wasted)
- **Slow Retrieval:** Manual file searching and grepping is inefficient and error-prone
- **Lost Context:** Agents lose the "big picture" when forced to operate on isolated text chunks

**Example: Without Cerberus**
```
Agent needs: "How does user authentication work?"
→ grep -r "auth" → 50 files matched
→ Read all 50 files → 500 KB of code
→ Token usage: ~150,000 tokens
→ Time: Minutes of manual searching
→ Result: Overwhelmed agent, wasted context
```

**Example: With Cerberus**
```
Agent: cerberus search "user authentication logic"
→ Hybrid search finds 5 relevant functions
→ Returns 2 KB of precise code
→ Token usage: ~500 tokens (300x reduction!)
→ Time: 7 seconds automated
→ Result: Perfect context, efficient retrieval
```

---

## 🚀 Key Features

### 🧩 AST-Based Chunking
Unlike simple text splitters, Cerberus uses **Tree-Sitter** to parse code into a structural map of functions, classes, methods, and variables. It understands the difference between a comment and a class definition.

**Supports:** Python, JavaScript, TypeScript, JSX, TSX (Go, Rust, Java coming in Phase 4)

### 🔍 Hybrid Search (Phase 3 ✅)
Combines **BM25 keyword search** with **vector semantic search** for best-in-class retrieval:

- **BM25:** Perfect for exact matches (function names, class names)
- **Vector:** Excellent for conceptual searches ("error handling logic")
- **RRF Fusion:** Merges both rankings for optimal results

**Automatic query type detection:** Cerberus detects whether you're searching for exact symbols or concepts and adjusts weights automatically.

**Performance:** <8 seconds for all query types (including model loading)

### ⚡ Incremental Updates (Phase 3 ✅)
Git-aware surgical index updates that re-parse **only changed symbols** instead of the entire codebase.

**Speed:** 10x faster than full reparse for <20% file changes
- Small changes (<5%): <1 second
- Medium changes (5-20%): 1-5 seconds
- Large changes (>30%): Auto-fallback to full reparse

**Smart features:**
- Detects changes via `git diff`
- Re-parses affected symbols and their callers
- Tracks commit hashes in index metadata

### 👁️ Background Watcher (Phase 3 ✅)
Invisible filesystem monitoring daemon that keeps your index synchronized in real-time.

**Features:**
- Auto-starts with CLI commands (optional)
- Debounced updates (waits 2s after last change)
- Cross-platform (macOS, Linux, Windows)
- Graceful shutdown and PID management

**Usage:**
```bash
cerberus watcher status    # Check daemon status
cerberus watcher start     # Start monitoring
cerberus watcher logs      # View real-time logs
```

### 📉 Context Compaction
Optimized retrieval ensures agents receive only what they need:

- **Padded Snippets:** Get function with N lines of context
- **Skeletonization:** Show signatures without implementation details
- **Import Resolution:** Automatically include definitions of referenced types

### 🤖 Agent-Native CLI
Every command supports `--json` output for seamless machine integration:

```bash
cerberus search "auth" --json
{
  "results": [
    {
      "name": "authenticate_user",
      "file": "src/auth.py",
      "lines": [42, 67],
      "score": 0.856,
      "match_type": "both"
    }
  ]
}
```

---

## 💡 Why Cerberus?

Cerberus occupies a specialized niche between "Code Search Engines" and "RAG Frameworks." While there are tools that overlap with its functionality, Cerberus is built with a specific **"Agent-First"** philosophy.

### 🧠 Surgical vs. Chunk-based Indexing
Most RAG tools split code into arbitrary "chunks" of 500-1000 tokens, often cutting functions in half. Cerberus understands **Abstract Syntax Trees (AST)**. It indexes by **Symbol Boundaries**, ensuring that functions, classes, and methods are always retrieved as complete, logical units.

### 💓 The Git-Native Heartbeat
Unlike indexers that re-scan the entire project or use basic file-hash checking, Cerberus hooks directly into the **Git lifecycle**. By parsing `git diff`, it performs surgical updates. If you change 3 lines in a 5,000-line file, Cerberus only re-parses the specific symbols affected by those lines, keeping the index in sync in real-time.

### 📉 Skeletonization (Token Economy)
When an agent needs to understand a massive file, most tools send either the whole file (wasting tokens) or a tiny snippet (losing context). Cerberus can generate a **Skeleton**—stripping the logic out and sending only the signatures. This allows an agent to "see" the entire structure of a massive project for a fraction of the cost.

### 🩺 Built-in "Doctor" Protocol
Cerberus isn't just for reading; it's for **reliable engineering**. The inclusion of `doctor.py` and the **XCalibr Autonomous Debugging Protocol** means Cerberus is designed to help an agent diagnose its own environment, ensuring grammars are compiled and the index is healthy before it starts working.

---

## 📊 Performance Metrics

Tested on production-scale project (TheCookBook: 1.1GB, 24,810 files):

| Metric | Value |
|--------|-------|
| Files Indexed | 428 TypeScript/JavaScript files |
| Symbols Extracted | 1,199 symbols |
| Index Time | 2.1 minutes (126s) |
| Index Size | 23 MB |
| Peak Memory | 522 MB |
| **Keyword Search** | **3.06s** |
| **Semantic Search** | **7.62s** |
| **Hybrid Search** | **7.36s** |
| **Token Savings** | **99.7%** (150K → 500 tokens) |

See [PHASE3_BENCHMARK_RESULTS.md](./PHASE3_BENCHMARK_RESULTS.md) for detailed benchmarks.

---

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- Git (for incremental updates)
- 500MB+ disk space for embedding models

### Install Dependencies

```bash
# Clone repository
git clone https://github.com/aegis-foundation/cerberus.git
cd cerberus

# Install Python dependencies
pip install -r requirements.txt

# Verify installation
PYTHONPATH=src python3 -m cerberus.main version
```

### Dependencies
- `tree-sitter` - AST parsing
- `sentence-transformers` - Semantic embeddings
- `rank-bm25` - Keyword search
- `watchdog` - Filesystem monitoring
- `typer` - CLI framework
- `pydantic` - Schema validation

---

## 🎯 Quick Start

### 1. Index a Project

```bash
# Basic indexing
cerberus index ./path/to/project -o my_index.json

# With file type filters
cerberus index ./src --ext .py --ext .ts -o index.json

# JSON output for automation
cerberus index ./project -o index.json --json
```

**Output:**
```
Indexed 428 files and 1199 symbols to my_index.json.
```

### 2. Search for Code

```bash
# Auto mode (detects query type)
cerberus search "database connection logic"

# Keyword mode (exact matches)
cerberus search "DatabaseConnection" --mode keyword

# Semantic mode (conceptual)
cerberus search "how is auth handled" --mode semantic

# Balanced hybrid
cerberus search "user login" --mode balanced --keyword-weight 0.7

# JSON output
cerberus search "auth" --json --limit 5
```

**Output:**
```
                    Hybrid Search: 'auth' (mode: auto)
┏━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┓
┃ Rank ┃ Score ┃ Type ┃ Name            ┃ Symbol     ┃ File       ┃ Lines ┃
┡━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━┩
│    1 │ 0.856 │  ⚡  │ authenticate    │ function   │ auth.py    │ 42-67 │
│    2 │ 0.742 │  🔤  │ AuthService     │ class      │ service.py │ 15-89 │
│    3 │ 0.623 │  🧠  │ verify_token    │ function   │ jwt.py     │ 23-45 │
└──────┴───────┴──────┴─────────────────┴────────────┴────────────┴───────┘

Match types: 🔤 Keyword  🧠 Semantic  ⚡ Both
```

### 3. Get Specific Symbol

```bash
# Retrieve exact function code
cerberus get-symbol "authenticate_user" --padding 3

# With import information
cerberus get-symbol "AuthService" --show-imports

# JSON output
cerberus get-symbol "verify_token" --json
```

### 4. Incremental Updates

```bash
# Update index after code changes (git-aware)
cerberus update --index my_index.json

# Dry-run (show what would change)
cerberus update --index my_index.json --dry-run

# With detailed statistics
cerberus update --index my_index.json --stats

# Force full reparse
cerberus update --index my_index.json --full
```

**Output:**
```
Detecting changes...
Updating index incrementally...

✓ Index updated successfully
  Strategy: incremental
  Files re-parsed: 3
  Symbols updated: 12
  Symbols removed: 0
  Time: 0.8s
```

### 5. Background Watcher

```bash
# Check watcher status
cerberus watcher status

# Start watching (real-time sync)
cerberus watcher start --project ./my-project --index my_index.json

# View logs
cerberus watcher logs --follow

# Stop watcher
cerberus watcher stop
```

**Output:**
```
✅ Watcher running (PID: 12345)
   Watching: /Users/dev/my-project
   Index: my_index.json
   Uptime: 2h 34m
   Last update: 45s ago
   Events processed: 127
```

### 6. View Statistics

```bash
cerberus stats --index my_index.json
```

**Output:**
```
       Index Stats for
    'my_index.json'
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric            ┃ Value ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Files       │ 428   │
│ Total Symbols     │ 1199  │
│ Avg Symbols/File  │ 2.80  │
│ Total Calls       │ 111K  │
│ Type Info Entries │ 1078  │
└───────────────────┴───────┘
```

---

## 🏗️ Architecture

Cerberus follows the **Self-Similarity Mandate**: every package has the same clean structure.

```
cerberus/
├── scanner/          # The "Legs" - Filesystem traversal
│   ├── facade.py     # Public API
│   ├── walker.py     # Directory walking
│   └── config.py     # Scanner configuration
│
├── parser/           # The "Eyes" - AST extraction
│   ├── facade.py     # Public API
│   ├── python_parser.py
│   ├── typescript_parser.py
│   └── config.py
│
├── index/            # The "Memory" - Persistence
│   ├── facade.py     # Public API
│   ├── index_builder.py
│   ├── index_loader.py
│   └── json_store.py
│
├── retrieval/        # The "Brain" - Hybrid search (Phase 3)
│   ├── facade.py     # Public API (hybrid_search)
│   ├── bm25_search.py      # Keyword search
│   ├── vector_search.py    # Semantic search
│   ├── hybrid_ranker.py    # RRF fusion
│   └── config.py
│
├── incremental/      # Git-aware updates (Phase 3)
│   ├── facade.py     # Public API
│   ├── git_diff.py   # Change detection
│   ├── change_analyzer.py
│   ├── surgical_update.py
│   └── config.py
│
├── watcher/          # Background daemon (Phase 3)
│   ├── facade.py     # Public API
│   ├── daemon.py     # Process management
│   ├── filesystem_monitor.py
│   └── config.py
│
├── synthesis/        # Context compaction (Phase 2)
│   ├── facade.py     # Public API
│   ├── skeletonizer.py
│   └── payload.py
│
└── main.py           # The "Mouth" - CLI (Typer)
```

**Design Principles:**
- Every package exposes a clean `facade.py` API
- Internal implementation details are hidden
- Configuration centralized in `config.py`
- Self-documenting structure (agent can navigate using Cerberus itself!)

---

## 📚 Complete CLI Reference

### Core Commands

```bash
# Indexing
cerberus index <path> -o <output>         # Create index
cerberus stats --index <file>             # Show statistics

# Search & Retrieval
cerberus search <query> [--mode auto|keyword|semantic|balanced]
cerberus get-symbol <name> [--padding N] [--show-imports]
cerberus get-context <symbol>             # Get synthesized context

# Updates (Phase 3)
cerberus update --index <file> [--dry-run|--stats|--full]

# Watcher (Phase 3)
cerberus watcher status                   # Check daemon status
cerberus watcher start [--project <path>] # Start monitoring
cerberus watcher stop                     # Stop daemon
cerberus watcher restart                  # Restart daemon
cerberus watcher logs [--follow]          # View logs

# Context Operations
cerberus skeleton-file <path>             # Show skeletonized view
cerberus skeletonize <file>               # AST-aware pruning
cerberus deps --symbol <name> [--recursive] # Show dependencies

# Utilities
cerberus doctor                           # Run diagnostics
cerberus generate-tools                   # Generate agent manifest
cerberus bench                            # Run benchmarks
```

### Global Flags

```bash
--json          # Machine-readable JSON output (all commands)
--help          # Show command help
```

---

## 🧪 Testing

Cerberus has comprehensive test coverage:

```bash
# Run all tests
PYTHONPATH=src python3 -m pytest tests/ -v

# Run specific test suites
PYTHONPATH=src python3 -m pytest tests/test_phase3_unit.py -v
PYTHONPATH=src python3 -m pytest tests/test_phase3_retrieval.py -v
PYTHONPATH=src python3 tests/test_phase3_integration.py
```

**Test Results:** 34/34 passing (100%) ✅

---

## 📖 Documentation

### User Documentation
- **[README.md](./README.md)** - This file
- **[Quick Start](#-quick-start)** - Get started in 5 minutes
- **[CLI Reference](#-complete-cli-reference)** - All commands

### Developer Documentation
- **[VISION.md](./docs/VISION.md)** - Architectural philosophy
- **[MANDATES.md](./docs/MANDATES.md)** - Development rules
- **[ROADMAP.md](./docs/ROADMAP.md)** - Current status and future plans
- **[AGENT_GUIDE.md](./docs/AGENT_GUIDE.md)** - AI agent integration guide

### Phase Documentation
- **[PHASE3_COMPLETE.md](./PHASE3_COMPLETE.md)** - Phase 3 completion report
- **[PHASE3_BENCHMARK_RESULTS.md](./PHASE3_BENCHMARK_RESULTS.md)** - Performance benchmarks
- **[PHASE4_ENHANCEMENTS.md](./docs/PHASE4_ENHANCEMENTS.md)** - Planned enhancements

---

## 🤖 AI Agent Integration

Cerberus is designed to be **agent-native**. Here's how to integrate:

### 1. Generate Tool Manifest

```bash
cerberus generate-tools > tools.json
```

This creates a JSON manifest describing all Cerberus capabilities for your agent framework (LangChain, CrewAI, AutoGPT).

### 2. Use JSON Output

Every command supports `--json` for structured output:

```python
import subprocess
import json

# Search for code
result = subprocess.run(
    ["cerberus", "search", "authentication", "--json"],
    capture_output=True,
    text=True
)
data = json.loads(result.stdout)

for item in data["results"]:
    print(f"Found: {item['name']} in {item['file']}")
```

### 3. Monitor Agent Logs

```bash
tail -f cerberus_agent.log
```

Structured JSON logs include:
- Performance metrics
- Error messages
- Trace events

### 4. Token Optimization

**Before Cerberus:**
```
Agent prompt: "Fix the authentication bug"
→ Reads 50 files (500 KB)
→ Context: 150,000 tokens
→ Cost: High
```

**With Cerberus:**
```
Agent prompt: "Fix the authentication bug"
→ cerberus search "authentication" --json
→ Returns 5 precise functions (2 KB)
→ Context: 500 tokens (300x reduction)
→ Cost: Minimal
```

---

## 🎯 Use Cases

### 1. Code Review Agents
```bash
# Agent reviews changes
git diff main | cerberus update --index review.json --dry-run
cerberus search "modified functions" --json
# Agent gets only changed code for review
```

### 2. Documentation Generators
```bash
# Agent generates docs
cerberus get-symbol "MyClass" --show-imports
# Gets class with all type definitions
```

### 3. Bug Fixing Agents
```bash
# Agent searches for error handling
cerberus search "error handling for database connections"
# Finds all relevant error handlers
```

### 4. Refactoring Agents
```bash
# Agent finds all callers
cerberus deps --symbol "old_function" --recursive
# Gets complete call graph for safe refactoring
```

---

## 🔧 Configuration

### Scanner Configuration (`cerberus/scanner/config.py`)

```python
DEFAULT_EXTENSIONS = [".py", ".js", ".ts", ".tsx", ".jsx"]
DEFAULT_IGNORE_PATTERNS = [
    "node_modules/**",
    "__pycache__/**",
    ".venv/**",
    "*.pyc"
]
```

### Hybrid Search Configuration (`cerberus/retrieval/config.py`)

```python
HYBRID_SEARCH_CONFIG = {
    "default_mode": "auto",
    "keyword_weight": 0.5,
    "semantic_weight": 0.5,
    "top_k_per_method": 20,
    "final_top_k": 10,
}

BM25_CONFIG = {
    "k1": 1.5,  # Term frequency saturation
    "b": 0.75,  # Length normalization
}
```

### Watcher Configuration (`cerberus/watcher/config.py`)

```python
WATCHER_CONFIG = {
    "auto_start": False,  # Auto-start on CLI commands
    "debounce_delay": 2.0,  # Seconds to wait after last change
}
```

---

## 🐛 Troubleshooting

### Issue: "Tree-sitter grammar not found"

**Solution:**
```bash
# Compile grammars manually
python3 compile_grammars.py
```

### Issue: "Embedding model download slow"

**Solution:** First-time model download takes ~4 seconds. Subsequent uses are instant (cached in memory).

### Issue: "Path not found in incremental update"

**Solution:** This is a known edge case with git diff path normalization. Use `--full` flag to force full reparse:
```bash
cerberus update --index my_index.json --full
```

### Issue: "Watcher not starting"

**Solution:** Check if another watcher is already running:
```bash
cerberus watcher status
cerberus watcher stop  # Stop existing watcher
cerberus watcher start # Start fresh
```

### Need Help?

Run diagnostics:
```bash
cerberus doctor
```

This checks:
- Python version
- Dependencies
- Tree-sitter grammars
- Embedding model availability
- Git integration

---

## 🗺️ Roadmap

### ✅ Phase 1: Foundation (Complete)
- AST-based parsing
- Basic indexing and retrieval
- Symbol resolution

### ✅ Phase 2: Context Synthesis (Complete)
- Skeletonization
- Payload synthesis
- Import resolution

### ✅ Phase 3: Operational Excellence (Complete)
- Git-native incrementalism
- Background watcher
- Hybrid retrieval (BM25 + Vector)

### 🔮 Phase 4: Integration Ecosystem (Planned)
- Official agent plugins (LangChain, CrewAI, AutoGPT)
- Web UI for visual exploration
- Security scanning (PII/secrets detection)
- Multi-language support (Go, Rust, Java)

See [ROADMAP.md](./docs/ROADMAP.md) and [PHASE4_ENHANCEMENTS.md](./docs/PHASE4_ENHANCEMENTS.md) for details.

---

## 🤝 Contributing

Cerberus follows strict development mandates for maintainability. See [MANDATES.md](./docs/MANDATES.md).

**Key principles:**
- Self-similarity in architecture
- Deterministic code over prompts
- Comprehensive testing (aim for 100%)
- Agent-native design

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 🙏 Acknowledgments

**Philosophy:** Aegis Foundation's robustness mandates

**Implementation:** Claude Sonnet 4.5 (Anthropic)

**Testing:** Automated test suite + production validation

**Inspiration:** The need for better AI agent tooling in software engineering

---

## 📊 Project Status

**Current Version:** Phase 3 Complete (v0.3.0)

**Status:** ✅ Production Ready

**Tests:** 34/34 Passing (100%)

**Benchmarks:** Validated on 400+ file production project

**Next:** Phase 4 enhancements (agent plugins, web UI)

---

## 🔗 Links

- **Documentation:** [./docs/](./docs/)
- **Tests:** [./tests/](./tests/)
- **Benchmarks:** [PHASE3_BENCHMARK_RESULTS.md](./PHASE3_BENCHMARK_RESULTS.md)
- **Completion Report:** [PHASE3_COMPLETE.md](./PHASE3_COMPLETE.md)
- **Future Plans:** [PHASE4_ENHANCEMENTS.md](./docs/PHASE4_ENHANCEMENTS.md)

---

**Cerberus: Empowering AI agents to work efficiently with massive codebases.**

*Developed by the Aegis Foundation.*
