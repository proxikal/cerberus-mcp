# Cerberus Session Hook

This hook auto-invokes the Cerberus skill at session start for optimal token efficiency (95%+ savings vs injecting instructions on every message).

## What It Does

1. **Detects context** - Project directory (code) vs general directory (brainstorming/notes)
2. **Finds skill** - Checks if Cerberus skill is installed in your AI agent's skills directory
3. **Auto-invokes** - Instructs the agent to invoke the Cerberus skill before any response
4. **Provides fallback** - If skill not installed, shows minimal guidance

## Installation

### 1. Copy the Hook

```bash
# Create hooks directory for your AI agent
mkdir -p ~/.claude/hooks  # or ~/.codex/hooks, ~/.aider/hooks, etc.

# Copy hook
cp hooks/session-start.sh ~/.claude/hooks/cerberus-startup.sh

# Make executable
chmod +x ~/.claude/hooks/cerberus-startup.sh
```

### 2. Configure Your AI Agent to Run Hooks

Different AI agents have different hook configurations. Here are examples:

#### Claude Code (CLI)

Add to your `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart:compact": "~/.claude/hooks/cerberus-startup.sh"
  }
}
```

**Hook types available:**
- `SessionStart` - Runs at session start (verbose output shown to user)
- `SessionStart:compact` - Runs at session start (compact output)
- `UserPromptSubmit` - Runs when user submits a message
- `ToolUse` - Runs when agent uses tools

**Tip:** Use `SessionStart:compact` for cleaner output.

#### Other AI Agents

Check your AI agent's documentation for hook configuration. Most modern AI agents support some form of session hooks or startup scripts.

**Common patterns:**
- Configuration file: `~/.agent-name/config.json` or `~/.agent-name/settings.json`
- Hooks directory: `~/.agent-name/hooks/` with auto-discovery
- Environment variable: `AGENT_STARTUP_HOOK=/path/to/hook.sh`

### 3. Restart Your AI Agent

The hook will run automatically on your next session.

## Expected Output

### With Skill Installed (Project Context)
```
IMPORTANT: Invoke Cerberus skill immediately using Skill tool (skill="Cerberus")
Context: Project directory detected - full Cerberus toolset available
```

### With Skill Installed (General Context)
```
IMPORTANT: Invoke Cerberus skill immediately using Skill tool (skill="Cerberus")
Context: General directory - memory tools available, index tools will gracefully skip
```

### Without Skill Installed (Project Context)
```
CERBERUS [project]: memory_context() recommended
TIP: Install Cerberus skill for 95% token savings - see repo skill/ directory
```

### Without Skill Installed (General Context)
```
CERBERUS [general]: Memory tools available
TIP: Install Cerberus skill for full guidance - see repo skill/ directory
```

## How It Works

The hook detects project directories by checking for:
- Version control: `.git`, `.svn`, `.hg`
- Language files: `go.mod`, `package.json`, `Cargo.toml`, `pyproject.toml`, etc.
- Cerberus index: `.cerberus/index.db` or `.cerberus/cerberus.db`

If any of these exist, it's considered a project directory with full tool access.

Otherwise, it's a general directory with memory-only access (no accidental indexing of brainstorming/notes).

## Benefits

- **95% token savings** - Hook + skill replaces per-message configuration injection
- **Context-aware** - Different behavior for code projects vs general directories
- **No accidental indexing** - Won't index your notes/brainstorming directories
- **Agent-agnostic** - Works with any AI agent supporting the skill template system
- **Auto-activation** - No manual skill invocation needed

## Troubleshooting

### Hook not running?

1. Check hook is executable: `ls -l ~/.claude/hooks/cerberus-startup.sh`
2. If not: `chmod +x ~/.claude/hooks/cerberus-startup.sh`
3. Verify configuration in `~/.claude/settings.json`
4. Restart your AI agent

### Skill not being invoked?

1. Verify skill is installed: `ls ~/.claude/skills/Cerberus/skill.md`
2. If not, see `skill/` directory in repo for installation
3. Check hook output - it should say "IMPORTANT: Invoke Cerberus skill..."

### Still using old CLAUDE.md?

If you have `~/.claude/CLAUDE.md` with Cerberus instructions, you can remove it:
```bash
rm ~/.claude/CLAUDE.md
# Or just empty it
echo "" > ~/.claude/CLAUDE.md
```

The hook + skill handle everything now with much better token efficiency.

## Customization

You can modify `session-start.sh` to:
- Add additional project markers (line 15-23)
- Change hook output messages (line 43-58)
- Add custom logic based on your workflow

Just remember to keep your customized version when updating Cerberus.
