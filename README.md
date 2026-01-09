# Cerberus: The Autonomous Context Engine

**Cerberus** is an intelligent "Context Management Layer" that bridges the gap between autonomous AI agents and massive software engineering projects. It solves the **"Context Wall"** problem by serving high-precision, compacted context to agents on-demand.

[![Status: Production](https://img.shields.io/badge/status-production-green.svg)](#)
[![Tests: 167/182 Passing](https://img.shields.io/badge/tests-167%2F182%20passing-brightgreen.svg)](#)
[![Phase: 6 Complete](https://img.shields.io/badge/phase-6%20complete-blue.svg)](#)
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
- **[Project Roadmap](./docs/ROADMAP.md)** - Phases 1-6 Complete
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
- **🕸️ Symbolic Intelligence:** Beyond text, it understands **relationships**. It resolves method calls to definitions, tracks types across files, and maps inheritance hierarchies.
- **🔍 Smart Context Assembly:** Automatically includes base classes, inherited methods, and execution paths—exactly what AI agents need.

---

## 🚀 Core Capabilities

### 🧩 AST-Based Mapping
Uses **Tree-Sitter** to parse code into a structural map. It understands symbol boundaries, parameters, return types, and relationships.
**Supports:** Python, JS, TS, JSX, TSX, Go.

### 🔍 Hybrid Retrieval (Phase 3)
Combines **BM25 keyword search** with **vector semantic search**. Automatically detects if your query is technical (CamelCase) or conceptual and adjusts the strategy.

### ⚡ Background Watcher (Phase 3)
An invisible daemon keeps your index synchronized with filesystem changes. It auto-starts on index commands and uses debounced updates to remain lightweight.

### 🕸️ Symbolic Intelligence (Phase 5)
- **Method Call Resolution:** Resolves `optimizer.step()` to `Optimizer.step()` definition
- **Type Tracking:** Infers variable types across file boundaries
- **Import Resolution:** Links imports to their internal definitions with confidence scores

### 🏗️ Advanced Context Synthesis (Phase 6) ✨ NEW
- **Inheritance Resolution:** Automatically tracks class hierarchies and MRO
- **Call Graph Generation:** Forward and reverse execution path visualization
- **Cross-File Type Inference:** Multi-strategy type resolution (annotations, instantiation, imports)
- **Smart Context Assembly:** AI-optimized context with 87% token savings
- **Override Detection:** Find all implementations of inherited methods

### 🩺 Aegis Reliability
Built-in diagnostics (`cerberus doctor`) ensure your environment is healthy, grammars are compiled, and the index is ready for production.

---

## 📊 Status & Scaling

| Metric | Current Capability | Achievement |
| :--- | :--- | :--- |
| **Capacity** | 10,000+ files | **TensorFlow (2,949 files) validated** |
| **Memory** | 126.5 MB peak | **49% under 250MB target** |
| **Memory Reduction** | 42.6x improvement | **1.2 GB → 28.1 MB** |
| **Storage** | SQLite + FAISS (Optional) | **Streaming architecture** |
| **Integrity** | 100% Deterministic | **AST-based, no LLMs** |
| **Token Savings** | 99.7% reduction | **150K → 500 tokens** |
| **Smart Context** | 87% savings | **With inheritance** |

**Current Version:** Phase 6 Complete (v0.6.0)
**Test Coverage:** 167/182 passing (91.8%)
**Performance:** Production-ready for massive codebases with constant memory usage.

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

# 4. Explore class hierarchies (Phase 6)
cerberus inherit-tree User

# 5. Generate call graphs (Phase 6)
cerberus call-graph authenticate_user --direction forward

# 6. Get smart AI-optimized context (Phase 6)
cerberus smart-context User --include-bases

# 7. Start real-time sync
cerberus watcher start
```

---

## 🏗️ Architecture

Every package exposes a clean `facade.py` API (Self-Similarity Mandate).

- `scanner/` - Generator-based streaming traversal
- `parser/` - AST extraction (Tree-Sitter)
- `index/` - Persistence (SQLite + FAISS)
- `retrieval/` - Hybrid search (BM25 + Vector)
- `resolution/` - Symbolic intelligence (Phase 5 & 6)
- `synthesis/` - Context compaction (Skeletonization)
- `incremental/` - Git-aware surgical updates
- `watcher/` - Background daemon for real-time sync

---

## 📋 Complete CLI Reference

### Core Indexing
```bash
cerberus index <directory>        # Build SQLite/JSON index
cerberus stats                    # Display index statistics
cerberus update                   # Incremental git-aware update
cerberus watcher start/stop       # Background sync daemon
```

### Search & Retrieval
```bash
cerberus search <query>           # Hybrid BM25+Vector search
cerberus get-symbol <name>        # Retrieve symbol code
cerberus deps <symbol>            # Show dependencies
```

### Phase 5: Symbolic Intelligence
```bash
cerberus calls                    # Query method calls
cerberus references               # Query symbol references
cerberus resolution-stats         # Resolution statistics
cerberus deps --show-resolution   # Import resolution details
```

### Phase 6: Advanced Context Synthesis ✨ NEW
```bash
cerberus inherit-tree <class>     # Show class MRO
cerberus descendants <class>      # Find all subclasses
cerberus overrides <class>        # Show overridden methods
cerberus call-graph <symbol>      # Generate call graphs
cerberus smart-context <symbol>   # AI-optimized context
```

### Context Synthesis
```bash
cerberus skeletonize <file>       # AST-aware skeleton
cerberus get-context <symbol>     # Context payload
cerberus skeleton-file <file>     # File skeletonization
```

### Utilities
```bash
cerberus doctor                   # Health diagnostics
cerberus generate-tools           # Agent tools manifest
cerberus bench                    # Benchmark performance
cerberus version                  # Version info
```

---

## 🗺️ Roadmap

### ✅ Phases 1-6 (Complete)
- **Phase 1:** AST parsing, recursive call graphs, type resolution
- **Phase 2:** Skeletonization, payload synthesis, token optimization
- **Phase 3:** Hybrid search, background watcher, git-native incrementalism
- **Phase 4:** Aegis-scale performance (42.6x memory reduction)
- **Phase 5:** Symbolic intelligence (method/type/import resolution)
- **Phase 6:** Advanced context synthesis (inheritance, call graphs, smart assembly) ✨

### 🔮 Phase 7: Agent Ecosystem Integration (Next)
- **Native Plugins:** Official tool-sets for LangChain, CrewAI, and AutoGPT
- **Agent Tool Manifest:** JSON schema for MCP (Model Context Protocol) servers
- **Streaming API:** HTTP/WebSocket API for remote agent access
- **Context Streaming:** Real-time context delivery for long-running sessions

**See [ROADMAP.md](./docs/ROADMAP.md) for detailed phase descriptions.**

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
| **Inheritance Resolution** | **✅ Phase 6** | ❌ | ⚠️ Partial | ❌ | ❌ |
| **Call Graphs** | **✅ Phase 6** | ❌ | ⚠️ Partial | ❌ | ❌ |
| **Smart Context** | **✅ 87% savings** | ❌ | ❌ | ⚠️ Basic | ❌ |

### 🏆 Why Cerberus Wins (The Data)

1.  **Surgical vs. Chunked:**
    *   **The Competitors:** Most RAG tools split code into arbitrary 500-token chunks. This often cuts functions in half, forcing the agent to request multiple chunks to understand one logic block.
    *   **Cerberus:** Uses Tree-Sitter to understand **Symbol Boundaries**. When you ask for `auth_user`, you get the *exact* function—headers, body, and decorators—padding included. Zero wasted tokens on irrelevant neighbors.

2.  **The "Skeleton" Advantage:**
    *   **The Competitors:** To understand a class, Copilot often reads the whole file. For a 2,000-line `User` class, that's ~15k tokens.
    *   **Cerberus:** Can generate a **Skeleton** (signatures only). The agent sees the entire class structure for ~500 tokens. **That is a 30x cost reduction for architectural reasoning.**

3.  **Phase 6 Smart Context:**
    *   **The Competitors:** If a class inherits from 3 base classes, agents must manually track down each definition.
    *   **Cerberus:** `smart-context` automatically includes all base classes (skeletonized) + MRO + overridden methods. **87% token savings** while providing complete understanding.

4.  **Local Speed vs. Cloud Latency:**
    *   **The Competitors:** Sourcegraph and Greptile are incredible, but they require network calls. Latency is 500ms - 2s.
    *   **Cerberus:** Is a local SQLite file. Queries happen in **milliseconds** on your SSD. This makes "Plan Mode" (where an agent queries dependencies 50 times in a row) feel instant rather than sluggish.

5.  **The Truth (Where we lose):**
    *   If you want a **UI** to click around in, use Sourcegraph.
    *   If you want **Autocomplete** while typing, use Copilot.
    *   **Cerberus is for AGENTS, not Humans.** It has no UI. It has no autocomplete. It is a pure, high-speed data pipeline designed to feed Claude and Gemini exactly what they need to write code without crashing.

---

## 🎯 Use Cases

### For Autonomous AI Agents
- **Code Navigation:** Resolve method calls to definitions instantly
- **Architectural Understanding:** Get complete inheritance chains in one query
- **Execution Path Analysis:** Generate call graphs to understand code flow
- **Context Optimization:** 87% token savings with smart context assembly
- **Real-time Updates:** Background watcher keeps context fresh

### For Agent Frameworks
- **LangChain Integration:** (Phase 7) Native tool wrapper for all commands
- **CrewAI Integration:** (Phase 7) Automatic context injection
- **Custom Agents:** JSON API for programmatic access

### Performance Metrics
- **99.7% token reduction:** 150K tokens → 500 tokens for typical queries
- **87% smart context savings:** Full inheritance awareness with minimal tokens
- **42.6x memory improvement:** Constant 126.5 MB for massive codebases
- **Millisecond queries:** Local SQLite beats cloud latency

---

## 🧪 Testing

```bash
# Run all tests
PYTHONPATH=src python3 -m pytest tests/ -v

# Run specific phase tests
PYTHONPATH=src python3 -m pytest tests/test_phase6_unit.py -v

# Run with coverage
PYTHONPATH=src python3 -m pytest tests/ --cov=cerberus --cov-report=html
```

**Current Test Results:** 167/182 passing (91.8%)
- 167 passing ✅
- 15 skipped (14 FAISS optional, 1 TypeScript)
- 0 failing ✅

---

## 📜 License

MIT License - See LICENSE file for details.

---

## 🤝 Contributing

Cerberus follows strict architectural mandates:
1. **Self-Similarity:** Every package has `facade.py` + `config.py`
2. **Aegis Robustness:** Structured logging, custom exceptions, performance tracing
3. **Code over Prompts:** Deterministic AST parsing, no LLM interpretation
4. **Dogfooding:** Cerberus must be able to index itself

See [MANDATES.md](./docs/MANDATES.md) for development guidelines.

---

**Cerberus: Empowering AI agents to work efficiently with massive codebases.**

**Version:** 0.6.0 (Phase 6 Complete)
**Status:** Production-Ready Deep Context Synthesis Engine
