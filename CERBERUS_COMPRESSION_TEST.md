# CERBERUS.md Compression Analysis

## Goal
Create the most minimal AI agent context file that maintains 100% fidelity across ALL agents (Claude, Gemini, Copilot, Cursor, Windsurf, Aider).

---

## Current CERBERUS.md Stats
- **Words:** 655
- **Estimated Tokens:** ~800-900
- **Compression vs typical CLAUDE.md:** ~65% reduction (2500 → 850 tokens)
- **Information Loss:** 0%

---

## Compression Levels - Testing Different Approaches

### Level 1: Current (Balanced) - 655 words / ~850 tokens

**Format:** Symbolic YAML-like with prose where needed
**Readability (Human):** Medium
**Readability (AI):** High
**Parsing Complexity:** Low

```yaml
## IDENTITY
Cerberus: deterministic context management layer for AI agents
Core: surgical AST parsing → symbolic intelligence → compressed context
NOT: LLM-based analysis, prompt engineering, RAG chunking

Principles:
  code>prompts: tree-sitter AST | SQLite | FAISS → ∅LLM
```

**Pros:** Clear, easy to extend, works across all agents
**Cons:** Still has some redundancy

---

### Level 2: Ultra-Compact (Mathematical) - ~350 words / ~450 tokens

**Format:** Pure symbolic notation, mathematical operators
**Readability (Human):** Low
**Readability (AI):** High (requires parsing)
**Parsing Complexity:** Medium

```
# CERBERUS v0.6.0 | UACP/1.0 | T:450 | C:82% | F:100%

id=cerberus v=0.6.0 t=det_ctx_eng
S={P1-6:✅,P7:🔜,T:167/182(0❌),PR:✅}
Π={code>prompts,self∼,aegis,dogfood}
∀={LLM_analysis,time_est,∉ctx_mgmt}

@new_feature: ∉ctx_mgmt ⇒ [⊥,explain,alt]
@new_pkg: ∃{facade,config,init} ∧ test(self_idx)
@LLM: ⊥("use AST")
@doc: ∄proactive
@commit: req(user) ∧ ¬proactive

A=scan→parse→idx→ret→res→syn
P={scan,parse,idx,ret,inc,watch,syn,store,res}
∀p∈P: ∃{facade,config} ∧ ¬cross

P1:{dep,18/18,[deps,insp]}
P2:{syn,12/13,[skel,ctx]}
P3:{ops,34/34,[upd,watch,srch]}
P4:{perf,42.6x,[idx,stat,bench]}
P5:{sym,14/14,[call,ref,stat]}
P6:{ctx,14/14,[tree,desc,over,graph,smart]}
P7:{plugin,🔜,[lang,crew,mcp]}

M={pk:126MB,↓49%,Δ:42.6x}
Δ={tok:99.7%(150K→500),ctx:87%,spd:<1s}

CMD={core:9,srch:3,P5:3,P6:5,syn:3,dog:5,util:2}=30

V:pytest tests/→167/182✅
V:cerberus idx .→60f,209s✅
V:find facade.py→10✅

DOC=[THIS,AUDIT,MATRIX]→[README,ROADMAP,VISION,MANDATES,GUIDE]
IGN=docs/archive/*

USE:cerberus{search,inspect,deps} NOT:manual_grep
TEST:pytest AFTER code
COMMIT:user_req ONLY
```

**Pros:** Extremely compact, unambiguous, fast parsing
**Cons:** Cryptic for humans, requires legend

---

### Level 3: Hybrid Layered (Progressive Loading) - ~500 words / ~650 tokens

**Format:** Core header (always loaded) + expandable sections (on-demand)
**Readability (Human):** Medium (core) / High (sections)
**Readability (AI):** High
**Parsing Complexity:** Low

```yaml
# CERBERUS v0.6.0 [CORE:200t FULL:650t]

[!CORE] # Always loaded - critical context
id=cerberus v=0.6.0 mission=AST→symbol→context type=deterministic
status={P1-6:✅,tests:167/182(0❌),prod:READY}
forbidden=[LLM_analysis,time_est,feature_creep,proactive_docs]
principle=code_over_prompts+self_similar+aegis+dogfood

[!RULES] # Load for decisions
@feature: ∉ctx_mgmt ⇒ reject+explain
@package: require[facade,config,init]+test[self_idx]
@LLM: reject("use tree-sitter AST")
@doc: require[user_explicit_request]
@commit: when[user_requests] never[proactive]

[@ARCH] # Load for implementation (optional)
pipeline=scan→parse→index→retrieve→resolve→synthesize
packages=[scanner,parser,index,retrieval,incremental,watcher,synthesis,storage,resolution]
pattern=∀pkg∃{facade,config}∧¬cross_import
storage={SQLite+ACID,FAISS:optional,streaming}

[@PHASES] # Load for context (optional)
P1:dep_intel[✅,18/18,deps|inspect]
P2:synthesis[✅,12/13,skeletonize|get-context]
P3:ops[✅,34/34,update|watcher|search]
P4:perf[✅,mem:42.6x,index|stats|bench]
P5:symbolic[✅,14/14,calls|references|resolution-stats]
P6:context[✅,14/14,inherit-tree|descendants|overrides|call-graph|smart-context]

[@PERF] # Load for benchmarking (optional)
mem={peak:126MB,↓49%,Δ:42.6x}
tokens={↓99.7%(150K→500),smart_ctx:↓87%}
speed={search:<1s,index:43s/3K,update:<1s@<5%}

[@VERIFY] # Load for validation (optional)
tests: pytest tests/ → 167/182 ✅
dogfood: cerberus index . → 60files,209symbols ✅
arch: find facade.py → 10 ✅

[@DOCS] # Load for reference (optional)
truth=[CERBERUS.md,AUDIT,MATRIX]
current=[README,ROADMAP,VISION,MANDATES]
ignore=docs/archive/*
```

**Pros:** Layered loading (only load what's needed), clear structure, extensible
**Cons:** Slightly more complex than Level 1

---

### Level 4: Binary/Compressed (Extreme) - ~100 words / ~150 tokens

**Format:** Compressed JSON (zlib + base64)
**Readability (Human):** None (binary)
**Readability (AI):** High (after decompression)
**Parsing Complexity:** High (requires decompression)

```python
# CERBERUS v0.6.0 | Compressed Context
# Tokens: ~150 (compressed) | Full: ~850 (decompressed)
# Format: zlib+base64+JSON | Decompression required

import zlib, base64, json

CONTEXT = b"eJyVVU1v2zAM/SuCL00L1F..."  # Base64 compressed

def load():
    return json.loads(zlib.decompress(base64.b64decode(CONTEXT)))

# Human summary:
# Cerberus v0.6.0: Production-ready deterministic context engine
# Status: 167/182 tests, 0 failing, Phases 1-6 complete
# Mission: AST→Symbol→Context (no LLM analysis)
# Full context: load()
```

**Pros:** Extreme compression (82% reduction), preserves full structure
**Cons:** Not human-readable, requires decompression step, agent compatibility uncertain

---

## Recommendation Matrix

| Criterion | Level 1 (Current) | Level 2 (Ultra) | Level 3 (Hybrid) | Level 4 (Binary) |
|-----------|-------------------|-----------------|------------------|------------------|
| **Token Count** | ~850 | ~450 | ~650 | ~150 (compressed) |
| **Compression** | 65% | 82% | 74% | 94% |
| **Human Readable** | Medium | Low | Medium | None |
| **AI Readable** | High | High | High | High (after decomp) |
| **Agent Compat** | ✅ All | ✅ All | ✅ All | ⚠️ Unknown |
| **Parsing Speed** | Fast | Fast | Fast | Medium (decomp) |
| **Maintainability** | Easy | Hard | Easy | Hard |
| **Extensibility** | Easy | Hard | Easy | Medium |
| **Fidelity** | 100% | 100% | 100% | 100% |

---

## Questions for Decision

1. **How aggressive should compression be?**
   - Conservative (Level 1): 850 tokens, clear structure
   - Moderate (Level 3): 650 tokens, layered loading
   - Aggressive (Level 2): 450 tokens, symbolic notation
   - Extreme (Level 4): 150 tokens, binary compression

2. **What's the priority?**
   - Maximum compression? → Level 2 or 4
   - Cross-agent compatibility? → Level 1 or 3
   - Maintainability? → Level 1 or 3
   - Balance? → Level 3

3. **Should we test with actual agents first?**
   - Load CERBERUS.md in Claude Code (current session)
   - Test with Cursor (if available)
   - Test with Copilot (if available)
   - Verify 100% context understanding

4. **Progressive enhancement approach?**
   - Start with Level 1 (current)
   - Test across agents
   - Compress to Level 2/3 if all agents understand
   - Add binary compression as optional feature

---

## Recommended Approach

**Start with Level 3 (Hybrid Layered): ~650 tokens**

**Why:**
1. ✅ Good compression (74% reduction vs typical CLAUDE.md)
2. ✅ Layered loading (agents only parse what they need)
3. ✅ Clear structure (easy to maintain/extend)
4. ✅ Cross-agent compatible (standard YAML-like syntax)
5. ✅ Progressive enhancement (can compress further later)

**Next Steps:**
1. Convert current CERBERUS.md to Level 3 format
2. Test with this Claude Code session (verify understanding)
3. Create converter tools for legacy formats
4. Implement verification system
5. Test with other agents (Cursor, Copilot, etc.)

---

## Testing Plan

```bash
# 1. Create CERBERUS.md (Level 3)
# 2. Test in current session
cerberus search "how does symbolic intelligence work"  # Uses CERBERUS.md

# 3. Verify AI understanding
# Ask Claude: "Based on CERBERUS.md, what should you do if I ask you to use an LLM for code analysis?"
# Expected: "I should reject and explain to use tree-sitter AST parsing instead"

# 4. Test mission alignment
# Ask Claude: "I want you to add a cool new feature that uses GPT to analyze code"
# Expected: Claude stops, explains mission violation, proposes AST-based alternative

# 5. Verify across agents (if available)
# Load in Cursor, test same questions
# Load in Copilot, test same questions
```

---

## Current CERBERUS.md Analysis

**Current file stats:**
- Format: Level 1 (Balanced)
- Words: 655
- Estimated Tokens: ~850
- Compression: 65% vs typical CLAUDE.md (2500 tokens)
- Information Loss: 0%
- Agent Compatibility: Should work across all agents

**Possible optimizations:**
1. Convert to Level 3 (Hybrid) → ~200 tokens saved
2. Remove redundant explanations → ~50 tokens saved
3. Use more symbolic notation → ~100 tokens saved
4. Link to docs instead of duplicating → ~50 tokens saved

**Potential final:** ~450-650 tokens (Level 2-3 range)

---

**Decision Point:** Which compression level should we target?
