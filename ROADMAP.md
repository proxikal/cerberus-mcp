# Cerberus Roadmap

> **For AI Agents:** A detailed, step-by-step implementation checklist is available in [AI_AGENT_CHECKLIST.md](./AI_AGENT_CHECKLIST.md).

This roadmap is a living plan. It favors small, testable milestones that deliver value quickly.

## North Star
Provide fast, low-cost, high-signal context slices for codebases by indexing structure, dependencies, and intent.

## Phase 0: Project Foundation
- Define MVP scope and success metrics (latency, token reduction, recall).
- Choose runtime and storage (language, on-disk index format).
- Establish repository structure and developer workflow.

## Phase 1: Codebase Mapping (MVP Pillar 1)
- File discovery and language detection.
- Lightweight symbol extraction (functions, classes, exports).
- Store a basic index (path, symbol name, kind, location).
- CLI command: `scan` to build or refresh the index.

## Phase 2: Smart Fetch (MVP Pillar 2)
- `read_symbol` returns a symbol definition plus minimal context.
- Simple dependency graph: imports/exports + local references.
- CLI command: `read-symbol <name>` with file/line output.

## Phase 3: Semantic Query (MVP Pillar 3)
- Chunking for vector search (configurable window sizes).
- Local vector store (pluggable; default local).
- CLI command: `search "intent"` returning ranked snippets.

## Phase 4: Stability and Speed
- Incremental indexing (git diff or file mtimes).
- Caching and index validation.
- Benchmarks on a real codebase.

## Phase 5: Agent Tooling
- JSON tool interface for agent integration.
- Deterministic outputs with guardrails and strict schemas.

## Open Questions
- Primary language/runtime (Python, Node/TS, Rust)?
- Default vector store choice?
- Target languages for symbol extraction in v1?
- How will we package and distribute the CLI?
