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

## Phase 4: Aegis-Scale Performance ✅ COMPLETE
*   ✅ **Aegis-Scale Memory Optimization:** Streaming, disk-first architecture (SQLite + FAISS) supporting 10,000+ files under 250MB RAM.
    *   ✅ True streaming scanner with generator-based file processing
    *   ✅ Batch processing (100 files) with immediate writes
    *   ✅ Chunked transaction inserts (1000 symbols per chunk)
    *   ✅ TensorFlow validation: 2,949 files, 68,934 symbols at 126.5 MB peak
    *   ✅ **42.6x memory reduction** (1.2 GB → 28.1 MB indexing)
*   **Official Agent Plugins:** Native tool-sets for LangChain and CrewAI. 🔜 **NEXT**
*   **Web-UI (Optional):** A lightweight local dashboard for visual exploration of the project graph.
*   **Security Scanning:** Automated PII and secret detection within the indexing pipeline.

**Status:** Aegis-Scale memory optimization complete with 49% headroom under target (126.5 MB peak vs 250 MB target). System is production-ready for massive codebases.

## Phase 5: Symbolic Intelligence
*   **Instance → Definition Resolution:** Resolve method calls on instances to their class definitions (e.g., `optimizer.step()` → `Optimizer.step()`).
*   **Type Tracking:** Track variable types across file boundaries for accurate context delivery.
*   **Cross-Reference Resolution:** Link symbol usage to definitions across the entire codebase.
*   **Advanced Context Synthesis:** Combine symbolic resolution with existing skeletonization for precision context delivery.

**Goal:** Enable AI agents to navigate codebases with full symbolic understanding, resolving references with 100% accuracy even across complex inheritance hierarchies and dynamic typing.
