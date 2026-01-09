# CERBERUS.md Cross-Agent Compatibility Report
Generated: 2026-01-08 23:08:26

## Summary
- Context file: CERBERUS.md
- Context size: 6798 bytes (~756 tokens)
- Agents tested: 3
- Success rate: 3/3

## Test Results

### CLAUDE - ✓ PASS

- **mission_understanding**: True

**Sample response:**
```
Based on the context, here's Cerberus in 5 words:

**Python AST symbolic analysis engine**

```

### GEMINI - ✓ PASS

- **understands_forbiddens**: True

**Sample response:**
```
Based on the provided identity and principles for Cerberus, the tool should **NOT**:

1.  **Perform LLM-based analysis:** It relies on deterministic tree-sitter AST parsing rather than using LLMs for 
```

### CODEX - ✓ PASS

- **understands_identity**: True

**Sample response:**
```
Cerberus is an autonomous context engine that deterministically turns code ASTs into symbol-aware context for AI agents. It indexes code by symbol boundaries using Tree-Sitter, keeps a git-native incr
```

## Recommendations

Based on compatibility test results:
- ✓ CERBERUS.md format is compatible with: claude, gemini, codex
- Consider this format production-ready for multi-agent workflows
