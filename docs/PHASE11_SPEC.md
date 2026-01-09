# Phase 11 Specification: The Surgical Writer (Symbolic Editing)

**Status:** Proposed (To Follow Phase 10)
**Goal:** complete the "Read-Think-Write" efficiency cycle by replacing wasteful "Full-File Rewrites" with precision **Symbolic Editing**. Enable Agents to modify code by *Concept* (Symbol) rather than by *Line Number*, matching their internal reasoning model.

---

## 🚨 The Problem: "Clumsy Hands"
**Observation:** While Phase 8/9 optimized *Reading* (0.2MB), Agents still *Write* inefficiently.
**The Anti-Pattern:** To change 1 line in a 1,000-line file, an Agent often uses `write_file` to regenerate the *entire* 1,000 lines.
**Cost:**
- **Token Waste:** 99.9% of the output tokens are redundant.
- **Risk:** Rewriting unrelated code increases the chance of "Hallucinated Regressions" (dropping a bracket, deleting a comment).
- **Friction:** Agents struggle with strict line-number based patching (`sed`, `patch`) because line numbers drift.

---

## 🎯 The Phase 11 Solution: "Symbolic Editing"

### 1. `cerberus edit` (The Core Command)
**Mission:** Edit code by Name, not Number.
- **Syntax:** `cerberus edit <file> --symbol <name> --replace <new_code_file>`
- **Logic:**
    1.  Cerberus parses `<file>` into an AST.
    2.  It locates the exact byte-range of `<symbol>` (Function, Class, or Variable).
    3.  It replaces *only* that range with the content of `<new_code_file>`.
    4.  It auto-formats (black/prettier) just the changed block.
- **Agent Benefit:** The Agent says *"Change function `process_data`"*, and Cerberus handles the "How" (indentation, line numbers).

### 2. `cerberus insert` (The Injector)
**Mission:** Add new code without context window bloat.
- **Syntax:** `cerberus insert <file> --parent <class_name> --after <method_name> --code "..."`
- **Logic:**
    - "Insert `new_method` into `UserClass` after `__init__`."
- **Agent Benefit:** No need to read the file to find the closing brace. Cerberus knows where the class ends.

### 3. `cerberus delete` (The Scalpel)
**Mission:** Remove dead code safely.
- **Syntax:** `cerberus delete <file> --symbol <name>`
- **Logic:** Removes the symbol and its associated docstring/decorators. Cleans up surrounding whitespace.

### 4. The "Diff Ledger" (Efficiency Tracking)
**Mission:** Prove the value of surgical edits.
- **Metric:** `Write Efficiency Ratio` = (Lines Changed) / (Total File Lines).
- **Goal:** Maintain a ratio of < 5% for maintenance tasks.
- **Feedback:** Command output includes: `[Meta] Saved 950 tokens vs full rewrite.`

### 5. The 4 Pillars of Integrity (Safety Guarantees)
**Mission:** Ensure that surgical edits are **safer** than full-file rewrites. The "Trust-But-Verify" Loop.

1.  **Auto-Indentation (The Formatter):**
    - **Mechanism:** Cerberus detects the target file's indentation style (Spaces vs Tabs).
    - **Dependency:** Requires `black` to be installed (`pip install black`).
    - **Action:** Automatically re-indents the injected code block to match the nesting level and formats it to project standards.
    - **Result:** Agent can be "lazy" with whitespace; Cerberus fixes it.

2.  **The Import Guardian (Dependency Check):**
    - **Mechanism:** Scans the new code block for external references (e.g., `np.array`).
    - **Action:** If the import (`import numpy as np`) is missing from the file, Cerberus **auto-injects** it at the top.
    - **Result:** Prevents `NameError` regressions.

3.  **Syntax Verification (The Dry Run):**
    - **Mechanism:** Before saving, Cerberus applies the patch in-memory and re-parses with Tree-sitter.
    - **Check:** If the resulting AST contains `ERROR` nodes, the edit is **rejected**.
    - **Result:** Physically impossible to break file syntax (unbalanced braces) via `cerberus edit`.

4.  **Semantic Integrity (Symbol Resolution):**
    - **Mechanism:** Leverages the Phase 9 Daemon Index.
    - **Check:** Warns if the new code calls a symbol that doesn't exist in the project.
    - **Result:** Immediate feedback on "Hallucinated Dependencies."

---

## 🧠 Why This is "Natural" (Symbiosis)
- **Cognitive Map:** LLMs think in "Blocks" (Functions/Classes).
- **Tool Match:** Phase 11 tools accept "Blocks" as input.
- **Friction:** Lowest possible. It is *easier* for the Agent to generate just the new function than to generate the whole file.
- **Result:** The Agent *instinctively* chooses Cerberus because it requires less work.

---

## 📉 Success Metrics
1.  **Output Tokens:** > 80% reduction in Write operations.
2.  **Accuracy:** 0% regression rate (unchanged code is never touched).
3.  **Adoption:** Agents prefer `cerberus edit` over `write_file` in > 90% of tasks.

---

## 🔗 Connection to Mission
Phase 11 gives Cerberus "Hands" that are as fast and precise as its "Eyes" (Phase 8) and "Brain" (Phase 9). It completes the **AI Operating System**.
