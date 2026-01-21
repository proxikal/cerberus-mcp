# Welcome to Cerberus MCP

**Model Context Protocol server for AI-powered code exploration and persistent session memory**

Cerberus combines intelligent code exploration with persistent session memory, designed exclusively for AI agents to maximize efficiency and maintain context across sessions.

## 🚀 Quick Links

### Getting Started
- **[Installation](Installation)** - Complete setup guide for all components
- **[Quick Start](Quick-Start)** - Get up and running in 5 minutes
- **[Context-Aware Operation](Context-Aware-Operation)** - How Cerberus adapts to your workspace

### Core Features
- **[MCP Tools Reference](MCP-Tools-Reference)** - All 51 tools explained with examples
- **[Session Memory](Session-Memory)** - Dual-layer memory system deep dive
- **[Advanced Analysis](Advanced-Analysis)** - Impact analysis, test coverage, branch comparison
- **[Token Efficiency](Token-Efficiency)** - Why Cerberus saves 70-95% tokens

### Configuration
- **[Agent Skill Guide](Agent-Skill-Guide)** - Using and customizing the Cerberus skill
- **[Session Hooks](Session-Hooks)** - Auto-invocation and startup configuration

### Reference
- **[Architecture](Architecture)** - System design for contributors
- **[Troubleshooting](Troubleshooting)** - Common issues and solutions
- **[FAQ](FAQ)** - Frequently asked questions

## What is Cerberus?

Cerberus is an MCP (Model Context Protocol) server that provides AI agents with two powerful capabilities:

### 1. 🔍 Intelligent Code Exploration

Navigate codebases through AST-based analysis with **90%+ token reduction** compared to reading full files:

- **Symbol search** - Find functions, classes, methods across entire codebase
- **Skeletonization** - Get signatures without implementation (67% token savings)
- **Context assembly** - One call for symbol + inheritance + dependencies
- **Call graph analysis** - Understand caller/callee relationships
- **Blueprint generation** - ASCII tree views of architecture

### 2. 🧠 Persistent Session Memory

Remember context across sessions with a **dual-layer memory system**:

- **Global memory** (~/.cerberus/memory/) - Preferences and corrections across ALL projects
- **Project memory** (.cerberus/memory/) - Architectural decisions per-project
- **Auto-learning** - Extract patterns from git history
- **Export/import** - Backup and share memory

## Why Cerberus?

### Token Efficiency
Traditional approaches waste tokens by:
- Reading entire files when you need one function (10,000+ tokens)
- Re-explaining preferences every session (5,000+ tokens per session)
- Searching text when you need structured code (95% false matches)

Cerberus eliminates this waste:
- `skeletonize` → 67% token savings vs full file read
- `context()` → 70-90% savings vs manual workflow
- Session memory → 95% savings vs per-message instructions

**Real example:** Finding and understanding a function
- Traditional: `grep` → `read` entire file → parse mentally → 10,000 tokens
- Cerberus: `search` → `context()` → 1,500 tokens (85% savings)

### Context-Aware Operation

Cerberus adapts to your workspace:

**Project Context** (has .git, go.mod, etc.):
- Full toolset available (exploration + memory)
- Index-based symbol search
- Advanced analysis features

**General Context** (brainstorming, notes):
- Memory tools only
- No accidental indexing
- Perfect for concept work

See **[Context-Aware Operation](Context-Aware-Operation)** for details.

## Supported Languages

- Python (.py)
- JavaScript/TypeScript (.js, .ts, .jsx, .tsx)
- Go (.go)
- Markdown (.md)

More languages coming soon.

## Key Statistics

- **51 MCP tools** across 9 categories
- **90%+ token reduction** for code exploration
- **95%+ token savings** with skill + memory vs traditional approaches
- **10x faster** incremental updates vs full re-indexing
- **562/564 tests passing** (99.6% pass rate)

## Community

- **GitHub**: [proxikal/cerberus-mcp](https://github.com/proxikal/cerberus-mcp)
- **Issues**: [Report bugs or request features](https://github.com/proxikal/cerberus-mcp/issues)
- **License**: MIT

## Next Steps

1. **[Install Cerberus](Installation)** - Set up MCP server, skill, and hook
2. **[Quick Start](Quick-Start)** - Your first session with Cerberus
3. **[MCP Tools Reference](MCP-Tools-Reference)** - Explore all 51 tools

---

**Built for AI agents. Optimized for efficiency. Designed for developers.**
