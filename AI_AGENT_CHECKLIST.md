# AI Agent Implementation Checklist for Cerberus

This checklist is designed to guide an AI agent through the autonomous construction of the Cerberus context engine. It breaks down the high-level Roadmap into executable, atomic tasks.

## Phase 0: Project Foundation & Setup
**Objective:** Establish the repository structure, dependency management, and core configuration.

- [x] **Decide on Tech Stack** (Recommended: **Python** for strong AI/Embedding support).
    - [x] Initialize project (e.g., `poetry new cerberus` or `pip install -e .`).
    - [x] Create `requirements.txt` or `pyproject.toml`.
- [x] **Repository Structure**
    - [x] Create `src/` (source code).
    - [x] Create `tests/` (unit tests).
    - [x] Create `docs/` (documentation).
    - [x] Create `.gitignore` (standard Python/Node patterns).
- [x] **Core Dependencies**
    - [x] Select CLI framework (e.g., `Typer` or `Click` for Python).
    - [x] Select Logging library (e.g., `loguru` or standard `logging`).
    - [x] Select Testing framework (e.g., `pytest`).
- [x] **Hello World CLI**
    - [x] Implement a basic entry point (e.g., `main.py`) that prints "Cerberus Active".
    - [x] Verify execution via command line.

## Phase 1: Codebase Mapping (The Scanner)
**Objective:** robustly traverse directory structures, respecting ignore files, and identifying target files.

- [x] **File Walker Module**
    - [x] Implement a function to recursively walk directories.
    - [x] Add support for `respect_gitignore` (using libraries like `pathspec`).
    - [x] Add support for filtering by file extension (e.g., `.py`, `.ts`, `.js`, `.md`).
- [x] **Metadata Extraction (Basic)**
    - [x] For each file found, capture:
        - [x] Relative Path.
        - [x] Absolute Path.
        - [x] File Size.
        - [x] Last Modified Timestamp.
- [x] **Scanner CLI Command**
    - [x] Implement `cerberus scan <directory>` command.
    - [x] Output a structured JSON summary of the scan (file counts, types).
- [x] **Unit Tests**
    - [x] Test walking a dummy directory structure.
    - [x] Test `.gitignore` exclusion logic.

## Phase 2: Symbol Extraction (The Parser)
**Objective:** Parse code files to understand their structure (Functions, Classes) without running them.

- [x] **Parser Integration**
    - [x] Install `tree-sitter` and language bindings (Python/JS). (Pivoted to Regex, but the intent of "parser" is done)
    - [x] Download grammars for key languages (Python, JavaScript, TypeScript). (Pivoted to Regex, config holds patterns)
- [x] **Symbol Extractor**
    - [x] Create a `Parser` class that accepts file content and language. (Implemented as `parser/facade.py` and `python_parser.py`)
    - [x] Implement logic to extract top-level definitions:
        - [x] Function names and line ranges (start/end).
        - [x] Class names and line ranges.
- [x] **Data Structure**
    - [x] Define a `Symbol` schema: `{ name, type, file_path, start_line, end_line, signature }`. (Already done in `schemas.py`)
- [x] **Integration with Scanner**
    - [x] Update the `scan` command to process files through the `Parser`.
- [x] **Unit Tests**
    - [x] Verify extraction of a function from a sample Python file.
    - [x] Verify extraction of a class from a sample JS file.
    - [x] Verify extraction of a class from a sample TS file.

## Phase 3: Indexing & Storage
**Objective:** Persist the mapped data so it can be queried instantly.

- [x] **Database Selection**
    - [x] Choose a lightweight local store (e.g., `SQLite` or a tailored JSON structure for MVP). (JSON store implemented for MVP)
- [x] **Schema Design**
    - [x] Create tables/collections for: `Files`, `Symbols`. (JSON schema mirrors FileObject/CodeSymbol)
- [x] **Index Manager**
    - [x] Implement `IndexBuilder` to save scan results to the DB.
    - [x] Implement `IndexLoader` to read data from the DB.
- [ ] **CLI Update**
    - [x] `cerberus index` command to run the scan + save to DB.
    - [x] `cerberus stats` to show database statistics (e.g., "Index contains 500 symbols").

## Phase 4: Smart Fetch (The Retrieval)
**Objective:** Retrieve specific code chunks by name, solving the "Token Wall".

- [x] **Symbol Lookup**
    - [x] Implement function `find_symbol(name)` that queries the DB.
- [x] **Content Slicing**
    - [x] Implement `read_range(file_path, start_line, end_line)`.
    - [x] Add context padding (e.g., +5 lines before/after).
- [x] **CLI Command**
    - [x] `cerberus get-symbol <name>`
    - [x] Output: The actual code of the function/class.
- [x] **Unit Tests**
    - [x] Test retrieving a known symbol from the index.
    - [x] Test handling of duplicate symbol names (disambiguation strategy).

## Phase 5: Semantic Search (The Brain)
**Objective:** Find code by *meaning* ("Auth logic") not just name ("loginUser").

- [x] **Embedding Provider**
    - [x] Select an embedding model (e.g., `sentence-transformers/all-MiniLM-L6-v2` for local, or OpenAI API). (Now using MiniLM embeddings with fallback token overlap)
- [x] **Vector Store**
    - [x] Integrate a local vector DB (e.g., `ChromaDB`, `FAISS`, or simple NumPy cosine similarity for MVP). (In-memory embedding store built from JSON index snippets)
- [x] **Embedding Pipeline**
    - [x] For each symbol/chunk, generate an embedding vector.
    - [x] Store vector + metadata in the Vector DB.
- [x] **Search Logic**
    - [x] Implement `semantic_search(query_string, limit=5)` with embeddings and thresholded results.
- [x] **CLI Command**
    - [x] `cerberus search "<natural language query>"`
    - [x] Output: Ranked list of code snippets with similarity scores.

## Phase 6: Agent Integration
**Objective:** Expose these capabilities as Tools for LLMs.

- [x] **Tool Definitions**
    - [x] Define JSON schemas for:
        - [x] `GetProjectStructure`
        - [x] `FindSymbol`
        - [x] `ReadSymbol`
        - [x] `SemanticSearch`
- [x] **Output Formatting**
    - [x] Ensure all CLI outputs have a `--json` flag for machine parsing.
- [x] **Documentation**
    - [x] Create `AGENT_INSTRUCTIONS.md` explaining how an agent should use Cerberus.
