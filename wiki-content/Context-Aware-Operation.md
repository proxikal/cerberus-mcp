# Context-Aware Operation

How Cerberus adapts to project vs general directories.

## Overview

Cerberus automatically detects your workspace type and adapts its behavior:

- **Project Context** - Full toolset for code development
- **General Context** - Memory-only for brainstorming/notes

This prevents accidental indexing of non-code directories while keeping memory universally available.

---

## Project Context

### What Triggers It

Cerberus detects project context when it finds:

**Version Control:**
- `.git/` - Git repository
- `.svn/` - Subversion
- `.hg/` - Mercurial

**Language-Specific Files:**
- `go.mod` - Go project
- `package.json` - Node.js/JavaScript
- `Cargo.toml` - Rust
- `pyproject.toml` - Python (modern)
- `setup.py` - Python (legacy)
- `requirements.txt` - Python dependencies
- `pom.xml` - Java/Maven
- `build.gradle` - Java/Gradle
- `composer.json` - PHP
- `Gemfile` - Ruby
- `mix.exs` - Elixir
- `Makefile` - C/C++/various

**Cerberus Index:**
- `.cerberus/index.db` - Index exists
- `.cerberus/cerberus.db` - Index exists (alternative name)

**If ANY of these exist, you're in project context.**

### Available Tools

**Full Cerberus toolset (51 tools):**

✅ **Exploration:**
- `search` - Symbol search
- `blueprint` - Structure visualization
- `skeletonize` - Signature extraction
- `project_summary` - Codebase overview

✅ **Reading:**
- `context` - Complete symbol context
- `get_symbol` - Symbol retrieval
- `read_range` - Line ranges
- `deps` - Dependencies
- `call_graph` - Call relationships

✅ **Advanced Analysis:**
- `analyze_impact` - Impact analysis
- `test_coverage` - Test mapping
- `find_circular_deps` - Dependency cycles
- `diff_branches` - Branch comparison
- `check_pattern` - Convention validation
- `validate_architecture` - Rule enforcement
- `related_changes` - Change prediction

✅ **Memory:**
- All memory tools available

✅ **Quality:**
- `style_check` - Style validation
- `style_fix` - Auto-fixes

✅ **Index Management:**
- `index_build` - Build index
- `smart_update` - Incremental updates
- `index_status` - Index health

### Typical Workflow

```
1. cd ~/projects/my-app
2. Open AI agent session
3. health_check()
   → context: project
   → Full toolset available

4. index_build(path=".")              # One-time per project
5. search(query="authenticate")       # Find code
6. context(symbol_name="authenticate") # Understand it
7. [Make changes]
8. smart_update()                     # Update index
```

---

## General Context

### What Triggers It

General context activates when **NO project markers** exist in current or parent directories.

**Examples:**
- `~/Documents/notes/`
- `~/Desktop/brainstorming/`
- `~/tmp/concept-images/`
- `~/.config/` (unless it's a dotfiles repo)

### Available Tools

**Memory tools ONLY:**

✅ **Memory (All Tools Work):**
- `memory_context()` - Load global preferences
- `memory_learn()` - Store preferences (global only)
- `memory_show()` - View memory
- `memory_stats()` - Statistics
- `memory_forget()` - Remove entries
- `memory_export()` - Backup memory
- `memory_import()` - Restore memory

❌ **Index/Search Tools Skipped:**
- `search` - Gracefully skips (not available)
- `blueprint` - Gracefully skips
- `skeletonize` - Gracefully skips
- etc.

**Native AI agent tools still work:**
- Read - Read files normally
- Write - Write files normally
- Edit - Edit files normally
- Bash - Run commands normally

### Why This Matters

**Prevents accidental indexing:**
```
# You're brainstorming UI concepts
cd ~/Documents/concepts/
touch app-mockup.md
touch user-flow-diagram.md

# WITHOUT context-awareness:
index_build(path=".")
→ Would index your notes/images as "code"
→ Wasted resources
→ Polluted search results

# WITH context-awareness:
index_build(path=".")
→ Gracefully skips
→ "General context detected - index tools not available"
→ Memory still works for storing ideas
```

### Typical Workflow

```
1. cd ~/Documents/product-ideas/
2. Open AI agent session
3. health_check()
   → context: general
   → Memory tools available, index tools skipped

4. memory_context()                    # Load your preferences
5. [Brainstorm ideas]
6. Write tool: concepts.md             # Native tool
7. memory_learn(
     category="preference",
     content="When brainstorming, always consider mobile-first"
   )
```

---

## Detection Logic

### How Cerberus Decides

```python
def detect_context():
    current_dir = os.getcwd()

    # Check current directory and all parents up to home
    while current_dir != os.path.expanduser("~"):
        # Project markers
        if any([
            os.path.exists(os.path.join(current_dir, ".git")),
            os.path.exists(os.path.join(current_dir, "package.json")),
            os.path.exists(os.path.join(current_dir, "go.mod")),
            # ... other markers
        ]):
            return "project"

        current_dir = os.path.dirname(current_dir)

    return "general"
```

### Parent Directory Scanning

Cerberus checks **parent directories** up to your home folder:

```
Current: ~/projects/myapp/src/auth/
         ↓
Check:   ~/projects/myapp/src/auth/  (no markers)
         ~/projects/myapp/src/        (no markers)
         ~/projects/myapp/            (.git found!) ✓

Result: Project context
```

This means:
- You can be in any subdirectory of a project
- Cerberus finds the project root automatically
- All tools work correctly

---

## Switching Contexts

### Manual Navigation

```
# Project context
cd ~/projects/myapp
health_check()
→ context: project

# Switch to general context
cd ~/Documents/notes
health_check()
→ context: general
```

### In Same Session

If you change directories in the same session, Cerberus adapts:

```
Session 1:
cd ~/projects/myapp
search(query="auth")        → Works (project context)

cd ~/Documents/notes
search(query="auth")        → Skips gracefully (general context)
```

---

## Benefits

### 1. Resource Efficiency

**Without context-awareness:**
```
Every directory gets indexed
→ Brainstorming notes indexed as "code"
→ Concept images scanned
→ Temporary files indexed
→ Wasted CPU/disk/memory
```

**With context-awareness:**
```
Only actual code projects get indexed
→ Clean, relevant search results
→ Efficient resource usage
→ No pollution
```

### 2. Mental Model Clarity

**Project mode:**
- "I'm coding, give me code tools"
- Full analysis and exploration

**General mode:**
- "I'm brainstorming, give me memory"
- No distractions from unavailable tools

### 3. Safety

**Prevents:**
- Indexing sensitive documents
- Scanning binary files unnecessarily
- Polluting search with non-code results
- Accidental processing of large media files

---

## Hook Integration

The session hook detects context and notifies you:

### With Skill Installed

**Project context:**
```
IMPORTANT: Invoke Cerberus skill immediately using Skill tool (skill="Cerberus")
Context: Project directory detected - full Cerberus toolset available
```

**General context:**
```
IMPORTANT: Invoke Cerberus skill immediately using Skill tool (skill="Cerberus")
Context: General directory - memory tools available, index tools will gracefully skip
```

### Without Skill

**Project context:**
```
CERBERUS [project]: memory_context() recommended
TIP: Install Cerberus skill for 95% token savings
```

**General context:**
```
CERBERUS [general]: Memory tools available
TIP: Install Cerberus skill for full guidance
```

---

## Common Scenarios

### Scenario 1: Dotfiles Repository

```
cd ~/.config/nvim  # Has .git
→ Project context (it's a git repo)
→ Full tools available
```

### Scenario 2: Temporary Workspace

```
cd ~/tmp/quick-test
touch test.py
→ General context (no project markers)
→ Memory only

git init
→ Now project context!
→ Full tools available
```

### Scenario 3: Monorepo

```
cd ~/projects/monorepo
→ .git at root

cd ~/projects/monorepo/services/auth
→ Still project context (found .git in parent)

cd ~/projects/monorepo/docs/brainstorming
→ Still project context (found .git in parent)
→ If you want general context, work outside the repo
```

---

## Customization

### Add Custom Project Markers

Edit the session hook (`~/.claude/hooks/cerberus-startup.sh`):

```bash
is_code_project() {
    # Add your custom markers
    [ -f "mycompany.config" ] || \
    [ -d ".myproject" ] || \
    # ... existing markers
}
```

### Force General Context in Project

If you have a subdirectory in a project that should be treated as general:

```
cd ~/projects/myapp/sketches
touch .cerberus-ignore  # Custom marker

# Modify hook to check for this
```

---

## Best Practices

1. **Use general context for:**
   - Brainstorming product ideas
   - Writing documentation (non-code)
   - Organizing personal notes
   - Concept art / design mockups

2. **Use project context for:**
   - Active software development
   - Code review
   - Refactoring
   - Architecture exploration

3. **Check context when uncertain:**
   ```
   health_check()
   → Look at "context" field
   ```

4. **Memory works everywhere:**
   - Store ideas in general context
   - Store code patterns in project context
   - Both accessible later

---

## Troubleshooting

### "Why are index tools not available?"

Check context:
```
health_check()
→ context: general
```

You're in a non-project directory. Either:
1. Navigate to a project: `cd ~/projects/myapp`
2. Initialize as project: `git init`
3. Use memory tools only

### "False positive: Not a project but detected as one"

A project marker exists but this isn't a code project.

**Solutions:**
1. Remove the marker (if accidental)
2. Customize hook to exclude this directory
3. Work in a subdirectory without markers

### "False negative: Is a project but not detected"

No project markers found.

**Solutions:**
1. Add a marker: `git init` or create `package.json`
2. Add custom marker and update hook
3. Use `index_build()` anyway (will work but context still general)

---

## Next Steps

- **[Session Hooks](Session-Hooks)** - Customize context detection
- **[Session Memory](Session-Memory)** - Works in both contexts
- **[MCP Tools Reference](MCP-Tools-Reference)** - See which tools are context-aware
