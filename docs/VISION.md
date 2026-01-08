# Cerberus: The Architectural Vision

Cerberus is an intelligent "Context Management Layer" designed to bridge the gap between autonomous AI agents and massive software engineering projects. It solves the **"Context Wall"** problem by pre-processing, indexing, and dynamically serving only the most relevant, compacted context to agents on-demand.

## 1. Core Mandate: Efficiency Through Deterministic Code
We build rigid, reliable software tools (CLIs, Parsers) to provide a deterministic foundation for AI agents.
*   **Code over Prompts:** We don't rely on LLMs for the heavy lifting of code analysis. We use AST parsing and Vector search.
*   **Deterministic Foundation:** Indexing and retrieval are predictable, allowing agents to be creative without hallucinating facts about the codebase.

## 2. The "Powerhouse" Evolution
Our goal is to move from "Search and Retrieve" to **Deep Context Synthesis**.

### Deep Resolution (Symbolic Intelligence)
*   **Cross-File Symbol Resolution:** Resolve instances to their source definitions (e.g., knowing `authService` is a `JWTService`).
*   **Type-Aware Indexing:** Indexing types, interfaces, and enums to answer architectural questions.
*   **Call-Graph Navigation:** Recursive mapping of execution paths.

### Context Compaction & Synthesis
*   **Skeletonized Scoping:** Providing the implementation of a target function while skeletonizing the rest of the file to preserve context without wasting tokens.
*   **Import Resolution Padding:** Automatically including definitions of internal types used in retrieved snippets.
*   **Synthesis:** Merging related snippets into a single, cohesive "Goldilocks" payload.
*   **Auto-Summarization (Optional / Low Priority):** The use of lightweight, local LLMs to pre-summarize boilerplate or non-critical modules. This serves as an optimization layer to further reduce token usage for high-reasoning agents (Claude, Codex) by delivering pre-digested summaries instead of raw code where appropriate.

### Operational Power (Speed & Scalability)
*   **Git-Native Incrementalism:** Use `git diff` to identify modified lines and surgically update the index (re-parsing only changed symbols).
*   **Background Watcher (Invisible Assistant):** A lightweight daemon process that automatically starts when an agent initiates a scan or query if not already active. It keeps the index synchronized with the filesystem in real-time without user intervention.
*   **Hybrid Semantic Search:** Combine **BM25 (Keyword)** and **Vector (Semantic)** search to ensure precise hits for specific variable names and broad conceptual queries alike.

## 3. Technology Stack
*   **Language:** Python 3.10+
*   **Type System:** Strict Typing with Pydantic
*   **CLI Framework:** Typer
*   **Parsing:** Hybrid approach (Tree-Sitter for deep AST, Regex for lightweight scans)
*   **ML:** Local Transformer Embeddings (Sentence-Transformers)
