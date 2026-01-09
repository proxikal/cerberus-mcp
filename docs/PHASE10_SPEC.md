# Phase 10 Specification: The Silent Protocol (Industrial Optimization)

**Status:** Proposed (To Follow Phase 9)
**Goal:** Eliminate "Presentation Bloat." Transform Cerberus from a Human-Centric CLI to an Agent-Native Protocol by removing decorative tokens (ASCII, emojis, whitespace) and enforcing strict efficiency metrics.

---

## 🎯 Core Objectives

### 1. The Global `--machine` Protocol
**Mission:** Ensure 100% Signal / 0% Noise.
- **Problem:** Current commands output Markdown tables, emojis ("🌟"), and whitespace for human readability. This wastes tokens.
- **Solution:**
    - Implement a global `CERBERUS_MACHINE_MODE` environment variable (and `--machine` flag).
    - When active, ALL commands bypass `rich.console` and return raw, minified text or JSON.
- **Example:**
    - *Human:* `| Symbol | Type | ...` (100 tokens)
    - *Machine:* `User:Class:src/user.py` (5 tokens)

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

---

## 📉 Success Metrics
1.  **Token Reduction:** > 90% reduction in output tokens for standard commands (scan, status, search).
2.  **Visual Noise:** 0% decorative characters in Machine Mode.
3.  **Configurability:** Metrics are purely opt-in via flags.

---

## 🔗 Connection to Mission
Phase 10 completes the transition started in Phase 9. While Phase 9 provides the *Speed* (Daemon), Phase 10 provides the *Efficiency* (Protocol), ensuring perfect symbiosis between Agent and Tool.
