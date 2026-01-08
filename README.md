# Cerberus: The Autonomous Context Engine

[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](#)
[![Tech: Python 3.10+](https://img.shields.io/badge/tech-python--3.10+-blue.svg)](#)

**Cerberus** is an intelligent "Context Management Layer" designed to bridge the gap between autonomous AI agents and massive software engineering projects. It solves the **"Context Wall"** problem by pre-processing, indexing, and dynamically serving only the most relevant, compacted context to agents on-demand.

---

## 🚀 The Problem: The Context Wall

Autonomous agents today face a critical limitation when working on large-scale repositories:
- **Context Limits:** Projects often exceed LLM context windows, causing agents to "forget" architecture or lose track of dependencies.
- **API Costs:** Blindly reading full files to find single functions burns through tokens and increases latency.
- **Structural Fragmentation:** Agents lose the "big picture" when forced to operate on isolated text chunks without understanding the underlying AST (Abstract Syntax Tree).

## 🛡️ The Solution: Cerberus

Cerberus acts as a persistent, intelligent interface for your codebase. Instead of an agent reading `UserAuth.ts` (500 lines) + `database.py` (800 lines) just to find a specific interaction, it queries Cerberus:
> *"Retrieve the function `handleLogin` and its local dependencies."*

Cerberus returns a **Compact Context Payload**: the exact lines, signatures, and relevant context needed for the task, resulting in a **10x-50x reduction in token usage**.

---

## ✨ Key Features

### 🧩 AST-Based Chunking
Unlike simple text splitters, Cerberus uses **Tree-Sitter** to parse code into a structural map of functions, classes, methods, and variables. It understands the difference between a comment and a class definition.

### 🧠 Semantic & Hybrid Search
Cerberus combines precise keyword lookup with vector-based **Semantic Search**. Using transformer embeddings (e.g., `all-MiniLM-L6-v2`), agents can find code by *intent* ("Find the logic that handles JWT validation") rather than just filenames.

### 🕸️ Project Graph Mapping
Cerberus builds a navigable graph of the project, tracking symbol definitions across files. This allows for deep retrieval of related symbols and dependency chains.

### 📉 Context Compaction
Optimized retrieval logic ensures that agents only receive what is necessary. It supports "padded" snippets, signature-only views, and summarized architectural overviews.

---

## 🏗️ System Architecture

Cerberus is built on the **Self-Similarity Mandate**: its architecture is so clean and modular that an AI agent can maintain Cerberus using Cerberus itself.

1.  **Schema Layer (`schemas.py`):** The single source of truth for all data structures (FileObjects, CodeSymbols, SearchResults).
2.  **The Scanner (`scanner/`):** The "Legs." Efficiently walks the filesystem, respecting `.gitignore` and `.cerberusignore`.
3.  **The Parser (`parser/`):** The "Eyes." Extracts structure (AST) using language-specific Tree-Sitter adapters (Python, JS, TS, etc.).
4.  **The Brain (`index/` & `semantic/`):** The "Memory." Manages persistence (JSON/Vector DB) and handles semantic queries.
5.  **The Interface (`main.py`):** The "Mouth." A high-performance CLI built with **Typer** for both humans and machines.

---

## 🛠️ CLI Usage Guide

Cerberus is designed to be "Agent-Native," with every command supporting a `--json` flag for easy machine integration.

### 🔍 Discovery & Scanning
```bash
# Map a project's files and metadata
cerberus scan ./src --ext .py --ext .ts

# Generate a persistent index
cerberus index ./src -o my_project.json --store-embeddings
```

### 🎯 Targeted Retrieval
```bash
# Get the exact code for a specific function with context
cerberus get-symbol "login_user" --padding 5 --json

# Perform a semantic search across the codebase
cerberus search "how do we handle database connections?" --limit 3
```

### 🩺 Maintenance & Stats
```bash
# Check index health and symbol breakdown
cerberus stats --index my_project.json

# Run environment diagnostics
cerberus doctor
```

---

## 🛠️ Tech Stack

- **Core:** Python 3.10+
- **Parsing:** Tree-Sitter
- **CLI:** Typer & Rich
- **Data:** Pydantic (Strict Typing)
- **ML/Embeddings:** Sentence-Transformers (Local-first)
- **Logging:** Loguru (JSON-stream for agents)

---

## 🔮 Strategic Roadmap

- [x] **MVP:** AST Scanning, Basic Indexing, CLI Interface.
- [x] **Semantic Layer:** Local Vector Search integration.
- [ ] **Dependency Graph:** Mapping `import` chains and cross-file calls.
- [ ] **Compaction Engine:** Automated summarization of large files.
- [ ] **Agent Plugins:** Official tools for LangChain, AutoGPT, and custom CLI agents.

---
*Developed by the Aegis Foundation. Built for the future of autonomous engineering.*