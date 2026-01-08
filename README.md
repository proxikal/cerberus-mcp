# Cerberus: The Autonomous Context Engine

**Cerberus** is an intelligent "Context Management Layer" designed to bridge the gap between autonomous AI agents and massive software engineering projects. It solves the "Context Wall" problem by pre-processing, indexing, and dynamically serving only the most relevant, compacted context to agents on-demand.

## 🚀 The Problem: The Context Wall

Autonomous agents today face a critical limitation:
- **Context Limits:** Large projects exceed LLM context windows, forcing agents to "forget" or constantly re-read files.
- **API Costs:** Repeatedly fetching massive files burns through API tokens and budgets.
- **Fragmentation:** Agents lose the "big picture" when operating on isolated file chunks.

## 🛡️ The Solution: Cerberus

Cerberus acts as a persistent, intelligent interface for your codebase. Instead of an agent reading `UserAuth.ts` (300 lines) + `db.ts` (500 lines) just to find one function, it asks Cerberus:
> *"Get me the function definition for `loginUser` and its dependencies."*

Cerberus returns a **Compact Context**: just the relevant 50 lines, creating a massive efficiency boost.

### Key Features

*   **🧩 AST-Based Chunking:** Intelligently breaks code into functions, classes, and modules (not just text lines).
*   **🕸️ Project Graph:** Maps dependencies (imports, exports, calls) to understand how files relate.
*   **🧠 Semantic Indexing:** Vector-based search allows agents to find code by *intent* ("Find auth logic") rather than just keywords.
*   **📉 Context Compaction:** Delivers optimized, minimal context payloads to save tokens and improve agent focus.

## 🛠️ Strategic Roadmap (MVP)

Our initial focus is on the **Token Saver MVP**:

1.  **Codebase Mapping:** Generate a structural map of the project (files + exports).
2.  **Smart Fetch Tooling:** Implement `read_symbol` to fetch specific functions/classes instead of full files.
3.  **Local Vector Index:** Enable semantic queries via a local vector database.

## 🔮 Future Vision

Cerberus aims to become the standard "Operating System" for autonomous software engineers, enabling them to tackle multi-million line codebases with the same ease as a single script.

---
*Generated based on AegisMind/Cerberus initial architecture concepts.*