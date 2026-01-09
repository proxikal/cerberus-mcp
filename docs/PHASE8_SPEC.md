# Phase 8 Specification: Predictive Context Assembly & Agent Autonomy

**Status:** Active Planning
**Goal:** Reach the "Final Form" of the Agent Cortex by eliminating the need for multi-turn exploration loops. Enable AI agents to solve complex problems with a single query through predictive context injection.

---

## 🎯 Core Features

### 1. `cerberus blueprint` (Whole-File Blueprint)
**Mission:** Replace the dangerous `cat` command with a token-safe alternative.
- **Description:** Outputs the complete AST-skeleton of a file (classes, signatures, docstrings) while omitting all function bodies.
- **Requirement:** Must be faster than reading the file from disk by utilizing the SQLite index.
- **Agent Benefit:** Allows agents to see the "Interface" of a massive file without loading thousands of logic tokens.

### 2. `cerberus timeline` (Change Intelligence)
**Mission:** Provide instant continuity for agents joining mid-task.
- **Description:** Uses `git diff` to identify and list only the **Symbols** (functions/classes) that have changed in the last N commits or since a specific branch point.
- **Agent Benefit:** Agents immediately identify the "Active Work Zone" and avoid re-analyzing stable code.

### 3. Automatic Type Hydration (`--auto-hydrate`)
**Mission:** Eliminate the "Search -> Get -> Search" exploration loop.
- **Description:** An enhancement to `get-symbol`. When a symbol signature references an internal type (e.g., `user: UserProfile`), Cerberus automatically fetches the skeleton of `UserProfile` and injects it into the response.
- **Constraint:** Limited to internal project symbols to prevent context bloat.
- **Agent Benefit:** One query provides the logic AND the dependencies.

### 4. `cerberus trace-path` (Execution Mapping)
**Mission:** Replace manual dependency tracing with deterministic chains.
- **Description:** Maps the execution path from a source symbol to a target symbol (e.g., `api_endpoint` -> `db_save`).
- **Output:** A sequence of skeletons showing how data flows through the system.
- **Agent Benefit:** Instant architectural understanding of complex data flows.

### 5. Agent Session Cache (Redundancy Filter)
**Mission:** Zero-token re-transmission.
- **Description:** Tracks which symbols have been sent to the agent in the current session.
- **Mechanism:** If an agent requests a symbol it already "knows," Cerberus sends a lightweight pointer/hash unless `--force` is used.
- **Agent Benefit:** Prevents "Session Amnesia" and saves massive tokens in long-running tasks.

---

## 🛠️ Autonomy Mandate: Replacing Legacy Tools

To achieve the Cerberus mission, the agent must be guided to abandon legacy shell tools.

### 🚫 Forbidden Legacy Tools
- `cat`: Wastes tokens on logic. Use `cerberus read --lines` or `cerberus blueprint`.
- `grep`: Unstructured. Use `cerberus search`.
- `ls -R`: Shallow. Use `cerberus tree --symbols`.

### ✅ The Cerberus Standard
Phase 8 is complete when an agent can perform a high-level refactor using **ONLY** Cerberus tools, resulting in **< 5% of the token usage** compared to legacy exploration.

---

## ✅ Integrity Mandate
1. **100% Completion:** No "partial" implementations. Every command must handle Python, JS, TS, and Go.
2. **Fidelity:** Hydration must never hallucinate types; it must be backed by the SQLite symbol store.
3. **Firmness:** The agent must be instructed to reject legacy tools when Cerberus equivalents exist.

---

**Goal:** Turn Cerberus into the indispensable "Brain Extension" for every AI Engineer.
