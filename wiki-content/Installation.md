# Installation

Complete guide to installing Cerberus MCP with all components for the full experience.

## Overview

Cerberus has 4 components:

1. **MCP Server** (Required) - The core toolset
2. **Agent Skill** (Highly Recommended) - Token-efficient guidance
3. **Session Hook** (Recommended) - Auto-invokes skill
4. **AI Agent Configuration** (Required) - Connect agent to MCP

**Total install time:** 5-10 minutes

---

## 1. Install MCP Server

The MCP server provides the 51 tools for code exploration and memory.

```bash
pip install git+https://github.com/proxikal/cerberus-mcp.git
```

**Verify installation:**
```bash
cerberus-mcp --help
```

You should see the MCP server help output.

---

## 2. Configure Your AI Agent

Add Cerberus to your AI agent's MCP server configuration.

### Claude Desktop

**Location:**
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

**Add to config:**
```json
{
  "mcpServers": {
    "cerberus": {
      "command": "cerberus-mcp"
    }
  }
}
```

**Restart Claude Desktop** - The MCP server will start automatically.

### Claude Code (CLI)

Add to `~/.claude/mcp_settings.json` or configure via CLI:

```bash
claude mcp add cerberus cerberus-mcp
```

### Other AI Agents

Consult your AI agent's documentation for MCP server configuration. Most agents support a similar JSON configuration format.

**Common patterns:**
- Configuration file: `~/.agent/config.json` or `~/.agent/mcp_servers.json`
- CLI command: `agent mcp add cerberus cerberus-mcp`
- Environment variable: `MCP_SERVERS='{"cerberus": {"command": "cerberus-mcp"}}'`

---

## 3. Install Agent Skill (Highly Recommended)

The Cerberus skill provides token-efficient guidance on using the 51 MCP tools correctly.

**Benefits:**
- 95% token savings vs per-message instructions
- Context-aware operation (project vs general directories)
- Enforces best practices automatically
- Load-on-demand pattern files for efficiency

### Installation

```bash
# Create skill directory for your agent
mkdir -p ~/.claude/skills/Cerberus  # Adjust path for your agent

# Navigate to Cerberus repo
cd /path/to/cerberus-mcp

# Copy skill files
cp -r skill/* ~/.claude/skills/Cerberus/
```

**Verify installation:**
```bash
ls ~/.claude/skills/Cerberus/
# You should see: skill.md  patterns/
```

### Agent-Specific Paths

Different AI agents use different skill directories:

| Agent | Skill Directory |
|-------|----------------|
| Claude Code | `~/.claude/skills/Cerberus/` |
| Codex | `~/.codex/skills/Cerberus/` |
| Aider | `~/.aider/skills/Cerberus/` |
| Other | Check agent documentation |

---

## 4. Install Session Hook (Recommended)

The session hook auto-invokes the Cerberus skill at session start, eliminating manual invocation.

### Copy Hook

```bash
# Create hooks directory
mkdir -p ~/.claude/hooks  # Adjust for your agent

# Copy hook
cp hooks/session-start.sh ~/.claude/hooks/cerberus-startup.sh

# Make executable
chmod +x ~/.claude/hooks/cerberus-startup.sh
```

### Configure Hook Execution

Your AI agent needs to know to run the hook.

#### Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart:compact": "~/.claude/hooks/cerberus-startup.sh"
  }
}
```

**Available hook types:**
- `SessionStart` - Verbose output shown to user
- `SessionStart:compact` - Compact output (recommended)
- `UserPromptSubmit` - Runs when user submits message
- `ToolUse` - Runs when agent uses tools

#### Other Agents

Check your AI agent's documentation for hook configuration.

**Common patterns:**
- Configuration: Add to `~/.agent/config.json` or `~/.agent/settings.json`
- Auto-discovery: Place in `~/.agent/hooks/` directory
- Environment variable: `AGENT_STARTUP_HOOK=/path/to/hook.sh`

See **[Session Hooks](Session-Hooks)** for detailed configuration and customization.

---

## 5. Clean Up Old Configuration (Optional)

If you previously used a global configuration file (like `~/.claude/CLAUDE.md`) with Cerberus instructions, you can remove it:

```bash
# Remove old config (if it exists)
rm ~/.claude/CLAUDE.md

# Or just empty it
echo "" > ~/.claude/CLAUDE.md
```

The skill + hook handle everything now with **95% better token efficiency**.

---

## 6. Restart Your AI Agent

Restart your AI agent to activate all components:
- MCP server starts automatically
- Hook runs on session start
- Skill loads when invoked by hook

---

## Verification

### Test MCP Server

Start a new session and run:

```
health_check()
```

You should see:
```
status: healthy
context: project or general
index: available (if in project)
memory: available
```

### Test Skill Auto-Invocation

Start a new session. You should see the hook output:

```
IMPORTANT: Invoke Cerberus skill immediately using Skill tool (skill="Cerberus")
Context: Project directory detected - full Cerberus toolset available
```

The agent should automatically invoke the skill before responding.

### Test Memory

```
memory_context()
```

Should return memory status (may be empty on first run).

### Test Code Exploration (in a project directory)

```
blueprint(path=".", format="tree")
```

Should show a tree view of your project structure.

---

## Troubleshooting

### MCP Server Not Found

**Issue:** `cerberus-mcp: command not found`

**Solution:**
```bash
# Check installation
pip list | grep cerberus

# Reinstall if needed
pip install --force-reinstall git+https://github.com/proxikal/cerberus-mcp.git

# Check PATH includes pip's bin directory
echo $PATH
```

### Hook Not Running

**Issue:** Hook output not showing on session start

**Solutions:**
1. Verify hook is executable:
   ```bash
   ls -l ~/.claude/hooks/cerberus-startup.sh
   # Should show -rwxr-xr-x
   ```

2. Make executable if needed:
   ```bash
   chmod +x ~/.claude/hooks/cerberus-startup.sh
   ```

3. Check hook configuration in `~/.claude/settings.json`

4. Restart your AI agent

### Skill Not Being Invoked

**Issue:** Hook shows "Install Cerberus skill" message

**Solution:**
```bash
# Verify skill is installed
ls ~/.claude/skills/Cerberus/skill.md

# If not found, reinstall
cp -r skill/* ~/.claude/skills/Cerberus/
```

### Tools Return "Index not found"

**Issue:** Search/exploration tools fail in project directory

**Solution:**
```bash
# Build index (one-time per project)
index_build(path=".")

# Or use smart_update for faster incremental indexing
smart_update()
```

### Memory Not Persisting

**Issue:** `memory_context()` returns empty every session

**Solution:**
```bash
# Check memory storage exists
ls ~/.cerberus/memory/  # Global memory
ls .cerberus/memory/    # Project memory

# Try storing something
memory_learn(category="preference", content="Test preference")
memory_show()
```

---

## Next Steps

- **[Quick Start](Quick-Start)** - Your first session with Cerberus
- **[MCP Tools Reference](MCP-Tools-Reference)** - Explore all 51 tools
- **[Session Hooks](Session-Hooks)** - Customize hook behavior
- **[Troubleshooting](Troubleshooting)** - More detailed solutions

---

## Development Installation

For contributors working on Cerberus itself:

```bash
# Clone repository
git clone https://github.com/proxikal/cerberus-mcp.git
cd cerberus-mcp

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run specific test file
pytest tests/test_mcp/test_search.py -v
```

See **[Architecture](Architecture)** for contribution guidelines.
