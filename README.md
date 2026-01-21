# Cerberus MCP

**Model Context Protocol server for AI-powered code exploration and persistent session memory**

[![Tests](https://github.com/proxikal/cerberus-mcp/actions/workflows/test-mcp.yml/badge.svg)](https://github.com/proxikal/cerberus-mcp/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Cerberus combines intelligent code exploration with persistent session memory, designed exclusively for AI agents to maximize efficiency and maintain context across sessions.

## What is Cerberus?

Cerberus provides AI agents with two powerful capabilities:

**🔍 Intelligent Code Exploration**
Navigate codebases through AST-based analysis with **90%+ token reduction** compared to reading full files. Find functions, analyze dependencies, trace call graphs, and understand architecture—all through structured, token-efficient queries.

**🧠 Persistent Session Memory**
Remember context across sessions with a **dual-layer memory system**: global preferences that apply everywhere, and project-specific decisions that persist per-codebase. No more re-explaining coding patterns every session.

**📊 Context-Aware Operation**
Cerberus adapts to your workspace—full toolset for code projects (with .git, go.mod, etc.), memory-only for general directories (brainstorming, notes). No accidental indexing of non-code content.

## Key Features

- **51 MCP tools** across 9 categories (search, structure, analysis, memory, quality)
- **70-95% token savings** vs traditional file reading approaches
- **Symbol search** - AST-based, 95% fewer false matches than text search
- **Skeletonization** - Get signatures without implementation (67% token savings)
- **Context assembly** - One call for symbol + inheritance + deps + imports
- **Advanced analysis** - Impact analysis, test coverage, branch comparison, circular dependency detection
- **Dual-layer memory** - Global preferences + project-specific decisions
- **Auto-learning** - Extract patterns from git history

## Quick Start

### 1. Install MCP Server

```bash
pip install git+https://github.com/proxikal/cerberus-mcp.git
```

### 2. Configure Your AI Agent

Add to your AI agent's MCP configuration (example for Claude Desktop):

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
mkdir -p ~/.claude/skills/Cerberus
cp -r skill/* ~/.claude/skills/Cerberus/
```

### 4. Install Session Hook (Recommended)

```bash
mkdir -p ~/.claude/hooks
cp hooks/session-start.sh ~/.claude/hooks/cerberus-startup.sh
chmod +x ~/.claude/hooks/cerberus-startup.sh
```

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart:compact": "~/.claude/hooks/cerberus-startup.sh"
  }
}
```

**For detailed installation instructions, see the [📚 Wiki](https://github.com/proxikal/cerberus-mcp/wiki/Installation)**

## Token Efficiency in Action

**Traditional approach** (finding and understanding a function):
```
grep → read full file → grep for usages → read more files
= 35,000 tokens, 5 commands, manual assembly
```

**Cerberus approach**:
```
search(query="authenticate", limit=3)
context(symbol_name="authenticate")
= 2,300 tokens, 2 commands, auto-assembled
```

**Savings: 93% (32,700 tokens)**

## Documentation

**📚 [Complete Documentation](https://github.com/proxikal/cerberus-mcp/wiki)**

- **[Installation](https://github.com/proxikal/cerberus-mcp/wiki/Installation)** - Detailed setup for all components
- **[Quick Start](https://github.com/proxikal/cerberus-mcp/wiki/Quick-Start)** - Get productive in 5 minutes
- **[MCP Tools Reference](https://github.com/proxikal/cerberus-mcp/wiki/MCP-Tools-Reference)** - All 51 tools explained
- **[Token Efficiency](https://github.com/proxikal/cerberus-mcp/wiki/Token-Efficiency)** - How Cerberus saves 70-95% tokens
- **[Session Memory](https://github.com/proxikal/cerberus-mcp/wiki/Session-Memory)** - Dual-layer memory system
- **[Context-Aware Operation](https://github.com/proxikal/cerberus-mcp/wiki/Context-Aware-Operation)** - Project vs general mode
- **[FAQ](https://github.com/proxikal/cerberus-mcp/wiki/FAQ)** - Common questions answered

## Supported Languages

- Python (.py)
- JavaScript/TypeScript (.js, .ts, .jsx, .tsx)
- Go (.go)
- Markdown (.md)

More languages coming soon.

## Example Usage

```python
# Load memory (session start)
memory_context()

# Explore codebase structure
blueprint(path="src/", format="tree")

# Find authentication code
search(query="authenticate", limit=5)

# Get complete context for a function
context(symbol_name="authenticate")
# Returns: code + base classes + callers + callees + imports

# Before refactoring
analyze_impact(symbol_name="processPayment")
test_coverage(symbol_name="processPayment")

# After editing
smart_update()  # Incremental index update (10x faster than full rebuild)

# Store architectural decision
memory_learn(
    category="decision",
    content="Uses JWT tokens, stored in HTTP-only cookies"
)
```

## Contributing

Contributions welcome! See [issues](https://github.com/proxikal/cerberus-mcp/issues) for current priorities.

**Development setup:**
```bash
git clone https://github.com/proxikal/cerberus-mcp.git
cd cerberus-mcp
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/proxikal/cerberus-mcp/issues)
- **Wiki**: [Complete Documentation](https://github.com/proxikal/cerberus-mcp/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/proxikal/cerberus-mcp/discussions)

---

**Built for AI agents. Optimized for efficiency. Designed for developers.**
