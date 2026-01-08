# The Self-Similarity Mandate

This document defines the core architectural principle governing the development of Cerberus itself. The mandate is simple: **Cerberus must be its own ideal client.** The architecture must be so clean and compartmentalized that an AI agent can maintain and debug Cerberus using the very tools Cerberus provides.

This prevents the project from becoming a "context wall" of its own, ensuring its long-term viability for AI-driven development.

## The 4 Rules of Self-Similarity

### 1. The "Module as a Microservice" Rule
No single file shall become a monolith. Every major component (`scanner`, `parser`, `brain`) **must be a directory (a Python package)**, not a single `.py` file.

*   **Structure:**
    *   `component_name/`
        *   `__init__.py`: The public contract. Exports *only* the high-level functions from the facade.
        *   `facade.py`: The primary entry point containing the main function(s).
        *   `specialist_a.py`, `specialist_b.py`: Internal modules that handle specific logic.
        *   `config.py`: Data-only configuration (e.g., lists of patterns, settings).
        *   `utils.py`: Helper functions used only within the component.

*   **Benefit:** Surgically contains context. An agent needing to fix a bug in a specialist module is never exposed to the complexity of other specialists.

### 2. The "Strict Facade" Rule
Modules are forbidden from talking to each other's internal components. The public API of a module is defined **exclusively** by what its `__init__.py` exports.

*   **Correct Usage:** `from cerberus.parser import parse_file`
*   **Forbidden Usage:** `from cerberus.parser.python_parser import some_internal_func`

*   **Benefit:** Creates clean, decoupled boundaries. Internals can be rewritten safely without breaking other parts of the application. It minimizes cognitive load.

### 3. The "Configuration as Data" Rule
Logic files must not contain complex configuration. All configuration—such as supported language lists, default ignore patterns, or processing flags—must be extracted into a `config.py` file within the module.

*   **Benefit:** To change behavior, an agent can perform a small, targeted modification on a simple data file instead of parsing complex application logic.

### 4. The "Dogfooding" CI/CD Rule
Cerberus must be able to index and analyze itself. Our test suite will include a workflow that:

1.  **Indexes Thyself:** Runs `cerberus scan` and `cerberus parse` on its own source code.
2.  **Queries Thyself:** Uses the `cerberus get-symbol` command to retrieve a function from its own indexed codebase.
3.  **Asserts Success:** The test passes if Cerberus can successfully find and retrieve its own functions.

*   **Benefit:** This is the ultimate guarantee of the system's utility and maintainability. It is the core feedback loop that proves the Self-Similarity Mandate is being upheld.
