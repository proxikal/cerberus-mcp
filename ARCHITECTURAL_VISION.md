# Cerberus Architectural Vision & Strategy

## 1. Core Mandate: Efficiency Through Deterministic Code
We are building a tool to *solve* context inefficiency. Therefore, our build process and the tool itself must embody this principle.
*   **Code over Prompts:** We build rigid, reliable software tools (CLIs, Parsers). We do not rely on "AI Prompts" to do the heavy lifting of code analysis.
*   **Deterministic Foundation:** The indexing and retrieval layers must be mathematically predictable (AST parsing, Vector Math) so that the AI Agent layer on top can be creative without hallucinating facts about the codebase.

## 2. Technology Stack
*   **Language:** **Python 3.10+**
    *   *Why:* Native language of AI, best ecosystem for Embeddings/Vector DBs, excellent CLI tools.
*   **Type System:** **Strict Typing with Pydantic**
    *   *Why:* Self-documenting code. An agent only needs to read the Schema to understand the system.
*   **CLI Framework:** **Typer**
    *   *Why:* Fast, declarative, auto-generates help documentation.
*   **Parsing:** **Tree-Sitter**
    *   *Why:* Robust, multi-language AST parsing (far superior to Regex).
*   **Testing:** **Pytest**
    *   *Why:* Industry standard, supports TDD.

## 3. The "Context-Efficient" Build Strategy
To build this without bloating our own context window:
1.  **Skeleton & Fill:** We define empty modules and interfaces first.
2.  **Contract First:** We write `schemas.py` to define data shapes (Inputs/Outputs) before writing logic.
3.  **Module Isolation:** We work on one module at a time (e.g., `parser.py`) without loading the entire project into context.
4.  **TDD:** We write the test first. The test is the "spec".

## 4. System Architecture
The application is divided into 4 decoupled modules to prevent spaghetti code:

### A. The Schema Layer (`schemas.py`)
The single source of truth for all data structures.
*   `FileObject`: Path, size, hash.
*   `CodeSymbol`: Name, type (Function/Class), line numbers, file path.
*   `IndexStats`: Total files, total symbols.

### B. The Scanner (`scanner.py`)
*   **Role:** The Legs.
*   **Responsibility:** Efficiently walks the file system.
*   **Input:** Root directory path.
*   **Output:** List of `FileObject`s.
*   **Key Feature:** Respects `.gitignore` and `.cerberusignore`.

### C. The Parser (`parser.py`)
*   **Role:** The Eyes.
*   **Responsibility:** Extracts structure (AST) from text.
*   **Input:** Source code string + Language.
*   **Output:** List of `CodeSymbol`s.
*   **Key Feature:** Language-agnostic abstraction (adapters for Python, TS, JS, Go).

### D. The Brain (`brain.py`)
*   **Role:** The Memory.
*   **Responsibility:** Manages the persistence layer (SQL/JSON/Vector DB).
*   **Input:** List of `CodeSymbol`s.
*   **Output:** Search results, retrieved code chunks.

### E. The Interface (`main.py`)
*   **Role:** The Mouth.
*   **Responsibility:** CLI entry point using `Typer`.
*   **Logic:** Orchestrates calls to Scanner -> Parser -> Brain.

## 5. The Self-Similarity Mandate
To ensure Cerberus itself remains maintainable by AI agents, its architecture is governed by a strict set of rules for compartmentalization and abstraction.

**[Read the full details in SELF_SIMILARITY.md](./SELF_SIMILARITY.md)**

## 6. Robustness & Self-Healing
To ensure Cerberus is a reliable foundation for AI agents, it incorporates a multi-layered defense system for logging, error handling, and self-diagnosis.

**[Read the full details in the ROBUSTNESS_STRATEGY.md](./ROBUSTNESS_STRATEGY.md)**

## 7. Development Workflow
1.  Define the **Schema** for a feature.
2.  Write a **Unit Test** for that feature.
3.  Implement the **Module** to pass the test.
4.  Integrate into **CLI**.
