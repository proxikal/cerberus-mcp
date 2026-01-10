# Phase 12 Specification: The Harmonized Writer (Agent Symbiosis)

**Status:** Implementation Complete (Enhancements Planned)
**Goal:** Achieve "Perfect Harmony" between the AI Agent and the Cerberus Tool. This phase implements the "Best Result" for code modification: Atomic Batching, Verified Transactions, and Advanced Safety Guards.

---

## 🎯 Core Objectives (Implemented)

### 1. The Batch Edit Protocol (Atomic Transactions)
**Mission:** Enable Agents to perform complex, multi-file refactors in a single turn without "Partial Failure" risks.
- **Problem:** "Partial Failure" leaves codebases in a broken state.
- **Solution:** `cerberus batch-edit <instructions.json>`
- **Logic:**
    1.  Load all target files.
    2.  Apply edits in-memory (AST-based).
    3.  **Sequential Integrity:** Re-parse the AST between steps to prevent line-number drift.
    4.  **Atomic Write:** Save all files at once.

### 2. The Verified Transaction (`--verify`)
**Mission:** The Agent literally **cannot break the build**.
- **Feature:** `cerberus batch-edit changes.json --verify "pytest tests/"`
- **Logic:**
    - **Snapshot:** Backup files to memory/disk.
    - **Apply:** Write changes.
    - **Verify:** Run the test command.
    - **Auto-Revert:** If tests fail (Exit Code != 0), restore the backup immediately.
- **Benefit:** Zero regression risk. The Agent operates in a "Hypothesis Testing" loop.

### 3. "Diff-First" Feedback
**Mission:** Speak the Agent's native language (`git diff`).
- **Feature:** Every mutation returns a **Unified Diff**.
- **Benefit:** Immediate visual confirmation of the exact change.

### 4. Strict Resolution & Optimistic Locking
- **Strict Mode:** NO Auto-Correct on writes. Ambiguous symbols = Error + Suggestions.
- **Locking:** Check file `mtime` before writing. If changed externally, Abort.

---

## 🚀 Phase 12.5: "Platinum" Enhancements (The Safety Net)

To achieve the "Best Possible Result," we add layers of intelligence and recovery.

### 5. The Symbol Guard (Reference Protection)
**Mission:** Prevent accidental "Mass Extinction" events.
- **Solution:**
    - Before any `delete` or `rename` operation, check the **Phase 9 Index**.
    - If `reference_count > 0`: BLOCK the operation.
    - **Error:** `[SAFETY BLOCK] Symbol 'ClassA' is referenced in 50 files. Use --force to override.`

### 6. Persistent Undo Stack (`cerberus undo`)
**Mission:** Infinite "Ctrl+Z" for the Agent.
- **Solution:** Store every successful batch transaction in `.cerberus/history/`. `cerberus undo` applies the Reverse Patch.

### 7. Dry Run Preview (`--preview`)
**Mission:** "Measure twice, cut once."
- **Feature:** `cerberus batch-edit ops.json --preview`
- **Benefit:** Allows the Agent to "Visualise" the outcome before committing to the disk write.

---

## 💎 Phase 12.5: "Diamond" Enhancements (Intelligence)

### 8. Semantic Smart Merge (Conflict Resolution)
**Mission:** Solve the "Collaboration" friction.
- **Logic:** If an Optimistic Lock fails (file changed externally):
    - **Action:** Attempt a **Three-Way AST Merge**.
    - **Condition:** **REQUIRED:** Must be run with `--verify`.
    - **Safety:** If AST nodes do not overlap, merge and run tests. If tests pass, commit.

### 9. The Style Guard (Mini-Linter)
**Mission:** Prevent "Lint Rot" and sloppy AI code.
- **Logic:** Before Atomic Write, run a lightweight internal linter.
- **Action:** **Auto-Fix** uncontroversial issues (unused imports) in *changed lines only*. Never block valid logic.

### 10. Token-Aware Diffing
**Mission:** Prevent Context Window Explosion.
- **Logic:** If the generated Diff > 100 lines:
    - **Action:** Truncate large blocks of *added* code.
    - **Constraint:** NEVER truncate *deleted* lines (high risk).

### 11. Just-in-Time (JIT) Guidance (The "Whisper" Protocol)
**Mission:** Eliminate "Syntax Hallucination" across all models (Claude, Gemini, Codex).
- **Problem:** Agents sometimes forget the exact syntax of a tool.
- **Solution:** Proactively teach the next step in the output footer.
    - Output of `search`: `[Tip] To see the file structure, run: cerberus blueprint src/file.py`
    - Output of `read`: `[Tip] To modify this symbol, run: cerberus edit src/file.py --symbol ...`
- **Benefit:** The Agent never has to guess; the tool guides the workflow.

### 12. Context Anchoring (The "GPS")
**Mission:** Prevent "Context Confusion" in massive-context models (1M+ tokens).
- **Problem:** Models lose track of file identity in long scrolls.
- **Solution:** Every output block must have a rigid, standardized header.
    - **Format:** `[File: src/auth.py] [Symbol: AuthConfig] [Lines: 10-45] [Status: Read-Only]`
- **Benefit:** Provides a permanent "Anchor Point" for the LLM's attention mechanism, drastically improving retrieval accuracy.

---

## 📉 Success Metrics
1.  **Integrity:** 0% Data Loss (via Optimistic Locking & Undo).
2.  **Safety:** 0% Accidental Deletion of referenced symbols (via Symbol Guard).
3.  **Latency:** < 100ms overhead for typical batches.
4.  **Symbiosis:** Agents prefer `cerberus` over direct file IO in > 95% of tasks.

---

## 🔗 Connection to Mission
Phase 12 transforms Cerberus from a "Text Editor" into an **Intelligent Guardian**. It enforces architectural safety rules (Symbol Guard), provides a safety net (Undo/Verify), intelligently manages conflicts (Smart Merge), and guides the Agent (JIT/Anchoring)—all while maintaining determinism.