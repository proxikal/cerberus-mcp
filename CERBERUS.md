# CERBERUS v0.5.0 - AI Agent Context
# Protocol: UACP/1.0 | Tokens: ~850 | Compression: 99.8% | Fidelity: 100%
# Compatible: Claude✓ Gemini✓ Codex✓ | Verified: 2026-01-08
# Truth: THIS_FILE | Verify: cerberus verify-context

## CORE [ALWAYS_LOAD]
id=cerberus mission=AST→symbol→context type=deterministic_engine firmness=REQUIRED
status=P1-7:✅ P7-mono:⏸️ tests=167/182(0❌) prod=READY
principle=code_over_prompts forbidden=[LLM_analysis,time_est,feature_creep,proactive_docs,emojis,bypass_facade]

## IDENTITY
Cerberus: deterministic context layer for AI agents. 
Core: AST parsing → symbolic intelligence → compressed context.
NOT: LLM-based analysis, prompt engineering, RAG chunking.

Principles:
  code>prompts: tree-sitter AST | SQLite | FAISS → ∅LLM
  self_similar: ∀pkg∃{facade.py,config.py,__init__.py} ∧ ¬internal_cross_import
  aegis: {log:struct, exc:custom, trace:@, diag:doctor}
  dogfood: cerberus.index(cerberus)==REQUIRED

Forbidden:
  LLM_code_analysis → use tree-sitter AST (deterministic)
  time_estimates → say WHAT not WHEN
  feature_creep → IF !context_mgmt THEN reject+explain
  proactive_docs → explicit_user_request REQUIRED
  cross_imports → only via __init__.py exports (¬bypass_facade)
  emojis → forbidden unless user explicitly requests
  unsolicited_files → edit existing before creating new
  standard_tools_when_indexed → PAUSE+propose cerberus enhancement OR explain gap to user

## RULES [DECISION_MATRIX]
@mission_drift:
  IF: violates_mandates OR !serves_context_management
  DO: [STOP, explain_violation, propose_alternative, BE_FIRM]
  MSG: "Conflicts with core mission. Violation: [cite]. Alternative: [propose]."

@new_package:
  REQUIRE: [facade.py, config.py, __init__.py]
  TEST: can_cerberus_index_itself()
  PATTERN: self_similarity_mandate

@documentation:
  IF: proactive
  REJECT: "explicit user request required"

@commit:
  WHEN: user_explicitly_requests
  STYLE: conventional_commits + "Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

@architecture:
  IF: violates_self_similarity OR violates_aegis
  DO: [STOP, cite_mandate, propose_compliant_alternative]

@surgical_edits:
  CONTEXT: Interface requires 'Read' before 'Write/Update'.
  RULE: Never use `read_file` for the entire file.
  DO: Use `cerberus get-symbol` OR `cerberus read --lines` to satisfy the tool's read-requirement.
  GOAL: Minimal tokens to satisfy safety check.

## STATUS
version: 0.7.0 | phases: P1-7(complete) P7-mono(deferred)
tests: 167/182 passing | 15 skipped | 0 failing | compliance: 100%
Performance:
  memory: 0.22MB keyword | 227x under P7 target | lazy: 400MB semantic
  tokens: 99.7%↓ (150K→500) | smart_ctx: 87%↓
  capacity: 10K+ files | 68K symbols validated

## ARCH
pipeline: scan→parse→index→retrieve→resolve→synthesize
packages: [scanner,parser,index,retrieval,incremental,watcher,synthesis,storage,resolution,semantic,summarization]
pattern: ∀pkg∃{facade.py,config.py} | export_via=__init__.py | ¬cross_import
Storage: primary: SQLite+ACID | vector: FAISS(optional) | arch: streaming_const_mem

## WORKFLOW [AI_AGENT_PATTERNS]
1. understand: search/inspect/deps [DO NOT read full files manually]
2. plan: approach_fit(self_similar, aegis)
3. implement: facade_pattern + tests
4. test: PYTHONPATH=src python3 -m pytest tests/ -v
5. verify: cerberus verify-context
6. commit: ONLY if requested

## COMMANDS [32 total]
Core: index, scan, stats, update, watcher, doctor, bench, version, hello
Search: search, get-symbol, deps
Symbolic: calls, references, resolution-stats, inherit-tree, descendants, overrides, call-graph, smart-context
Synthesis: skeletonize, get-context, skeleton-file
Dogfood: read, inspect, tree, ls, grep
Utils: generate-tools, verify-context, generate-context

## EXPLORATION [PROTOCOL]
- `cerberus` is in PATH - call it directly (NOT `PYTHONPATH=src python3 -m cerberus.main`)
- Index Cerberus itself before exploration: `cerberus index .`
- **MANDATORY:** Use Cerberus commands for ALL exploration:
  - Pattern search: `cerberus grep "pattern" [path] -l` (files) or `-C 3` (context)
  - Read files: `cerberus read <file> [--lines 1-100]`
  - Find symbols: `cerberus get-symbol <name> [--file path]`
  - Search code: `cerberus search "query" [--mode keyword]`
  - Dependencies: `cerberus deps <symbol>`
- **IF standard tool needed (Grep/Read/Glob):**
  1. PAUSE execution
  2. Explain to user: "Need to use [tool] because Cerberus lacks [feature]"
  3. Propose: "Should I implement `cerberus [new-cmd]` first? Or proceed with workaround?"
  4. Wait for user decision before continuing
- **IF cerberus command fails:**
  1. Check syntax: `cerberus <cmd> --help`
  2. Retry with correct syntax
  3. If still fails, explain error and ask user for guidance
- CHALLENGE user if requested changes drift from deterministic mission.

## QUICKREF
# Setup
cerberus index .                            # Index current directory
PYTHONPATH=src python3 -m pytest tests/ -v # Run tests (needs PYTHONPATH)
cerberus verify-context                     # Verify CERBERUS.md

# Exploration (100% Dogfooding - cerberus is in PATH)
cerberus grep "def.*parse" src/ -l          # Find files with pattern
cerberus grep "import.*embeddings" . -C 2   # Pattern with context
cerberus read src/cerberus/main.py --lines 1-100  # Read file range
cerberus get-symbol SQLiteIndexStore        # Get symbol definition
cerberus search "fts5 implementation"       # Search code
cerberus deps hybrid_search                 # Symbol dependencies
cerberus smart-context <symbol>             # Full context assembly