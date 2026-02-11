# Cerberus MCP

<!-- BADGES: Verified Status -->
![Tests](https://github.com/proxikal/cerberus-mcp/actions/workflows/test-mcp.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)
![Code Style](https://img.shields.io/badge/Code%20Style-Ruff-black?style=flat-square)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)

> **Model Context Protocol server for intelligent code exploration with AST-based navigation and persistent session memory.**

---

## ⚠️ **Important Notice**

**Cerberus is in early development and highly experimental.** While functional, it has rough edges:

- **Large Project Performance:** Indexing time scales linearly with codebase size (~8 minutes for 6200 files with semantic search enabled, ~45 seconds without embeddings)
- **Memory Usage:** Semantic search model requires ~400MB RAM (bundled all-MiniLM-L6-v2)
- **Breaking Changes:** API and tool signatures may change as we refine features
- **Limited Testing:** Not all edge cases are covered; bugs expected in complex scenarios
- **Resource Intensive:** FAISS + embedding generation can heat up laptops on large codebases

**Use at your own risk. Not recommended for production workflows yet.**

---

## ⚡ Core Features

| Feature | Description | Real Performance |
| :--- | :--- | :--- |
| **🔍 AST-Based Search** | Navigate code via Abstract Syntax Trees + semantic search (enabled by default with bundled model). | Semantic: 0.3-0.5 similarity scores. Keyword fallback if embeddings unavailable. |
| **🧠 Persistent Memory** | Dual-layer system: Global Preferences (everywhere) and Project Decisions (context-specific). | SQLite-backed, FTS5 search, ~50-200 tokens per memory context load. |
| **📉 Token Efficiency** | Skeletonization strips implementations, context assembly fetches only needed code. | **Measured: 60-75% savings** vs reading full files (not 90%, that was exaggerated). |

---

## 📊 Real-World Benchmarks

**Tested on Cerberus itself** (6,206 files, 93,643 symbols):

| Operation | Time | Tokens | Notes |
|-----------|------|--------|-------|
| **Index Build (with embeddings)** | ~8.3 minutes | N/A | FAISS + all-MiniLM-L6-v2 generation |
| **Index Build (without embeddings)** | ~45 seconds | N/A | SQLite only, keyword search fallback |
| **Semantic Search (5 results)** | <1s | ~450 tokens | Includes similarity scores |
| **Get Symbol (code only)** | <0.5s | ~1,300 tokens | 75% vs full file read (~5,355 tokens) |
| **Context (with deps)** | <1s | ~2,000-4,000 tokens | Depends on symbol complexity |

**Token Efficiency Reality Check:**
- **Claim:** "90% savings"
- **Reality:** **60-75% savings** in typical workflows (still significant!)
- **Why less?** Full file reads rarely needed; comparison isn't apples-to-apples

---

## 🛠️ Tech Stack

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastMCP](https://img.shields.io/badge/FastMCP-Enabled-000000?style=for-the-badge)
![TreeSitter](https://img.shields.io/badge/Tree--Sitter-Parser-green?style=for-the-badge)
![SQLite](https://img.shields.io/badge/SQLite-Memory-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-Semantic-blue?style=for-the-badge)

---

## 🚀 Quick Start

**Prerequisites:** Python 3.10+, ~1GB disk space for index, 500MB RAM for semantic search

### 1. Install MCP Server

```bash
pip install git+https://github.com/proxikal/cerberus-mcp.git
```

### 2. Configure Your AI Agent

Add to your MCP configuration (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "cerberus": {
      "command": "cerberus-mcp"
    }
  }
}
```

### 3. Install Agent Skill (Recommended)

```bash
# Deploys specialized prompts that help agents use Cerberus effectively
mkdir -p ~/.claude/skills/Cerberus
cp -r skill/Cerberus/* ~/.claude/skills/Cerberus/
```

### 4. First Run

```
# In your AI agent (e.g., Claude Code):
# The agent will automatically call index_build on first use
# Expect 1-10 minutes depending on codebase size
```

---

## 🤖 Optional: Local LLM Summarization

Cerberus supports **zero-token file summarization** using local LLMs via [llm-toolchain](https://github.com/proxikal/llm-toolchain).

### Installation

```bash
# Install llm-toolchain (optional)
pip install llm-toolchain

# Requires Ollama running locally
# Download from: https://ollama.ai
```

### Configuration

Add to your `cerberus.toml`:

```toml
[summarization]
enabled = true
model = "qwen3:8b"  # Best for tool calling (or any Ollama model)
ollama_url = "http://localhost:11434"
```

**How it works:**
- If `llm-toolchain` installed → uses zero-token file operations
- If not installed → falls back to direct file reads (standard behavior)
- If Ollama unavailable → summarization gracefully disabled

---

## 📚 Documentation Portal

We maintain detailed documentation in our [Wiki](https://github.com/proxikal/cerberus-mcp/wiki).

| Section | Content |
| :--- | :--- |
| **🚀 [Getting Started](https://github.com/proxikal/cerberus-mcp/wiki/Quick-Start)** | Installation, Configuration, and First Steps. |
| **🛠️ [MCP Tools](https://github.com/proxikal/cerberus-mcp/wiki/MCP-Tools-Reference)** | Reference for all 56 tools (Search, Analysis, Memory). |
| **🧠 [Memory System](https://github.com/proxikal/cerberus-mcp/wiki/Session-Memory)** | How the dual-layer preference and decision engine works. |
| **⚡ [Efficiency](https://github.com/proxikal/cerberus-mcp/wiki/Token-Efficiency)** | Real-world token savings breakdowns. |

---

## 🌐 Language Support

**Cerberus supports multiple programming languages** with varying feature coverage:

### ✅ **Universal Features** (All Languages)
These tools work across Python, TypeScript, JavaScript, Go, and other languages:
- **Core Navigation:** `search`, `get_symbol`, `context`, `blueprint`, `read_range`, `file_info`, `skeletonize`
- **Dependency Analysis:** `deps`, `call_graph`, `analyze_impact`, `test_coverage`
- **Project Tools:** `project_summary`, `smart_update`, `index_build`
- **Memory System:** All memory tools (`memory_learn`, `memory_search`, `memory_context`, etc.)

### 🔄 **Multi-Language Support**
- **`find_circular_deps`**: Python, TypeScript, JavaScript (detects import cycles)

### 🔄 **Enhanced Multi-Language Features**
- **`check_pattern`**: Python + TypeScript/JavaScript patterns (Python more mature)
- **`style_check`**: Python-optimized (basic TS/JS support)
- **`related_changes`**: Full TypeScript/JavaScript type support

### 📝 **Notes**
- **Parser:** Uses tree-sitter for multi-language AST parsing
- **Semantic Search:** Language-agnostic (works with all indexed code)
- **Import Resolution:** Supports Python imports, ES6 modules, CommonJS

---

## 🎯 When to Use Cerberus

**Good fits:**
- Large codebases (>1000 files) where manual navigation is slow
- Projects with complex dependency graphs
- Multi-session work where context needs to persist
- AI agent workflows with strict token budgets

**Not ideal for:**
- Small projects (<100 files) - setup overhead not worth it
- First-time exploration - initial indexing takes time
- Read-only analysis of unfamiliar code - index may not help much
- Projects with rapidly changing file structure - re-indexing frequent

---

## 🤝 Contributing

Contributions welcome! See [issues](https://github.com/proxikal/cerberus-mcp/issues) for current priorities.

**Known Issues:**
- Semantic search indexing is slow on large codebases (working on it)
- Memory system needs better conflict resolution
- Some tree-sitter parsers are incomplete for newer language features

**Development setup:**
```bash
git clone https://github.com/proxikal/cerberus-mcp.git
cd cerberus-mcp
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

**Built for AI agents. Optimized for efficiency. Experimental by nature.**
