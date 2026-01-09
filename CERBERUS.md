# CERBERUS v0.5.0 - AI Agent Context
# Protocol: UACP/1.0 | Tokens: ~850 | Compression: 99.8% | Fidelity: 100%
# Compatible: Claude✓ Gemini✓ Codex✓ | Verified: 2026-01-08
# Truth: THIS_FILE | Verify: cerberus verify-context

## CORE [ALWAYS_LOAD]
id=cerberus mission=AST→symbol→context type=deterministic_engine firmness=REQUIRED
status=P1-6:✅ P7:🔜 tests=167/182(0❌) prod=READY
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

## STATUS
version: 0.5.0 | phases: P1-6(complete) P7(planned)
tests: 167/182 passing | 15 skipped | 0 failing | compliance: 100%
Performance:
  memory: 126.5MB peak | Δ42.6x reduction | target: <50MB (P7)
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

## COMMANDS [40 total]
Core: index, scan, stats, update, watcher, doctor, bench, version, hello
Search: search, get-symbol, deps
Symbolic: calls, references, resolution-stats, inherit-tree, descendants, overrides, call-graph, smart-context
Synthesis: skeletonize, get-context, skeleton-file
Dogfood: read, inspect, tree, ls, grep
Utils: generate-tools, verify-context, generate-context

## EXPLORATION [PROTOCOL]
- Index Cerberus itself before exploration.
- Use `search` for concepts, `get-symbol` for logic, `deps` for impact.
- CHALLENGE user if requested changes drift from deterministic mission.

## QUICKREF
PYTHONPATH=src python3 -m cerberus.main index .
PYTHONPATH=src python3 -m pytest tests/ -v
cerberus search "your query"
cerberus smart-context <symbol>