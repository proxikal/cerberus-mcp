# Cerberus: The Autonomous Context Engine

**Cerberus** is an intelligent "Context Management Layer" that bridges the gap between autonomous AI agents and massive software engineering projects. It solves the **"Context Wall"** problem by serving high-precision, compacted context to agents on-demand.

[![Status: Production](https://img.shields.io/badge/status-production-green.svg)](#)
[![Tests: 146/156 Passing](https://img.shields.io/badge/tests-146%2F156%20passing-brightgreen.svg)](#)
[![Phase: 5 Complete](https://img.shields.io/badge/phase-5%20complete-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](#)

---

## 📖 Documentation

### User Documentation
- **[Quick Start](#-quick-start)** - Get started in 5 minutes
- **[CLI Reference](#-complete-cli-reference)** - All commands
- **[Competitor Comparison](#-competitor-comparison)** - How Cerberus stacks up

### Developer & Architecture
- **[Architectural Vision](./docs/VISION.md)** - Philosophy & Strategy
- **[Development Mandates](./docs/MANDATES.md)** - Reliability rules
- **[Project Roadmap](./docs/ROADMAP.md)** - Phases 1-6
- **[AI Agent Guide](./docs/AGENT_GUIDE.md)** - Integration instructions

---

## 🚨 The Challenge: The Context Wall

Autonomous AI agents face a critical limitation: **Context Waste**. Reading entire files to find a single function burns tokens, causes "hallucinations" due to context noise, and slows down the engineering loop.

**Cerberus** provides a deterministic **"Mental Map"** of your codebase using Abstract Syntax Trees (AST) and hybrid search.

### 💡 Why Cerberus?

Cerberus is built with an **"Agent-First"** philosophy:

- **🧠 Surgical Precision:** Unlike standard RAG that treats code as raw text chunks, Cerberus indexes by **Symbol Boundaries**. Logic units are always retrieved whole.
- **💓 Git-Native Sync:** By parsing `git diff`, Cerberus only re-parses affected symbols. Your index stays fresh in real-time, even during massive refactors.
- **📉 Token Economy:** With **Skeletonization**, Cerberus can strip logic and send only signatures. Agents "see" the entire structure for 1/100th of the cost.
- **🕸️ Symbolic Intelligence:** Beyond text, it understands **relationships**. It resolves method calls to definitions and tracks types across file boundaries.

---

## 🚀 Core Capabilities

### 🧩 AST-Based Mapping
Uses **Tree-Sitter** to parse code into a structural map. It understands symbol boundaries, parameters, and return types.
**Supports:** Python, JS, TS, JSX, TSX, Go (Rust coming in Phase 6).

### 🔍 Hybrid Retrieval
Combines **BM25 keyword search** with **vector semantic search**. Automatically detects if your query is technical (CamelCase) or conceptual and adjusts the strategy.

### ⚡ Background Watcher
An invisible daemon keeps your index synchronized with filesystem changes. It auto-starts on index commands and uses debounced updates to remain lightweight.

### 🩺 Aegis Reliability
Built-in diagnostics (`cerberus doctor`) ensure your environment is healthy, grammars are compiled, and the index is ready for production.

---

## 📊 Status & Scaling

| Metric | Current Capability | Phase 6 Target |
| :--- | :--- | :--- |
| **Capacity** | 100 - 10,000+ files | **Enterprise Monorepos** |
| **Memory** | < 250 MB (Streaming) | **Constant** |
| **Storage** | SQLite + FAISS (Optional) | **Distributed** |
| **Integrity** | 100% Deterministic | 100% Deterministic |

**Current Version:** Phase 5 Complete (v0.5.0)
**Performance:** Validated on **TensorFlow** (2,949 files, 68,934 symbols) with a 42.6x memory reduction using the new streaming architecture.

---

## 🛠️ Installation & Setup

### 1. Install Cerberus
```bash
git clone https://github.com/proxikal/Cerberus.git
cd Cerberus
pip install -r requirements.txt
```

### 2. Optional: Enable FAISS (Recommended for >10k files)
For massive codebases, installing FAISS enables ultra-fast vector search with constant memory usage.
```bash
pip install faiss-cpu>=1.7.4
```

### 🎯 Quick Start
```bash
# 1. Index your project (creates cerberus.db by default)
cerberus index .

# 2. Search for logic (uses cerberus.db automatically)
cerberus search "how is auth handled"

# 3. Get surgical context
cerberus get-symbol "authenticate_user" --padding 5

# 4. Start real-time sync
cerberus watcher start
```

---

## 🏗️ Architecture

Every package exposes a clean `facade.py` API (Self-Similarity Mandate).

- `scanner/` - Generator-based streaming traversal.
- `parser/` - AST extraction (Tree-Sitter).
- `index/` - Persistence (SQLite + FAISS).
- `retrieval/` - Hybrid search (BM25 + Vector).
- `resolution/` - Symbolic intelligence (Phase 5).
- `synthesis/` - Context compaction (Skeletonization).

---

## 🗺️ Roadmap

### ✅ Phases 1-5 (Complete)
- AST Parsing, Hybrid Search, Background Watcher.
- Aegis-Scale (SQLite) streaming architecture.
- Symbolic Intelligence (Method/Type resolution).

### 🔮 Phase 6: Advanced Context Synthesis (Active)
- **Inheritance Resolution:** Track method inheritance through class hierarchies.
- **Cross-File Inference:** Advanced dataflow analysis for deeper context.
- **Native Plugins:** Official tool-sets for LangChain, CrewAI, and AutoGPT.

---

## 🏁 Competitor Comparison

| Feature | Cerberus | Cursor / Copilot | Sourcegraph | Aider |
| :--- | :--- | :--- | :--- | :--- |
| **Parsing** | **AST-Based (Surgical)** | Text Chunks | LSIF (Heavy) | Simple Map |
| **Infrastructure** | **100% Local** | Cloud-Dependent | Enterprise | Local |
| **Git Integration** | **Native (Surgical)** | Basic Hash | Repository Sync | Manual |
| **Context Tooling** | **Skeletonizer** | Snippets | Full File | Repomap |

---

**Cerberus: Empowering AI agents to work efficiently with massive codebases.**