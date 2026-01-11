# Cerberus: The Autonomous AI Agent Operating System

**Cerberus** is a high-precision "Context Management Layer" designed for autonomous AI agents working on massive, complex codebases. It solves the **"Context Wall"** problem by serving deterministic, AST-aware, and token-optimized context on-demand.

[![Version: 0.19.9](https://img.shields.io/badge/version-0.19.9-blue.svg)](#)
[![Status: Production-Ready](https://img.shields.io/badge/status-production--ready-green.svg)](#)
[![Tests: 586/587 Passing](https://img.shields.io/badge/tests-586%2F587%20passing-brightgreen.svg)](#)
[![Phase: 19.5 Complete](https://img.shields.io/badge/phase-19.5%20complete-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](#)

---

## 📖 Table of Contents

- [🚨 The Challenge: The Context Wall](#-the-challenge-the-context-wall)
- [🧠 The Solution: Agent-First Intelligence](#-the-solution-agent-first-intelligence)
- [🚀 Core Capabilities](#-core-capabilities)
  - [🧩 AST-Based Mapping](#-ast-based-mapping)
  - [🔍 Hybrid Retrieval](#-hybrid-retrieval)
  - [⚡ Performance Daemon](#-performance-daemon)
  - [🕸️ Symbolic Intelligence](#-symbolic-intelligence)
- [🏗️ Phase 13: Architectural Intelligence](#-phase-13-architectural-intelligence)
  - [🗺️ Visual Blueprints](#-visual-blueprints)
  - [📊 Stability & Risk Scoring](#-stability--risk-scoring)
  - [🔄 Structural Diffs](#-structural-diffs)
  - [💧 Auto-Hydration](#-auto-hydration)
- [🔮 Phase 14: Productivity Enhancements](#-phase-14-productivity-enhancements)
- [🏁 Competitive Comparison](#-competitive-comparison)
  - [Feature Matrix](#feature-matrix)
  - [Real-World Metrics](#real-world-metrics)
  - [🏆 Why Choose Cerberus?](#-why-choose-cerberus)
- [🛠️ Installation & Setup](#️-installation--setup)
- [🎯 Quick Start](#-quick-start)
- [📋 CLI Reference](#-cli-reference)
- [🏗️ Architecture](#️-architecture)
- [🧪 Testing](#-testing)
- [📜 License](#-license)

---

## 🚨 The Challenge: The Context Wall

Autonomous AI agents face three critical bottlenecks when working on real-world software:

1.  **Token Waste:** Reading 2,000 lines of code to find a 5-line logic bug is expensive and slow.
2.  **Context Noise:** Irrelevant code "distracts" LLMs, leading to hallucinations and poor reasoning.
3.  **Stateless Exploration:** Agents spend multiple turns "wandering" through directories just to understand the architecture.

**Cerberus** provides a deterministic **"Cortex"** that bridges this gap, allowing agents to navigate code at the speed of thought.

---

## 🧠 The Solution: Agent-First Intelligence

Cerberus is built on the **"Zero Guesswork"** principle. Unlike RAG-based tools that treat code as raw text chunks, Cerberus uses **Abstract Syntax Trees (AST)** to index your project.

- **Surgical Precision:** Every symbol (function, class, variable) is indexed by its exact byte boundaries.
- **Symbolic Intelligence:** It understands relationships. It resolves method calls, tracks types across files, and maps inheritance hierarchies.
- **Deterministic Scaling:** Validated on **TensorFlow** (2,949 files, 68k symbols) with constant memory usage (< 130MB).
- **Machine-First Protocol:** Defaulting to **minified JSON** for agents, with an optional `--human` mode for developers.

---

## 🚀 Core Capabilities

### 🧩 AST-Based Mapping
Uses **Tree-Sitter** to parse code into a structural map. It understands symbol boundaries, parameters, return types, and relationships.
**Supports:** Python, JS, TS, JSX, TSX, Go, Java, C++, Rust.

### 🔍 Hybrid Retrieval
Combines **BM25 keyword search** with **vector semantic search**. Automatically detects if a query is technical (`CamelCase`) or conceptual and adjusts the strategy.

### ⚡ Performance Daemon (`cerberus serve`)
A persistent background process that eliminates the "Python Startup Tax." Queries are resolved in **milliseconds (< 50ms)**, enabling instant agent exploration.

### 🕸️ Symbolic Intelligence
- **Method Call Resolution:** Resolves calls across the entire project with confidence scores.
- **Inheritance Awareness:** Automatically tracks class MRO (Method Resolution Order) and overrides.
- **Cross-File Type Inference:** Infers types from annotations, imports, and instantiations.

---

## 🏗️ Phase 13: Architectural Intelligence

Phase 13 transforms Cerberus from a search tool into a high-fidelity **Architectural Intelligence System**.

### 🗺️ Visual Blueprints (`blueprint`)
Generate token-efficient ASCII trees of your codebase. See the "Mental Map" without reading the logic.
- `cerberus blueprint src/file.py --deps` (Shows what functions call)
- `cerberus blueprint src/file.py --meta` (Shows complexity & size)

### 📊 Stability & Risk Scoring
Identify "Dragons" before touching the code. Cerberus calculates a **Stability Score** (0.0 - 1.0) based on:
- **Git Churn:** How often is this symbol edited?
- **Test Coverage:** Is this logic protected by tests?
- **Complexity:** How deep is the nesting/branching?
- **Result:** 🟢 SAFE, 🟡 MEDIUM, or 🔴 HIGH RISK.

### 🔄 Structural Diffs
Compare the **Architecture** between commits, not just the text.
- `cerberus blueprint --diff HEAD~1` (Shows added/removed/modified symbols).

### 💧 Auto-Hydration
Eliminate the "Search -> Read -> Search" loop. Cerberus pre-fetches skeletons of all referenced internal dependencies in a single query.

---

## 🔮 Phase 14: Productivity Enhancements

The productivity layer for next-generation AI Engineers is now complete:

- **🛡️ Style Guard (14.1):** AST-based style fixing (whitespace, imports, quotes) that requires explicit agent action via `cerberus quality style-fix`. ✅
- **⚓ Context Anchors (14.2):** Persistent "GPS" metadata (file, lines, dependencies, risk, temporal) injected into all outputs to prevent context drift in long sessions. ✅
- **🔮 Predictive Editing (14.3):** Deterministic suggestions for related changes based on AST call graphs. After editing a symbol, Cerberus automatically suggests direct callers, dependencies, and test files via `cerberus quality related-changes`. ✅

### How it Works

When you edit a symbol, Cerberus now proactively suggests related changes:

```bash
$ cerberus mutations edit src/auth.py --symbol validate_token --code "..."
✓ Successfully edited 'validate_token'
🔮 [Predictive] Related changes suggested (2 HIGH confidence):
  1. middleware.py:45 - Direct caller (AST-verified)
  2. test_auth.py:89 - Test file (exact match + verified import)
💡 Review with: cerberus quality related-changes validate_token
```

**Key Principles:**
- **100% Deterministic:** Only AST-verified relationships, no heuristics or ML
- **High Confidence Only:** Minimum threshold of 0.9 confidence score
- **Zero Noise:** Only shows top 5 predictions to avoid overwhelming the agent

---

## 🏁 Competitive Comparison

### Feature Matrix

| Feature | Cerberus | Cursor / Copilot | Aider | Sourcegraph | Greptile | RAG |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **AST-Based Parsing** | ✅ | ❌ | ⚠️ | ⚠️ | ❌ | ❌ |
| **100% Local** | ✅ | ❌ | ✅ | ⚠️ | ❌ | ⚠️ |
| **Git-Diff Aware** | ✅ | ❌ | ✅ | ⚠️ | ❌ | ❌ |
| **Call Graphs** | ✅ | ❌ | ❌ | ⚠️ | ❌ | ❌ |
| **Stability Scoring** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Architectural Diffs** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Symbolic Editing** | ✅ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ |
| **Agent-First API** | ✅ | ❌ | ⚠️ | ⚠️ | ✅ | ✅ |

### Real-World Metrics

| Metric | Cerberus | Aider | Cursor | Sourcegraph | Greptile | RAG |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Token Efficiency** | **99.7%** | ~60% | ~40% | N/A | ~70% | ~80% |
| **Latency (avg)** | **15ms** | N/A | 50ms | 800ms | 600ms | 400ms |
| **Memory (10K files)** | **126MB** | ~50MB | N/A | N/A | N/A | ~200MB |
| **Cost (10K queries)** | **$0** | $0 | $20 | $129+ | $99+ | $5-50 |

*Tested on M1 Mac, 2K file codebase, 100-query averages.*

### 🏆 Why Choose Cerberus?

1.  **Surgical Precision vs. Text Chunks:** RAG tools split code into random chunks, often cutting functions mid-logic. Cerberus respects symbol boundaries—you get complete functions, never fragments.
2.  **The Skeleton Advantage:** Understanding a 2,000-line class costs ~15K tokens. Cerberus shows signatures only—full structure for ~500 tokens (96.7% reduction).
3.  **Millisecond Latency:** Local SQLite queries in 5-20ms. Agent "plan mode" (50+ rapid queries) feels instant, not sluggish.
4.  **Aegis Safety:** Integrated `batch-edit --verify` ensures that an agent **cannot break your build**. If tests fail, it auto-reverts.

---

## 🛠️ Installation & Setup

### 1. Install Cerberus
```bash
git clone https://github.com/proxikal/Cerberus.git
cd Cerberus
pip install -r requirements.txt
```

### 2. Enable FAISS (Recommended for >10k files)
```bash
pip install faiss-cpu>=1.7.4
```

---

## 🎯 Quick Start

```bash
# 1. Index your project
cerberus index .

# 2. Get architectural overview (Phase 13)
cerberus blueprint src/ --aggregate --stability

# 3. Search conceptually
cerberus search "how is user auth handled"

# 4. Get surgical symbol code
cerberus get-symbol "authenticate_user"

# 5. Smart context (includes inheritance + deps)
cerberus smart-context "UserClass" --include-bases --auto-hydrate

# 6. Atomic mutation with verification (Phase 12)
cerberus batch-edit ops.json --verify "pytest tests/"

# 7. Start real-time sync daemon (Phase 9)
cerberus serve
```

---

## 📋 CLI Reference

### 🗺️ Orientation (Phase 13)
- `cerberus blueprint <file>` - Structural tree
- `cerberus blueprint <file> --deps` - + Dependency overlay
- `cerberus blueprint <file> --meta` - + Complexity metrics
- `cerberus blueprint <file> --stability` - + Risk scoring
- `cerberus blueprint --diff <ref>` - Structural differences
- `cerberus blueprint src/ --aggregate` - Package-level view

### 🔍 Retrieval & Search
- `cerberus search <query>` - Hybrid BM25 + Vector search
- `cerberus get-symbol <name>` - Retrieve symbol source code
- `cerberus smart-context <symbol>` - AI-optimized payload
- `cerberus trace-path <src> <dest>` - Execution path mapping

### 🕸️ Symbolic Intelligence
- `cerberus calls <symbol>` - Forward call graph
- `cerberus references <symbol>` - Reverse call graph (Who calls this?)
- `cerberus inherit-tree <class>` - Full inheritance MRO
- `cerberus deps <symbol>` - Dependency analysis with confidence scores

### ✍️ Mutations (Surgical Editing)
- `cerberus edit <file> --symbol <name> --code "..."` - Edit by name
- `cerberus insert <file> --after <name> --code "..."` - AST-aware injection
- `cerberus batch-edit <json_file> --verify <cmd>` - Atomic verified refactor
- `cerberus undo` - Revert last successful mutation

### 🩺 Operational
- `cerberus doctor` - Health & environment diagnostics
- `cerberus serve` - Start the high-performance daemon
- `cerberus stats` - Index statistics (tokens, symbols, files)
- `cerberus bench` - Performance benchmarks

---

## 🏗️ Architecture

Cerberus follows a strict **Decoupled Facade** architecture (Self-Similarity Mandate):

- `parser/` - Tree-Sitter AST extraction
- `index/` - Hybrid storage (SQLite + FAISS)
- `retrieval/` - BM25 + Vector search logic
- `resolution/` - Symbolic resolution (Types, Calls, Inheritance)
- `mutation/` - AST-aware surgical editing
- `blueprint/` - Architectural intelligence & visualization
- `quality/` - Style Guard & Predictive suggestions (Phase 14)
- `daemon/` - High-performance background server

---

## 🧪 Testing

Cerberus is built for production environments where reliability is non-negotiable.

```bash
# Run all tests
PYTHONPATH=src python3 -m pytest tests/ -v

# Run specific phase tests
PYTHONPATH=src python3 -m pytest tests/test_phase13_5.py -v
```

**Current Results:** 274 Passing | 15 Skipped (Optional FAISS/TS) | 0 Failing.

---

## 📜 License

MIT License. See `LICENSE` for details.

---

**Cerberus: Empowering AI agents to work efficiently with massive codebases.**

**Version:** 0.13.0 (Phase 13 Complete)
**Validated On:** TensorFlow (2,949 files, 68,934 symbols)
**Dogfooding Status:** Cerberus is used to build Cerberus.