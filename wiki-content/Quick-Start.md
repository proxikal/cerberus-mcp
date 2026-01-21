# Quick Start

Get productive with Cerberus in 5 minutes.

## Prerequisites

- Cerberus MCP server installed
- AI agent configured with Cerberus
- (Optional) Skill and hook installed

See **[Installation](Installation)** if you haven't set these up yet.

---

## Your First Session

### 1. Start in a Project Directory

```bash
cd ~/projects/my-project  # Any directory with code
```

### 2. Load Memory (If Skill Installed)

If you have the skill installed, it will auto-invoke and load memory. Otherwise:

```
memory_context()
```

**Output:**
```
Global preferences: 0
Project decisions: 0
(Empty on first run - memory builds over time)
```

### 3. Check Context

```
health_check()
```

**Output:**
```
status: healthy
context: project  (or "general" if not in a code project)
index: not_built
memory: available
recommendations: ["Run index_build() to enable search tools"]
```

### 4. Build Index (One-Time Per Project)

```
index_build(path=".")
```

**What this does:**
- Scans all code files in current directory
- Extracts functions, classes, methods (symbols)
- Stores in `.cerberus/cerberus.db`
- Takes 5-30 seconds depending on project size

**Output:**
```
Indexed 1,234 symbols across 87 files
Index stored at: .cerberus/cerberus.db
```

---

## Exploring Code

Now you can use the full toolset.

### Find a Function

```
search(query="authenticate", limit=5)
```

**Output:**
```
1. authenticate (function) - src/auth/service.py:45
2. authenticate_user (function) - src/auth/handlers.py:12
3. AuthenticateRequest (class) - src/auth/models.py:8
4. is_authenticated (function) - src/middleware/auth.py:67
5. authentication_required (decorator) - src/decorators.py:23
```

### Get Full Context for a Symbol

```
context(symbol_name="authenticate")
```

**What you get (in ONE call):**
- Full source code of the function
- Base classes (if it's a method)
- Functions that call it (callers)
- Functions it calls (callees)
- All imports it uses

**Token savings:** 70-90% vs reading full file + deps manually

### See Project Structure

```
blueprint(path="src/", format="tree")
```

**Output:**
```
src/
├── auth/
│   ├── service.py (AuthService, authenticate, logout)
│   ├── models.py (User, Session, AuthToken)
│   └── handlers.py (login_handler, logout_handler)
├── api/
│   ├── routes.py (register_routes, health_check)
│   └── middleware.py (cors_middleware, auth_middleware)
└── db/
    ├── connection.py (get_db, close_db)
    └── models.py (BaseModel, TimestampedModel)
```

### Get Just Function Signatures

```
skeletonize(path="src/auth/service.py")
```

**Output:**
```python
class AuthService:
    def __init__(self, db):
        ...

    def authenticate(self, username: str, password: str) -> Optional[User]:
        ...

    def create_session(self, user: User) -> Session:
        ...

    def logout(self, session_id: str) -> bool:
        ...
```

**Token savings:** 67% vs reading full file

---

## Using Memory

### Store a Decision

You just discovered this project uses JWT for auth:

```
memory_learn(
    category="decision",
    content="Uses JWT tokens for authentication, stored in HTTP-only cookies"
)
```

### Store a Preference

You prefer async/await over callbacks:

```
memory_learn(
    category="preference",
    content="Prefer async/await over callbacks for asynchronous code"
)
```

**Note:** Preferences are global (all projects), decisions are per-project.

### Store a Correction

You made a mistake assuming this uses sessions:

```
memory_learn(
    category="correction",
    content="This project uses stateless JWT auth, not server-side sessions"
)
```

### Recall Memory

Next session:

```
memory_context()
```

**Output:**
```
Global preferences:
- Prefer async/await over callbacks for asynchronous code

Project decisions (my-project):
- Uses JWT tokens for authentication, stored in HTTP-only cookies

Global corrections:
- This project uses stateless JWT auth, not server-side sessions
```

---

## Advanced Features

### Before Refactoring

```
# What breaks if I change this function?
analyze_impact(symbol_name="authenticate")

# What tests cover this?
test_coverage(symbol_name="authenticate")

# Get full context
context(symbol_name="authenticate")
```

### Compare Branches

```
# See what changed between main and feature branch
diff_branches(branch_a="main", branch_b="feature/new-auth")
```

**Output:**
- Added symbols
- Modified symbols
- Deleted symbols
- Symbol-level summary (not line-level)

### Find Circular Dependencies

```
find_circular_deps(path="src/")
```

**Output:**
```
Found 2 circular dependency chains:

1. auth/service.py → api/middleware.py → auth/service.py
2. db/models.py → auth/models.py → db/models.py
```

### After Editing Code

```
# What else might need updating?
related_changes(file_path="src/auth/service.py", symbol_name="authenticate")

# Update index incrementally (10x faster than full rebuild)
smart_update()
```

---

## Token Efficiency in Action

### Traditional Approach

**Task:** Find and understand the `authenticate` function

```
1. grep -r "def authenticate" .          (search)
2. cat src/auth/service.py               (read entire file - 500 lines)
3. grep -r "authenticate(" .              (find usages)
4. cat src/api/handlers.py               (read another file)
5. cat src/auth/models.py                (read model definitions)
```

**Total:** ~10,000 tokens, 5 commands, manual assembly

### Cerberus Approach

```
1. search(query="authenticate", limit=5)
2. context(symbol_name="authenticate")
```

**Total:** ~1,500 tokens, 2 commands, auto-assembled

**Savings:** 85% fewer tokens, 60% fewer commands

---

## Context-Aware Operation

Cerberus adapts to your workspace:

### Project Directory (has .git, go.mod, etc.)
```
health_check()
→ context: project
→ Full toolset available
```

### General Directory (brainstorming, notes)
```
health_check()
→ context: general
→ Memory tools only (no accidental indexing)
```

This prevents indexing your notes, brainstorming docs, or concept images.

See **[Context-Aware Operation](Context-Aware-Operation)** for details.

---

## Common Workflows

### Understanding New Codebase

```
1. project_summary()                    # 80/20 overview
2. blueprint(path=".", format="tree")   # See structure
3. search(query="main", limit=5)        # Find entry points
4. context(symbol_name="main")          # Deep dive
```

### Before Major Refactoring

```
1. analyze_impact(symbol_name="target_function")
2. test_coverage(symbol_name="target_function")
3. context(symbol_name="target_function")
4. [Make changes]
5. related_changes(file_path="modified_file.py")
6. smart_update()
```

### Code Review

```
1. diff_branches(branch_a="main", branch_b="feature/X")
2. For each changed symbol:
   - analyze_impact(symbol_name="changed_symbol")
   - test_coverage(symbol_name="changed_symbol")
3. check_pattern(pattern="error_handling", path="src/")
```

---

## Next Steps

- **[MCP Tools Reference](MCP-Tools-Reference)** - Explore all 51 tools in detail
- **[Session Memory](Session-Memory)** - Master the dual-layer memory system
- **[Advanced Analysis](Advanced-Analysis)** - Deep dive on Phase 4 features
- **[Token Efficiency](Token-Efficiency)** - Understand the savings

---

## Tips

1. **Always start with `memory_context()`** - Loads previous knowledge
2. **Use `context()` for symbols** - Don't read full files
3. **Use `smart_update()` after edits** - Don't rebuild index
4. **Store decisions as you discover them** - Build memory over time
5. **Use `project_summary()` for new codebases** - 80% less exploration
