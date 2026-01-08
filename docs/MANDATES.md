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
