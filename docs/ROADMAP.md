# Cerberus Roadmap: The Powerhouse Path

This roadmap focuses on the remaining milestones to transition Cerberus into a Deep Context Synthesis engine.

## Phase 1: Advanced Dependency Intelligence
*   **Recursive Call Graphs:** Map execution paths beyond a single level of callers.
*   **Type-Aware Resolution:** Track class instances and their types across file boundaries to resolve method calls accurately.
*   **Import Linkage:** Explicitly link symbols to their imported sources in the graph.

## Phase 2: Context Synthesis & Compaction
*   **Advanced Skeletonization:** Use AST-aware pruning to remove function bodies while keeping signatures and docstrings. ✅ **CORE FEATURE**
*   **Payload Synthesis:** Merge a target function implementation with the skeletons of its surrounding class and relevant imports. ✅ **CORE FEATURE**
*   **Auto-Summarization:** Integration of lightweight local LLMs to pre-summarize large files or architectural layers. ⚠️ **OPTIONAL / LOW PRIORITY**
    *   *Purpose:* To act as a "token-saver" by delivering pre-digested summaries to the primary agents (Claude, Codex) for non-critical code paths.

**Note:** Cerberus is designed to be the *source of truth* for AI agents. The use of internal LLMs is strictly for context optimization and is not a substitute for the high-reasoning capabilities of the agent consuming the context. Priority remains on deterministic, AST-based retrieval.

## Phase 3: Operational Excellence ✅ COMPLETE
*   ✅ **Git-Native Incrementalism:** Use `git diff` to identify modified lines and surgically update the index (re-parsing only changed symbols).
*   ✅ **Background Watcher (Invisible Assistant):** A lightweight daemon process that automatically starts when an agent initiates a scan or query if not already active. It keeps the index synchronized with the filesystem in real-time without user intervention.
*   ✅ **Hybrid Retrieval Optimization:** Fine-tuning the balance between BM25 keyword matching and Vector semantic search.

**Status:** All milestones complete (34/34 tests passing). Includes `cerberus update` and `cerberus watcher` commands with full functionality.

## Phase 4: Integration & Aegis-Scale Performance
*   **Aegis-Scale Memory Optimization:** Transition to a streaming, disk-first architecture (SQLite) to support 10,000+ files under 250MB RAM.
*   **Official Agent Plugins:** Native tool-sets for LangChain and CrewAI.
*   **Web-UI (Optional):** A lightweight local dashboard for visual exploration of the project graph.
*   **Security Scanning:** Automated PII and secret detection within the indexing pipeline.
