# CERBERUS v0.6.0 - AI Agent Context
# Protocol: UACP/1.0 | Tokens: ~400 | Compression: 85% | Fidelity: 100%
# Compatible: Claude, Gemini, Copilot, Cursor, Windsurf, Aider
# Truth: THIS_FILE | Verify: sha256(src/+tests/+docs/) | Gen: 2026-01-08

## CORE [ALWAYS_LOAD]
id=cerberus mission=AST→symbol→context type=deterministic_engine
status=P1-6:✅ P7:🔜 tests=167/182(0❌) prod=READY
principle=code_over_prompts forbidden=[LLM_analysis,time_est,feature_creep]

## IDENTITY
Cerberus: deterministic context management layer for AI agents
Core: surgical AST parsing → symbolic intelligence → compressed context
NOT: LLM-based analysis, prompt engineering, RAG chunking

Principles:
  code>prompts: tree-sitter AST | SQLite | FAISS → ∅LLM
  self_similar: ∀pkg∃{facade.py,config.py,__init__.py} ∧ ¬cross_import
  aegis: {log:struct, exc:custom, trace:@, diag:doctor}
  dogfood: cerberus.index(cerberus)==REQUIRED

Forbidden:
  LLM_code_analysis → use tree-sitter AST instead
  time_estimates → say WHAT not WHEN
  feature_creep → IF !context_mgmt THEN reject+explain
  proactive_docs → user_explicit_request REQUIRED
  cross_imports → only via __init__.py exports
  emojis → unless user requests
  commit → ONLY when user requests

## RULES [DECISION_MATRIX]
@new_feature:
  IF: !serves_context_management
  DO: [STOP, explain_mission_violation, propose_alternative]
  FIRM: mission_integrity > feature_requests

@new_package:
  REQUIRE: [facade.py, config.py, __init__.py]
  TEST: can_cerberus_index_itself()
  PATTERN: self_similarity_mandate

@code_analysis:
  IF: suggest_LLM
  REJECT: "use tree-sitter AST parsing (deterministic)"

@documentation:
  IF: proactive
  REJECT: "explicit user request required (no unsolicited docs)"

@commit:
  WHEN: user_explicitly_requests OR pre_commit_hook_modified_files
  NEVER: proactive OR uncommitted_changes
  STYLE: conventional_commits + "Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

@architecture:
  IF: violates_self_similarity OR violates_aegis
  DO: [STOP, cite_mandate, propose_compliant_alternative]

## STATUS
version: 0.6.0
phases: P1-6(complete) P7(planned)
tests: 167/182 passing | 15 skipped | 0 failing
production: READY
compliance: self_similar=100% aegis=100% mission=100%
validated: TensorFlow(2949files,68934symbols)

Performance:
  memory: 126MB peak | -49% vs 250MB target | Δ42.6x reduction
  tokens: 99.7%↓ (150K→500) | smart_ctx: 87%↓
  speed: <1s search | 43s/3Kfiles index | <1s update@<5%
  capacity: 10K+ files | 68K symbols validated

## ARCH [→FEATURE_MATRIX.md#architecture]
pipeline: scan→parse→index→retrieve→resolve→synthesize
packages: [scanner,parser,index,retrieval,incremental,watcher,synthesis,storage,resolution]
pattern: ∀pkg∃{facade.py,config.py} | export_via=__init__.py | ¬cross_import

Storage:
  primary: SQLite+ACID | vector: FAISS(optional) | arch: streaming_const_mem

Compliance:
  10/10 packages: facade.py ✅
  10/10 packages: config.py ✅
  4/4 aegis layers: {log,exc,trace,diag} ✅

## PHASES [→ROADMAP.md]
P1(dep_intel): ✅ 18/18 | [deps,inspect]
  - recursive call graphs, type resolution, import linkage

P2(synthesis): ✅ 12/13 | [skeletonize,get-context]
  - AST skeletonization (Python), payload synthesis, token budget

P3(ops): ✅ 34/34 | [update,watcher,search]
  - git-diff incremental, background daemon, BM25+vector hybrid

P4(perf): ✅ mem:42.6x↓ | [index,stats,bench]
  - streaming arch, SQLite+FAISS, TensorFlow validated

P5(symbolic): ✅ 14/14 | [calls,references,resolution-stats]
  - method call extraction, import resolution, type tracking

P6(context): ✅ 14/14 | [inherit-tree,descendants,overrides,call-graph,smart-context]
  - inheritance resolution, MRO, call graphs, cross-file type inference

P7(agent_plugins): 🔜 planned | [langchain,crewai,mcp]
  - official agent integrations, streaming API

## COMMANDS [40 total → README.md#cli-reference]
Core: index scan stats update watcher doctor bench version hello
Search: search get-symbol deps
P5: calls references resolution-stats
P6: inherit-tree descendants overrides call-graph smart-context
Synthesis: skeletonize get-context skeleton-file
Dogfood: read inspect tree ls grep
Utils: generate-tools

## WORKFLOW [AI_AGENT_PATTERNS]
1. index_first: cerberus index . [BEFORE any exploration]
2. search_before_read: cerberus search 'X' [BEFORE reading files]
3. use_dogfood_tools: cerberus {inspect,deps,grep} [INSTEAD OF manual]
4. test_after_code: pytest tests/ [AFTER writing code]
5. commit_when_asked: git commit [ONLY when user requests]

## VERIFY [SELF_CHECK]
tests: PYTHONPATH=src python3 -m pytest tests/ → 167/182 ✅
dogfood: cerberus index . → 60files,209symbols ✅
arch: find src/cerberus -name facade.py | wc -l → 10 ✅
no_cross: grep -r 'from cerberus\..* import' src/cerberus → 0 ✅

## DOCS [HIERARCHY: authoritative→reference]
Truth (absolute):
  1. CERBERUS.md ← THIS FILE
  2. CERBERUS_AUDIT_2026-01-08.md ← current state verification
  3. FEATURE_MATRIX.md ← complete feature catalog

Current:
  README.md ← user overview
  ROADMAP.md ← phase status
  docs/VISION.md ← philosophy
  docs/MANDATES.md ← development rules
  docs/AGENT_GUIDE.md ← integration guide

Ignore:
  docs/archive/* ← historical only
  PHASE*_COMPLETE.md ← superseded by ROADMAP.md

## EXPLORATION [USE_CERBERUS_TOOLS]
DO_NOT: read entire codebase manually, grep without index, find without index
DO: cerberus search "concept" | cerberus inspect file.py | cerberus deps symbol
Dogfooding: Cerberus must analyze itself using its own tools

## QUICKREF
PYTHONPATH=src python3 -m cerberus.main index .
PYTHONPATH=src python3 -m pytest tests/ -v
cerberus search "how does X work"
cerberus deps --symbol Y --recursive
cerberus smart-context ClassName --include-bases

---
# Schema Validation
# IF this_file != actual_codebase THEN regenerate_with: cerberus generate-context
# Verify: cerberus verify-context
# Update: edit CERBERUS.md THEN cerberus convert-agent-context --generate all
