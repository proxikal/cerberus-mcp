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

Cerberus occupies a specialized niche: **The Local Context Engine.** Unlike IDE plugins or cloud search engines, Cerberus is designed to be the "Cortex" for autonomous agents.

| Feature | Cerberus | Cursor / Copilot | Sourcegraph | Aider | Standard RAG |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Parsing** | **AST-Based (Surgical)** | Text-Based (Chunks) | LSIF (Heavy) | Simple Map | Raw Chunks |
| **Infrastructure** | **100% Local** | Cloud-Dependent | Enterprise/Cloud | Local | Cloud API |
| **Git Integration** | **Native (Diff-Aware)** | Basic Hash | Repository Sync | None/Manual | None |
| **Agent Interface** | **JSON / API** | IDE UI | Web UI / API | Chat UI | Vector DB |
| **Cost (Tokens)** | **$ (Surgical)** | $$ (Full Files) | N/A (Search) | $ (Map) | $$ (Dump) |

### 🏆 Why Cerberus Wins (The Data)

1.  **Surgical vs. Chunked:** 
    *   **The Competitors:** Most RAG tools split code into arbitrary 500-token chunks. This often cuts functions in half, forcing the agent to request multiple chunks to understand one logic block.
    *   **Cerberus:** Uses Tree-Sitter to understand **Symbol Boundaries**. When you ask for `auth_user`, you get the *exact* function—headers, body, and decorators—padding included. Zero wasted tokens on irrelevant neighbors.

2.  **The "Skeleton" Advantage:**
    *   **The Competitors:** To understand a class, Copilot often reads the whole file. For a 2,000-line `User` class, that's ~15k tokens.
    *   **Cerberus:** Can generate a **Skeleton** (signatures only). The agent sees the entire class structure for ~500 tokens. **That is a 30x cost reduction for architectural reasoning.**

3.  **Local Speed vs. Cloud Latency:**
    *   **The Competitors:** Sourcegraph and Greptile are incredible, but they require network calls. Latency is 500ms - 2s.
    *   **Cerberus:** Is a local SQLite file. Queries happen in **milliseconds** on your SSD. This makes "Plan Mode" (where an agent queries dependencies 50 times in a row) feel instant rather than sluggish.

4.  **The Truth (Where we lose):**
    *   If you want a **UI** to click around in, use Sourcegraph.
    *   If you want **Autocomplete** while typing, use Copilot.
    *   **Cerberus is for AGENTS, not Humans.** It has no UI. It has no autocomplete. It is a pure, high-speed data pipeline designed to feed Claude and Gemini exactly what they need to write code without crashing.

---

**Cerberus: Empowering AI agents to work efficiently with massive codebases.**