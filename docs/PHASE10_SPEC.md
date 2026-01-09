# Phase 10 Specification: The Deterministic Interface (Agent Symbiosis)

**Status:** Proposed (To Follow Phase 9)
**Goal:** Transform Cerberus from a CLI Tool into a **Deterministic Agent Operating System**. Eliminate "Presentation Bloat," enforce strict data protocols, and enable Self-Healing and Atomic Batching to maximize Agent efficiency.

---

## 🎯 Core Objectives

### 1. The Global "Machine-First" Protocol
**Mission:** Ensure 100% Signal / 0% Noise by default.
- **Problem:** Conventional tools default to human-readable output (tables, colors), forcing agents to opt-out of bloat.
- **Solution:**
    - **Machine Mode is the DEFAULT.** All commands return minified JSON or raw text unless specified otherwise.
    - Implement a `--human` (or `-H`) flag to opt-in to "Pretty" output (Markdown tables, emojis, colors).
    - **Result:** The Agent never has to remember to be efficient; the tool is efficient by design.
- **Example:**
    - *Default (Agent):* `User:Class:src/user.py` (5 tokens)
    - *Opt-in (--human):* `| Symbol | Type | ...` (100 tokens)

### 2. Configurable "Token Ledger" (Metrics)
**Mission:** Provide precise, optional feedback on efficiency without polluting the output.
- **Requirement:** Retain existing "Session Total" but add "Per-Turn" tracking.
- **Flags:**
    - `--show-turn-savings`: Appends a single line: `[Meta] Saved: 450 tokens`.
    - `--show-session-savings`: Appends a single line: `[Meta] Session Saved: 50,000 tokens`.
    - `--silent-metrics`: Suppresses all metric output (default in Machine Mode).
- **Format:** Strict, minimal one-liners. No boxes, no colors.

### 3. "Strip the Paint" (Codebase Audit)
**Mission:** Remove hardcoded "Human Vanity."
- **Action:** Audit codebase for:
    - `rich.print` / `console.print`
    - ASCII Art Banners
    - Emoji literals ("✅", "❌")
- **Implementation:** Wrap all such outputs in `if not config.MACHINE_MODE:` checks.
- **Result:** The Agent receives pure data.

### 4. The Symbiosis Check (Protocol Enforcement)
**Mission:** Active correction of wasteful Agent behavior.
- **Feature:** Output Interception.
- **Logic:** If Cerberus detects usage of forbidden legacy patterns (e.g., `ls -R`, `cat` on large files):
    - **Intercept:** Stop the output.
    - **Replace:** Return a minimal warning: `[PROTOCOL] 'ls -R' blocked. Use 'cerberus index'. Output suppressed.`
- **Benefit:** Prevents the Agent from accidentally flooding its own context window.

### 5. Structured Failure (Self-Healing)
**Mission:** Turn errors into actionable data points, eliminating "Agent Confusion."
- **Problem:** Text errors (`Error: Symbol not found`) require the Agent to "think" and guess.
- **Solution:** Return JSON Error Objects with actionable `suggestions`.
- **Example:**
    ```json
    {
      "status": "error",
      "code": "SYMBOL_NOT_FOUND",
      "input": "Usr",
      "suggestions": ["User", "UserConfig", "Auth"],
      "actionable_fix": "cerberus get-symbol User"
    }
    ```
- **Result:** The Agent performs **Deterministic Recovery** (retries immediately using the suggestion) without reasoning overhead.

### 6. The Schema Contract (Introspection)
**Mission:** Allow the Agent to learn the tool's rules without human training.
- **Feature:** `cerberus schema <command>`
- **Output:** Returns strict JSON Schema for the command's *Input Arguments* and *Output Data*.
- **Benefit:** Zero "Hallucination" of flags. The Agent knows exactly what is possible.

### 7. The Batch Protocol (Atomic Efficiency)
**Mission:** Reduce 10 turns of context switching into 1 atomic operation.
- **Architecture:** **Serverless / In-Process**.
    - **Rule:** Batch commands MUST NOT communicate with the Daemon (avoids single-threaded deadlocks/hangs).
    - **Mechanism:**
        1. `cerberus batch` loads the SQLite Index *once* into its own process memory (paying the startup tax once).
        2. It uses `ThreadPoolExecutor` to execute requests in parallel against the local DB.
        3. It aggregates results into a single JSON response.
- **Benefit:** Massive throughput, zero network overhead, and immunity to Daemon hangs.

---

## 📉 Success Metrics
1.  **Token Reduction:** > 90% reduction in output tokens for standard commands (scan, status, search).
2.  **Visual Noise:** 0% decorative characters in Machine Mode.
3.  **Configurability:** Metrics are purely opt-in via flags.

---

## 🔗 Connection to Mission
Phase 10 completes the transition started in Phase 9. While Phase 9 provides the *Speed* (Daemon), Phase 10 provides the *Efficiency* (Protocol), ensuring perfect symbiosis between Agent and Tool.
