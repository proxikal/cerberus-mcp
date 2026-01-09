# Cerberus Development Mandates

To ensure Cerberus remains maintainable and reliable, all development must adhere to these two core strategies.

---

## 1. The Self-Similarity Mandate
Cerberus must be its own ideal client. The architecture must be so clean that an AI agent can maintain Cerberus using the tools Cerberus provides.

### The 4 Rules
1.  **Module as a Microservice:** Every major component (`scanner`, `parser`, `index`) must be a directory (package), not a single file. Each package must have a `facade.py` and a clean `__init__.py`.
2.  **Strict Facade Rule:** Modules are forbidden from talking to each other's internals. Public APIs are defined exclusively by `__init__.py` exports.
3.  **Configuration as Data:** Logic files must not contain complex configuration. Use `config.py` for patterns, settings, and constants.
4.  **Dogfooding:** Cerberus must be able to index and analyze itself.
5.  **Parsimony (The Surgical Rule):** Never rewrite a full file if a surgical edit (patch) is sufficient. Prioritize atomic, verifiable changes to minimize token waste and regression risk.

---

## 2. The Aegis Robustness Model
A four-layer defense system for resilience and transparency.

### Layer 1: Structured Logging
*   **Human Stream:** Pretty, colorful `stderr` output for developers.
*   **Agent Stream:** Pure, single-line JSON logs in `cerberus_agent.log` for machine diagnostics.

### Layer 2: Custom Exceptions
Avoid generic exceptions. Use specific classes like `ParserError` or `IndexCorruptionError` in `cerberus/exceptions.py` to enable fine-grained error handling.

### Layer 3: Performance Tracing
Use a `@trace` decorator (or equivalent) to log entry, exit, and execution time of critical functions to identify bottlenecks.

### Layer 4: Proactive Diagnostics (The Doctor)
The `cerberus doctor` command must check dependencies, permissions, and index health, providing exact shell commands for remediation.

---

## 3. The Symbiosis Protocol
Cerberus is designed for Agents first, Humans second.

### Rule 1: Deterministic Interfaces
*   **Inputs:** Strict arguments via CLI flags (Phase 10 Schema).
*   **Outputs:** Structured JSON (Machine Mode) over Markdown tables.
*   **Errors:** Actionable JSON objects with `suggestions`, not vague text.

### Rule 2: Token Discipline
*   **Read:** Use `blueprint` or `get-symbol` instead of `cat`.
*   **Write:** Use `edit` or `patch` instead of `write_file`.
*   **Metric:** Every operation must justify its token cost.

### Rule 3: The Cortex Architecture
*   **State:** Held by the Daemon (Phase 9), not the Agent.
*   **Memory:** Tiered caching (RAM/SSD) to prevent Agent context bloat.
