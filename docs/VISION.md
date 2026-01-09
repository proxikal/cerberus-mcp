# Cerberus: The Architectural Vision

Cerberus is an intelligent "Context Management Layer" designed to bridge the gap between autonomous AI agents and massive software engineering projects. It solves the **"Context Wall"** problem by pre-processing, indexing, and dynamically serving only the most relevant, compacted context to agents on-demand.

## 1. Core Mandate: Efficiency Through Surgical Precision
We build rigid, reliable software tools (CLIs, Parsers) to provide a deterministic foundation for AI agents.
*   **Code over Prompts:** We don't rely on LLMs for the heavy lifting of code analysis. We use AST parsing and Vector search.
*   **Deterministic Foundation:** Indexing and retrieval are predictable, allowing agents to be creative without hallucinating facts.
*   **Surgical Precision:** We modify code by *Symbol* (AST), not by *Line Number*. We fix the "clumsy hands" of LLMs.

## 2. Strategic Evolution
Our goal is to move from "Search and Retrieve" to **Deep Context Synthesis**.

### Symbolic Intelligence
Beyond simple indexing, Cerberus aims to understand the *meaning* of code relationships. This includes resolving instances to their source definitions and tracking types across file boundaries.

### Context Compaction
Cerberus is a "token-saver." By providing surgical snippets and skeletonized architectural views, it allows high-reasoning agents (like Claude or Gemini) to operate on massive codebases without hitting context limits or wasting compute on boilerplate.

### Operational Transparency
Through the **Aegis Robustness Model**, Cerberus provides clear diagnostics and structured logging, ensuring that an autonomous agent can monitor its own context layer's health.

## 3. The Cortex Architecture (Phase 9)
Cerberus is evolving from a "CLI Tool" to a **Persistent Daemon**.
*   **Zero-Latency:** The "Brain" stays warm in RAM.
*   **Tiered Memory:** Massive scale (100k files) without Agent RAM bloat.
*   **Secure Swarm:** Multi-agent coordination via local sockets.

## 4. Symbiosis (Phase 10 & 11)
Cerberus must be the "Natural Choice" for any Agent.
*   **Phase 10:** The Deterministic Interface (JSON Protocol).
*   **Phase 11:** The Surgical Writer (Symbolic Editing).
*   **Goal:** The Agent uses Cerberus not because it *has to*, but because it is *easier* and *safer* than the alternatives.

---

For detailed specifications, see:
- [Phase 8: Context Compression](./PHASE8_SPEC.md)
- [Phase 9: Cortex Daemon](./PHASE9_SPEC.md)
- [Phase 10: Deterministic Interface](./PHASE10_SPEC.md)
- [Phase 11: Surgical Writer](./PHASE11_SPEC.md)
