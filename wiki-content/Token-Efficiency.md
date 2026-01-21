# Token Efficiency

Why Cerberus saves 70-95% tokens compared to traditional approaches.

## The Token Problem

AI agents pay for every token in:
1. **Input** - Your instructions, code context, previous messages
2. **Output** - The agent's responses

Traditional approaches waste massive amounts of tokens on:
- Reading entire files when you need one function
- Re-explaining preferences every session
- Text searching when you need structured code
- Manual context assembly from multiple sources

---

## How Cerberus Saves Tokens

### 1. Skeletonization (67-90% savings)

**Traditional:**
```python
# Reading full file (500 lines, 10,000 tokens)
Read tool: src/auth/service.py
```

**Cerberus:**
```python
# Skeletonize (signatures only, 1,500 tokens)
skeletonize(path="src/auth/service.py")

# Returns:
class AuthService:
    def __init__(self, db): ...
    def authenticate(self, username: str, password: str) -> Optional[User]: ...
    def create_session(self, user: User) -> Session: ...
    # ... etc
```

**Savings:** 85% (8,500 tokens saved)

### 2. Context Assembly (70-90% savings)

**Traditional workflow:**
```
1. search for "authenticate"                      → 500 tokens
2. Read entire file                               → 10,000 tokens
3. Search for callers                             → 800 tokens
4. Read caller files                              → 15,000 tokens
5. Read model definitions                         → 5,000 tokens
6. Manually piece it together                     → cognitive overhead
Total: ~31,300 tokens
```

**Cerberus workflow:**
```
1. search(query="authenticate", limit=5)          → 500 tokens
2. context(symbol_name="authenticate")            → 1,500 tokens
Total: 2,000 tokens

Returns:
- Function source code
- Skeletonized base classes
- All callers
- All callees
- Related imports
```

**Savings:** 94% (29,300 tokens saved)

### 3. Session Memory (95% savings)

**Traditional (per-message injection):**
```
Every message includes:
- "This project uses JWT for auth..."             → 200 tokens
- "Prefer async/await over callbacks..."          → 150 tokens
- "Use Factory pattern for handlers..."           → 180 tokens
- etc...

Over 20 messages: 530 × 20 = 10,600 tokens
```

**Cerberus (one-time load):**
```
Session start:
memory_context()                                  → 500 tokens (one time)

Total over 20 messages: 500 tokens
```

**Savings:** 95% (10,100 tokens saved)

### 4. Symbol Search vs Text Search (95% fewer false matches)

**Traditional (grep/text search):**
```
grep -r "authenticate" .

Results:
- "authenticate" in comments                      ❌ False match
- "authenticate_user"                             ✓ Partial match
- "authentication_required"                       ✓ Partial match
- "is_authenticated"                              ✓ Partial match
- "# TODO: authenticate this request"             ❌ False match
- String: "Please authenticate"                   ❌ False match

95% false positive rate common
Agent must read context to filter
```

**Cerberus (AST-based symbol search):**
```
search(query="authenticate", limit=5)

Results:
- authenticate (function) - src/auth/service.py:45    ✓ Exact symbol
- authenticate_user (function) - src/auth/handlers.py ✓ Related symbol
- AuthenticateRequest (class) - src/auth/models.py    ✓ Related type

0% false positives - all results are actual code symbols
No reading required to filter
```

**Savings:** 95% fewer false matches, 80% less context reading

### 5. Blueprint vs File Listing (90% savings)

**Traditional (ls + manual inspection):**
```
ls -la src/
# Lists files, no structure
# Must read each file to understand contents
# No symbol information

Then:
cat src/auth/service.py  # 10,000 tokens
cat src/auth/models.py   # 8,000 tokens
cat src/auth/handlers.py # 6,000 tokens

Total: 24,000+ tokens just to understand 3 files
```

**Cerberus (blueprint):**
```
blueprint(path="src/auth/", format="tree")

Returns:
src/auth/
├── service.py (AuthService, authenticate, create_session, logout)
├── models.py (User, Session, Token, AuthToken)
└── handlers.py (login_handler, logout_handler, refresh_token_handler)

Total: ~350 tokens
```

**Savings:** 98.5% (23,650 tokens saved)

---

## Real-World Examples

### Example 1: Understanding a Function

**Task:** Understand how `processPayment` works

**Traditional:**
```
1. grep -r "processPayment" .                     → Find it
2. cat src/payments/service.py                    → 15,000 tokens (500 lines)
3. grep -r "PaymentService" .                     → Find usages
4. cat src/api/handlers.py                        → 12,000 tokens
5. cat src/models/payment.py                      → 8,000 tokens
Total: 35,000+ tokens
```

**Cerberus:**
```
1. search(query="processPayment", limit=3)        → 500 tokens
2. context(symbol_name="processPayment")          → 1,800 tokens
Total: 2,300 tokens
```

**Savings:** 93% (32,700 tokens saved)

### Example 2: Code Review

**Task:** Review 10 changed functions in a PR

**Traditional:**
```
For each function:
- Read full file                                  → 10,000 tokens
- Read test file                                  → 8,000 tokens
- Read related files                              → 15,000 tokens

10 functions × 33,000 tokens = 330,000 tokens
```

**Cerberus:**
```
1. diff_branches(branch_a="main", branch_b="feature/X")  → 2,000 tokens
2. For each changed symbol:
   - context(symbol_name="...")                   → 1,500 tokens
   - test_coverage(symbol_name="...")             → 800 tokens

10 functions × 2,300 tokens = 23,000 + 2,000 = 25,000 tokens
```

**Savings:** 92% (305,000 tokens saved)

### Example 3: New Codebase Exploration

**Task:** Understand a new 50,000 line codebase

**Traditional:**
```
1. Read README                                    → 2,000 tokens
2. ls -la structure exploration                   → 500 tokens
3. Read 10 key files to understand                → 100,000 tokens
4. grep for patterns                              → 5,000 tokens
5. Piece together understanding                   → manual work
Total: 107,500+ tokens
```

**Cerberus:**
```
1. project_summary()                              → 2,500 tokens
2. blueprint(path=".", format="tree")             → 800 tokens
3. search for 5 key concepts                      → 2,500 tokens
4. context on 3 entry points                      → 4,500 tokens
Total: 10,300 tokens
```

**Savings:** 90% (97,200 tokens saved)

---

## Cumulative Savings

### Over a Typical Development Session

**Scenario:** 4-hour coding session with Cerberus

Actions:
- 5 function lookups
- 3 refactoring impact analyses
- 2 architecture explorations
- 1 code review
- Memory loaded once

**Traditional approach:**
```
5 function lookups × 35,000              = 175,000 tokens
3 impact analyses × 50,000               = 150,000 tokens
2 architecture explorations × 100,000    = 200,000 tokens
1 code review × 300,000                  = 300,000 tokens
Memory injected 40 messages × 500        =  20,000 tokens
Total: 845,000 tokens
```

**Cerberus approach:**
```
5 function lookups × 2,300               =  11,500 tokens
3 impact analyses × 3,000                =   9,000 tokens
2 architecture explorations × 10,000     =  20,000 tokens
1 code review × 25,000                   =  25,000 tokens
Memory loaded once                       =     500 tokens
Total: 66,000 tokens
```

**Savings:** 92% (779,000 tokens saved)

**Cost impact (at $3/million input tokens):**
- Traditional: $2.54
- Cerberus: $0.20
- **You save: $2.34 per 4-hour session**

---

## How We Achieve This

### 1. AST-Based Parsing

Traditional tools work with text. Cerberus works with **Abstract Syntax Trees**:

```
Text search: "authenticate"
→ Matches: code, comments, strings, variable names
→ Must read context to filter

AST search: symbol named "authenticate"
→ Matches: Only actual function/class definitions
→ Already filtered, structured data
```

### 2. Skeletonization

Remove implementation, keep structure:

```python
# Full function (200 tokens)
def authenticate(username: str, password: str) -> Optional[User]:
    """Authenticate user credentials."""
    user = db.query(User).filter_by(username=username).first()
    if not user:
        logger.warning(f"Authentication failed: user {username} not found")
        return None
    if not user.verify_password(password):
        logger.warning(f"Authentication failed: invalid password for {username}")
        return None
    logger.info(f"User {username} authenticated successfully")
    return user

# Skeletonized (30 tokens)
def authenticate(username: str, password: str) -> Optional[User]:
    """Authenticate user credentials."""
    ...
```

**You still know:**
- Function name
- Parameters and types
- Return type
- Purpose (docstring)

**You don't get:**
- Implementation details (unless needed)

### 3. Smart Indexing

Build once, query many times:

```
First time (one-time cost):
index_build(path=".")                    → 30 seconds, builds database

After that:
search(query="...", limit=5)             → 50ms, queries database
```

No re-scanning files for every search.

### 4. Incremental Updates

After editing code:

```
Traditional: Re-read entire codebase     → 30 seconds, 100,000+ tokens

Cerberus:
smart_update()                            → 3 seconds, only changed files
                                         → 10x faster, 95% fewer tokens
```

### 5. Dual-Layer Memory

Store once, use everywhere:

```
Global preferences (once):
memory_learn(category="preference", content="Prefer async/await")

Used in:
- Project A
- Project B
- Project C
- ... etc

No re-explanation needed per project
```

---

## Tips for Maximum Efficiency

1. **Always use `context()` over manual assembly**
   - One call vs 4-5 separate calls
   - 70-90% savings

2. **Start with `memory_context()`**
   - Loads preferences once per session
   - 95% savings vs per-message injection

3. **Use `skeletonize` before reading full files**
   - See structure first
   - Read full code only when needed
   - 67% savings

4. **Keep search limits low**
   - `limit=5` often enough
   - Each result costs ~100 tokens

5. **Use `smart_update` not `index_build`**
   - 10x faster after edits
   - Only processes changed files

6. **Prefer `blueprint` over `Glob` + `Read`**
   - One call vs many
   - Structured output
   - 90%+ savings

7. **Use `project_summary` for new codebases**
   - 80/20 overview
   - 2,500 tokens vs 100,000+ exploration

---

## Monitoring Your Savings

Use metrics to track efficiency:

```
metrics_report(period="session", detailed=true)
```

Shows:
- Tools used
- Token estimates
- Efficiency patterns
- Suggestions for improvement

---

## Next Steps

- **[MCP Tools Reference](MCP-Tools-Reference)** - Learn all 51 tools
- **[Quick Start](Quick-Start)** - Start saving tokens today
- **[Agent Skill Guide](Agent-Skill-Guide)** - Auto-enforce efficiency
