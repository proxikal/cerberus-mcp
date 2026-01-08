# Cerberus Robustness Strategy (The "Aegis" Model)

This document outlines the 4-layer defense system for our tool, **Cerberus**. The system itself is codenamed the **"Aegis Model"**. It is designed to make Cerberus resilient, transparent, and "self-healing."

## Layer 1: Structured, Actionable Logging (The Nervous System)
The foundation of our strategy is a **Two-Stream Logging System** that serves both human developers and autonomous agents with maximum efficiency.

### Stream 1: The Human Stream
*   **Destination:** The console (`stderr`).
*   **Format:** Pretty, colorful, human-readable text.
*   **Purpose:** For developers to get a quick, intuitive sense of what Cerberus is doing during manual execution.
*   **AI Context Cost:** **High.** Agents will be instructed to ignore this stream.

### Stream 2: The Agent Stream
*   **Destination:** A dedicated log file, `cerberus_agent.log`.
*   **Format:** **Pure, single-line JSON.** This format is trivial for a machine to parse.
*   **Purpose:** To create a structured, queryable database of events. An AI agent can diagnose issues with surgical precision without needing to "read" the whole log. For example, it can run `grep '"level": "ERROR"' cerberus_agent.log` to find the exact cause of a failure.
*   **AI Context Cost:** **Extremely Low.**

### Implementation Details
*   **Technology:** `loguru`.
*   **Configuration:** A central `logging_config.py` manages both streams. The Agent Stream will use a JSON serializer, log at a `DEBUG` level to capture all details, and automatically rotate to prevent file size from growing indefinitely.

## Layer 2: Custom Exceptions (Precise Diagnoses)
We will avoid generic exceptions to make our error handling explicit and intelligent.

*   **Implementation:** A dedicated `cerberus/exceptions.py` module.
*   **Example Classes:**
    *   `ParserError(file_path, line, message)`: Raised when `tree-sitter` fails on a specific file.
    *   `GrammarNotFoundError(language)`: Raised if a required language grammar is not found.
    *   `IndexCorruptionError(details)`: Raised if the internal database fails a sanity check.
*   **Benefit:** This enables fine-grained control flow like `try...except ParserError:`, allowing the system to gracefully handle a bad file, log the warning, and continue its scan without crashing.

## Layer 3: Performance Tracing (The EKG)
To ensure efficiency, we must measure everything.

*   **Implementation:** A simple `@trace` decorator that can be applied to any function.
*   **Functionality:** When a function is called, the decorator will log its entry, exit, and total execution time to the `DEBUG` level.
*   **Benefit:** Provides a detailed, real-time performance map of all operations, allowing for rapid identification and remediation of bottlenecks.

## Layer 4: The "Doctor" (The Immune Response)
A dedicated CLI command for proactive self-diagnosis and user guidance.

*   **Implementation:** A `cerberus doctor` command within `main.py`.
*   **Core Responsibilities:**
    1.  **Dependency Check:** Verifies that all required external binaries and libraries are installed and accessible.
    2.  **Grammar Check:** Iterates through supported languages and confirms the corresponding `tree-sitter` grammar files are present.
    3.  **Permissions Check:** Tests read/write access for all necessary directories (cache, index, etc.).
    4.  **Index Validation:** Performs a health check on the internal database to detect corruption or schema mismatches.
*   **Self-Healing Guidance:** If a problem is detected (e.g., a missing grammar), the `doctor` will not just report the error; it will provide the **exact shell command** the user needs to run to fix it.
