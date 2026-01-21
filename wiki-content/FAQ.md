# Frequently Asked Questions

Quick answers to common questions about Cerberus.

## General

### What is Cerberus?

Cerberus is an MCP (Model Context Protocol) server that provides AI agents with code exploration tools and persistent session memory. It saves 70-95% tokens compared to traditional approaches.

### Who is Cerberus for?

Cerberus is designed exclusively for AI agents (Claude, Codex, Aider, etc.), not for human developers directly. It provides tools that AI agents use to explore code more efficiently.

### What languages does Cerberus support?

- Python (.py)
- JavaScript/TypeScript (.js, .ts, .jsx, .tsx)
- Go (.go)
- Markdown (.md)

More languages coming soon.

### Is Cerberus free?

Yes, Cerberus is open source under the MIT license. Free to use, modify, and distribute.

---

## Installation & Setup

### Do I need all 4 components?

**Minimum (required):**
- MCP server
- AI agent configuration

**Highly recommended:**
- Agent skill (95% token savings)
- Session hook (auto-invokes skill)

### How long does installation take?

5-10 minutes for complete setup including all components.

### Can I use Cerberus with multiple AI agents?

Yes! Cerberus works with any AI agent that supports MCP servers and the skill template system. Install the skill in each agent's directory.

### Where is data stored?

**Global memory:** `~/.cerberus/memory/`
**Project memory:** `.cerberus/memory/` (in each project)
**Index:** `.cerberus/cerberus.db` (in each project)

### Can I backup my data?

Yes:
```
memory_export(output_path="/backup/cerberus-memory.json")
```

Restore with:
```
memory_import(input_path="/backup/cerberus-memory.json")
```

---

## Usage

### Do I need to build an index for every project?

Yes, but only once per project:
```
index_build(path=".")  # One-time, 5-30 seconds
```

After that, use `smart_update()` for incremental updates (10x faster).

### What if I forget to update the index after editing code?

Search results will be stale until you run:
```
smart_update()  # Incremental, very fast
```

Enable auto-update:
```
index_auto_update(enabled=true)
```

### How do I know if I'm in project or general context?

```
health_check()
```

Look at the `context` field:
- `"project"` - Full toolset available
- `"general"` - Memory-only mode

### Can I use Cerberus for brainstorming?

Yes! In general context (non-code directories), memory tools work perfectly for storing ideas while avoiding accidental indexing.

### How much does Cerberus cost to run?

Cerberus is free and runs locally. The only cost is your AI agent's token usage, which Cerberus reduces by 70-95%.

---

## Memory

### What's the difference between preferences and decisions?

**Preferences** (global):
- Coding style choices
- Tool preferences
- General patterns
- Apply to ALL projects

**Decisions** (project-specific):
- Architecture choices
- Tech stack details
- Project conventions
- Apply ONLY to current project

### How long is memory stored?

Permanently, until you explicitly delete it with `memory_forget()`.

### Can I share memory between team members?

Yes:
```
# Export
memory_export(output_path="team-memory.json")

# Team member imports
memory_import(input_path="team-memory.json", merge=true)
```

### Does memory work in general context?

Yes! Memory works everywhere (project and general contexts).

---

## Performance

### How long does indexing take?

Depends on project size:
- Small (1,000 files): 5-10 seconds
- Medium (10,000 files): 20-40 seconds
- Large (100,000 files): 2-5 minutes

### How long do searches take?

Instant (<100ms) after indexing.

### Does Cerberus slow down my AI agent?

No - it speeds it up by reducing tokens sent/received.

### Can I index very large codebases?

Yes, Cerberus handles codebases with 100,000+ files. Indexing is one-time, searches are instant.

---

## Token Efficiency

### How much do I actually save?

Real examples from users:
- Function lookup: 85% savings
- Code review: 92% savings
- Codebase exploration: 90% savings
- Session memory: 95% savings

### Do I save tokens if I only use a few tools?

Yes, even using just `search` + `context` saves 70-90% vs traditional read-everything approach.

### Does the skill add token overhead?

The skill loads once (~2,500 tokens one-time). Over a session with 20 messages, it replaces ~10,600 tokens of per-message instructions. Net savings: 76%.

---

## Tools

### What's the most important tool?

`context()` - Gets symbol code + inheritance + dependencies + imports in ONE call. Saves 70-90% tokens vs manual workflow.

### When should I use `skeletonize` vs `Read`?

**Use `skeletonize`:**
- Want to see structure/API without implementation
- Exploring unfamiliar code
- Need overview of large files

**Use `Read` (native):**
- Need full implementation details
- Reading configuration files
- Non-code files

### What's the difference between `search` and `Grep`?

**`search` (Cerberus):**
- Finds files, symbols, markdown headings
- `search("README")` → finds README.md
- `search("auth")` → finds auth functions/classes
- 95% fewer false matches
- Returns structured data (type, name, file, line)

**`Grep` (native):**
- Text pattern matching only
- Matches in code, comments, strings
- Must filter manually
- Use for: literal strings in code bodies, comments, SQL

### Should I use `index_build` or `smart_update`?

**`index_build`:**
- First time in project
- After index corruption
- Full rebuild

**`smart_update`:**
- After editing code
- 10x faster (git-aware)
- Incremental updates only

---

## Troubleshooting

### MCP server not found

```bash
# Check installation
pip list | grep cerberus

# Reinstall
pip install --force-reinstall git+https://github.com/proxikal/cerberus-mcp.git
```

### Hook not running

```bash
# Make executable
chmod +x ~/.claude/hooks/cerberus-startup.sh

# Verify configuration in ~/.claude/settings.json
```

### Skill not auto-invoking

```bash
# Verify skill installed
ls ~/.claude/skills/Cerberus/skill.md

# Reinstall
cp -r skill/* ~/.claude/skills/Cerberus/
```

### Search returns no results

**Search finds:** filenames, code symbols, markdown headings
**Search doesn't find:** text inside code bodies, comments, strings (use Grep)

```bash
# Check index exists
ls .cerberus/cerberus.db

# Rebuild index (includes .md files by default)
index_build(path=".")
```

### Tools fail with "not in project context"

```bash
# Check context
health_check()

# If general context, either:
# 1. Navigate to project
cd ~/projects/myapp

# 2. Initialize as project
git init
```

---

## Advanced

### Can I customize which files are indexed?

Yes, via `index_build` parameters:
```
index_build(path="src/", extensions=[".py", ".js"])
```

### Can I exclude directories from indexing?

Currently, Cerberus respects `.gitignore`. Custom exclusion coming soon.

### Can I run Cerberus on a remote server?

The MCP server runs wherever your AI agent runs. If your agent supports remote MCP servers, yes.

### Does Cerberus work with monorepos?

Yes. Index at the root, search works across all subprojects.

### Can I use Cerberus for non-code projects?

Yes, in general context for memory-only usage (brainstorming, notes, etc.).

---

## Contributing

### How can I contribute?

- Report bugs: [GitHub Issues](https://github.com/proxikal/cerberus-mcp/issues)
- Request features: [GitHub Issues](https://github.com/proxikal/cerberus-mcp/issues)
- Submit PRs: [Contributing Guide](Architecture)
- Improve docs: Edit this wiki

### What languages would you like supported next?

See current requests: [GitHub Issues](https://github.com/proxikal/cerberus-mcp/issues?q=is%3Aissue+label%3Alanguage-support)

Vote for your favorite or request a new one.

---

## More Help

- **[Installation](Installation)** - Setup guide
- **[Quick Start](Quick-Start)** - Get started in 5 minutes
- **[MCP Tools Reference](MCP-Tools-Reference)** - All 51 tools explained
- **[Troubleshooting](Troubleshooting)** - Detailed problem solving
- **[GitHub Issues](https://github.com/proxikal/cerberus-mcp/issues)** - Get help from community
