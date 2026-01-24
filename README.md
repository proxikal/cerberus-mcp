# Cerberus MCP

<!-- BADGES: Verified Status -->
![Tests](https://github.com/proxikal/cerberus-mcp/actions/workflows/test-mcp.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white)
![Code Style](https://img.shields.io/badge/Code%20Style-Ruff-black?style=flat-square)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)

> **The Model Context Protocol server for intelligent code exploration and persistent session memory.**

Cerberus provides AI agents with AST-based navigation and a dual-layer memory system, eliminating the need to "re-read" the same files or "re-learn" the same project constraints every session.

---

## ⚡ Highlights

| Feature | Description |
| :--- | :--- |
| **🔍 Intelligent Search** | Navigate via AST (Abstract Syntax Trees). Finds functions and symbols with **95% fewer false positives** than text search. |
| **🧠 Persistent Memory** | A dual-layer system that remembers your **Global Preferences** (everywhere) and **Project Decisions** (context-specific). |
| **📉 90% Token Savings** | "Skeletonization" and "Context Assembly" retrieve only the necessary signatures and dependencies, preventing context window bloat. |

---

## 🛠️ Tech Stack

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastMCP](https://img.shields.io/badge/FastMCP-Enabled-000000?style=for-the-badge)
![TreeSitter](https://img.shields.io/badge/Tree--Sitter-Parser-green?style=for-the-badge)
![Pydantic](https://img.shields.io/badge/Pydantic-Validated-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Memory-003B57?style=for-the-badge&logo=sqlite&logoColor=white)

---

## 🚀 Quick Start

**Prerequisites:** Python 3.10+

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
# Deploys the specialized prompts that help the agent use Cerberus effectively
mkdir -p ~/.claude/skills/Cerberus
cp -r skill/* ~/.claude/skills/Cerberus/
```

---

## 🤖 Optional: Local LLM Summarization

Cerberus supports **zero-token file summarization** using local LLMs via [llm-toolchain](https://github.com/proxikal/llm-toolchain).

### Why llm-toolchain?

**Traditional approach** (summarizing a file):
```
1. Read entire file into context → 3,000 tokens
2. Send to LLM → 3,000 tokens
3. Get summary → 200 tokens
Total: ~3,200 tokens per file
```

**With llm-toolchain**:
```
1. Prompt: "Summarize src/auth.py" → 50 tokens
2. LLM reads file server-side → 0 tokens (tool layer handles it!)
3. Summary → 200 tokens
Total: ~250 tokens (92% savings!)
```

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
model = "deepseek-coder:6.7b"  # Or any Ollama model
ollama_url = "http://localhost:11434"
```

**How it works:**
- If `llm-toolchain` is installed → uses zero-token file operations
- If not installed → falls back to direct file reads (standard behavior)
- If Ollama unavailable → summarization gracefully disabled

---

## 📚 Documentation Portal

We maintain detailed documentation in our [Wiki](https://github.com/proxikal/cerberus-mcp/wiki).

| Section | Content |
| :--- | :--- |
| **🚀 [Getting Started](https://github.com/proxikal/cerberus-mcp/wiki/Quick-Start)** | Installation, Configuration, and First Steps. |
| **🛠️ [MCP Tools](https://github.com/proxikal/cerberus-mcp/wiki/MCP-Tools-Reference)** | Reference for all 51+ tools (Search, Analysis, Memory). |
| **🧠 [Memory System](https://github.com/proxikal/cerberus-mcp/wiki/Session-Memory)** | How the dual-layer preference and decision engine works. |
| **⚡ [Efficiency](https://github.com/proxikal/cerberus-mcp/wiki/Token-Efficiency)** | Deep dive into how we save 90% of tokens. |

---

## 📊 Token Efficiency in Action

**Traditional approach** (finding and understanding a function):
```
grep → read full file → grep for usages → read more files
= 35,000 tokens, 5 commands, manual assembly
```

**Cerberus approach**:
```python
search(query="authenticate", limit=3)
context(symbol_name="authenticate")
# = 2,300 tokens, 2 commands, auto-assembled
```

**Savings: ~93% (32,700 tokens)**

---

## 🤝 Contributing

Contributions welcome! See [issues](https://github.com/proxikal/cerberus-mcp/issues) for current priorities.

**Development setup:**
```bash
git clone https://github.com/proxikal/cerberus-mcp.git
cd cerberus-mcp
pip install -e ".[dev]"
pytest tests/ -v
```

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

**Built for AI agents. Optimized for efficiency. Designed for developers.**