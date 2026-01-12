# Cerberus

**AST-based code exploration with session memory for AI agents**

Cerberus is a command-line tool that helps developers and AI agents efficiently navigate and understand codebases through Abstract Syntax Tree (AST) parsing, symbol indexing, and cross-session memory.

[![Version: 1.0.1](https://img.shields.io/badge/version-1.0.1-blue.svg)](https://github.com/proxikal/Cerberus/releases/tag/v1.0.1)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## Table of Contents

- [What is Cerberus?](#what-is-cerberus)
- [Key Features](#key-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Workflows](#core-workflows)
  - [For AI Agents](#for-ai-agents)
  - [For Developers](#for-developers)
- [Command Reference](#command-reference)
- [Supported Languages](#supported-languages)
- [Project Templates](#project-templates)
- [Session Memory](#session-memory)
- [How It Works](#how-it-works)
- [Requirements](#requirements)
- [License](#license)

---

## What is Cerberus?

Cerberus solves a fundamental problem in code navigation: **finding relevant code without reading entire files**.

Traditional tools require you to:
1. Open a file (read 500+ lines)
2. Scan for the function you need
3. Read surrounding context to understand it
4. Repeat for each related file

Cerberus provides:
1. **Symbol-level indexing** - See all functions/classes in a file instantly
2. **AST-aware skeletonization** - Get signatures without function bodies (95%+ token reduction)
3. **Architectural blueprints** - Understand file structure before reading code
4. **Cross-session memory** - Learn patterns and avoid repeating mistakes

---

## Key Features

### 1. AST-Based Symbol Extraction
Cerberus parses source files into Abstract Syntax Trees and extracts:
- Functions and methods (with parameters, return types)
- Classes and interfaces
- Variables and constants
- Enums and type definitions

Each symbol is indexed with exact line numbers, making navigation precise.

### 2. Skeletonization (Token Optimization)
The `skeletonize` command removes function bodies while preserving:
- Function signatures
- Type annotations
- Docstrings
- Class structures

**Result:** Understanding a 500-line module costs ~50 tokens instead of ~5,000.

### 3. Architectural Blueprints
The `blueprint` command generates ASCII tree views showing:
- File structure (classes, functions, variables)
- Dependencies between symbols
- Complexity metrics (nesting depth, line count)

### 4. Session Memory
The `memory` system allows agents to:
- **Learn patterns** - Record architectural decisions, coding patterns
- **Store corrections** - Remember common mistakes to avoid
- **Maintain context** - Persist knowledge across sessions

### 5. Config-Driven Documentation
The `docs` command provides path-agnostic documentation access:
- Works in any Cerberus installation (dev, Homebrew, pip)
- No hardcoded paths
- Modular documentation (load only what you need)

### 6. Golden Egg Project Templates
Portable documentation system for AI agent collaboration:
- Modular documentation structure (60% context reduction)
- Agent leadership protocols
- Session rotation system
- Integration-ready templates

---

## Installation

### Homebrew (macOS/Linux)
```bash
brew tap proxikal/cerberus
brew install cerberus
```

### From Source
```bash
git clone https://github.com/proxikal/Cerberus.git
cd Cerberus
pip install -e .
```

### Verify Installation
```bash
cerberus version
cerberus doctor  # Run diagnostics
```

---

## Quick Start

### 1. Index Your Project
```bash
cd /path/to/your/project
cerberus index . --ext .py,.js,.ts --json
```

This creates `.cerberus/cerberus.db` with all symbols from your codebase.

### 2. Explore a Directory
```bash
cerberus orient src/
```

Get a high-level overview of directory structure and file types.

### 3. Navigate to a File
```bash
cerberus go src/lib/auth.py --json
```

See all symbols in the file with line numbers (classes, functions, variables).

### 4. Search for Symbols
```bash
cerberus retrieval search "authenticate" --json
```

Find all symbols matching "authenticate" across the entire codebase.

### 5. Get Symbol Details
```bash
cerberus retrieval get-symbol validateToken --json
```

Retrieve the full source code for a specific symbol with surrounding context.

### 6. Skeletonize a File
```bash
cerberus retrieval skeletonize src/lib/auth.py --json
```

Get only function signatures and docstrings (95%+ smaller than full file).

### 7. Generate Blueprint
```bash
cerberus retrieval blueprint src/lib/ --json
```

See architectural structure with dependencies and complexity metrics.

---

## Core Workflows

### For AI Agents

**Exploration Workflow:**
```bash
# 1. Load session memory (patterns, decisions, corrections)
cerberus memory context --compact --json

# 2. Orient to understand structure
cerberus orient src/

# 3. Navigate to specific file
cerberus go src/lib/auth.py --json

# 4. Search for specific symbol
cerberus retrieval search "validateToken" --json

# 5. Get symbol details
cerberus retrieval get-symbol validateToken --json

# 6. Read full implementation (use Read tool on line numbers)
```

**Learning Workflow:**
```bash
# Record architectural decision
cerberus memory learn --decision "Auth uses JWT tokens with 1hr expiry"

# Record coding pattern
cerberus memory learn --pattern "Always await Prisma queries in async functions"

# Record correction
cerberus memory learn --correction "Next.js requires trailingSlash: true in config"

# Retrieve context for next session
cerberus memory context --compact --json
```

### For Developers

**Quick File Navigation:**
```bash
# See what's in a file without opening it
cerberus go src/components/Button.tsx

# Find where a function is defined
cerberus retrieval search "handleSubmit"

# Get only the API surface (signatures)
cerberus retrieval skeletonize src/lib/api.ts
```

**Architecture Understanding:**
```bash
# See high-level structure
cerberus orient src/

# Get dependency map
cerberus retrieval blueprint src/lib/ --json

# Update index after changes
cerberus update --json
```

**Documentation Access:**
```bash
# Quick reference
cerberus docs quick

# Full command reference
cerberus docs commands

# Architecture guide
cerberus docs architecture

# Find where docs are installed
cerberus docs path
```

---

## Command Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `cerberus index <path>` | Create symbol index for codebase |
| `cerberus update` | Incrementally update index based on changes |
| `cerberus start` | Initialize session with health checks |
| `cerberus orient <path>` | Directory overview with structure |
| `cerberus go <file>` | File symbols with line numbers |
| `cerberus doctor` | Run environment diagnostics |

### Retrieval Commands

| Command | Description |
|---------|-------------|
| `cerberus retrieval search <query>` | Search for symbols (BM25 + vector) |
| `cerberus retrieval get-symbol <name>` | Get symbol source code |
| `cerberus retrieval skeletonize <file>` | Get signatures only (no bodies) |
| `cerberus retrieval blueprint <path>` | Architectural overview |
| `cerberus retrieval get-context <symbol>` | Full context payload for symbol |

### Memory Commands

| Command | Description |
|---------|-------------|
| `cerberus memory learn` | Store pattern, decision, or correction |
| `cerberus memory context` | Get all stored patterns for session |
| `cerberus memory show` | Display stored memory |
| `cerberus memory stats` | Memory statistics |
| `cerberus memory export` | Export memory for backup |
| `cerberus memory import` | Import memory from backup |

### Documentation Commands

| Command | Description |
|---------|-------------|
| `cerberus docs quick` | Quick reference (common commands) |
| `cerberus docs commands` | Full command reference |
| `cerberus docs architecture` | Internals & configuration |
| `cerberus docs path` | Show documentation directory |
| `cerberus docs list` | List all available docs |

### Utility Commands

| Command | Description |
|---------|-------------|
| `cerberus utils stats` | Index statistics |
| `cerberus utils bench` | Performance benchmarks |
| `cerberus clean` | Clean cache and database files |
| `cerberus watcher` | Manage background file watcher |

---

## Supported Languages

Cerberus currently supports AST parsing for:

- **Python** (`.py`) - Functions, classes, methods, variables
- **JavaScript** (`.js`) - Functions, classes, methods
- **TypeScript** (`.ts`) - Functions, classes, methods, interfaces, enums, variables
- **Go** (`.go`) - Functions, structs
- **Workflow Markdown** (`.md`) - Section headings in allowlisted workflow docs

**Symbol Detection:**
- Python: `class`, `def` (functions/methods)
- JavaScript: `class`, `function`, async functions
- TypeScript: `class`, `function`, `interface`, `enum`, `const` exports, methods
- Go: `func`, `type ... struct`
- Workflow Markdown: `#`/`##`/`###` heading sections (allowlisted)

---

## Project Templates

Cerberus includes a **Golden Egg** template system for setting up AI agent collaboration in any project.

### What's Included

- **Modular Documentation** - Core guide + on-demand modules (60%+ context reduction)
- **Agent Leadership Protocol** - Intelligent pushback system to protect optimizations
- **Session Rotation System** - Automatic archiving to prevent documentation bloat
- **Operation Checklists** - Machine-readable YAML workflows

### Setup in New Project

```bash
# Navigate to your project
cd /path/to/your/project

# Copy templates
cp -r ~/path/to/Cerberus/project-templates/* .

# Rename for your project (e.g., "MyApp")
mv PROJECT-GUIDE.md MYAPP.md
mv PROJECT-LEADERSHIP.md MYAPP-LEADERSHIP.md
mv PROJECT-HANDOFF.md HANDOFF.md

# Replace placeholders
# {{PROJECT_NAME}} → MyApp
# {{LOCAL_DIR}} → ~/Dev/MyApp
# {{TECH_STACK}} → Your stack

# Initialize Cerberus index
cerberus index . --ext .ts,.js,.py --json

# Create archive directory
mkdir -p .handoff-archive

# Record in memory
cerberus memory learn --decision "Project: MyApp uses golden egg doc system"
```

See `project-templates/README.md` for full setup guide and examples.

---

## Session Memory

The memory system allows patterns and knowledge to persist across sessions.

### Memory Types

1. **Decisions** - Architectural choices
   ```bash
   cerberus memory learn --decision "Use JWT auth with 1hr expiry"
   ```

2. **Patterns** - Coding conventions
   ```bash
   cerberus memory learn --pattern "Always validate input at API boundaries"
   ```

3. **Corrections** - Mistakes to avoid
   ```bash
   cerberus memory learn --correction "Remember to await async Prisma queries"
   ```

4. **Project Info** - Metadata
   ```bash
   cerberus memory learn --project-info "Stack: Next.js 15 + PostgreSQL"
   ```

### Retrieving Memory

```bash
# Get all patterns for session startup
cerberus memory context --compact --json

# View stored memory
cerberus memory show

# Memory statistics
cerberus memory stats
```

### Memory Storage

Memory is stored per-project in:
```
~/.config/cerberus/memory/<project-name>/
├── decisions.json
├── patterns.json
├── corrections.json
└── project_info.json
```

---

## How It Works

### 1. Indexing

```bash
cerberus index . --ext .py,.ts,.js
```

Cerberus:
1. Scans directory for files matching extensions
2. Parses each file into an Abstract Syntax Tree (AST)
3. Extracts symbols (functions, classes, variables) with:
   - Name
   - Type (function, class, method, etc.)
   - Line numbers (start/end)
   - File path
4. Stores symbols in SQLite database (`.cerberus/cerberus.db`)

### 2. Retrieval

```bash
cerberus retrieval search "authenticate"
```

Cerberus:
1. Uses BM25 keyword search on symbol names
2. Optionally uses vector semantic search (if FAISS installed)
3. Returns ranked results with file paths and line numbers
4. Agent uses line numbers to read specific code sections

### 3. Skeletonization

```bash
cerberus retrieval skeletonize src/auth.py
```

Cerberus:
1. Parses file into AST
2. Traverses tree to find function/class nodes
3. Removes function bodies (keeps signatures)
4. Preserves docstrings and type annotations
5. Returns minimal representation (95%+ smaller)

### 4. Memory Context

```bash
cerberus memory context --compact --json
```

Cerberus:
1. Reads all memory files for current project
2. Merges patterns, decisions, corrections
3. Compacts into JSON payload
4. Agent loads at session startup

---

## Requirements

- **Python**: 3.11 or higher
- **Operating System**: macOS, Linux, or Windows WSL
- **Dependencies**: Automatically installed via pip/Homebrew
  - `typer` - CLI framework
  - `rich` - Terminal formatting
  - `pydantic` - Data validation
  - `loguru` - Logging
  - `watchdog` - File watching
  - `rank-bm25` - Keyword search
  - `sentence-transformers` - Semantic search (optional)
  - `tree-sitter` - AST parsing
  - `psutil` - System utilities

### Optional Dependencies

- **FAISS** (`faiss-cpu`) - Vector search for semantic matching (recommended for large codebases >10k files)

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Links

- **GitHub Repository**: https://github.com/proxikal/Cerberus
- **Homebrew Tap**: https://github.com/proxikal/homebrew-cerberus
- **Issues**: https://github.com/proxikal/Cerberus/issues
- **Releases**: https://github.com/proxikal/Cerberus/releases

---

**Cerberus v1.0.0 - Golden Egg Edition**
Empowering AI agents and developers to navigate codebases efficiently.
