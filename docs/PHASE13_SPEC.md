# Phase 13 Specification: The Predictive Blueprint (Architectural Intelligence)

**Status:** Proposed (To Follow Phase 12)
**Goal:** Transform the basic `blueprint` command from a simple "Symbol List" into a high-fidelity **Architectural Map**. By layering Dependency Data, Complexity Metrics, and Git Churn onto a **Token-Efficient Visual Structure**, we enable Agents to understand *how* code works without reading the implementation.

---

## 🎯 Core Objectives

### 1. Visual Hierarchy (The Semantic Tree)
**Mission:** Provide an instant "Mental Model" using the most token-efficient format possible.
- **Why Visuals for AI?** LLMs process indentation-based hierarchy (Trees) more efficiently than deeply nested JSON syntax (brackets/quotes).
- **Mandate:** **Strict Visuals Only.**
    - ✅ **Allowed:** Indentation, Tree characters (`├──`, `└──`).
    - ❌ **Forbidden:** Decorative boxes, colors, ambiguous ASCII art (arrows pointing across lines).
- **New Feature:** `cerberus blueprint --visual`
- **Output Standard:**
    ```text
    [File: src/auth_manager.py]
    ├── [Class: AuthConfig] (Lines 10-45)
    │   ├── __init__(env_prefix: str)
    │   └── load_from_env() -> AuthConfig
    └── [Class: SessionManager] (Lines 48-200)
        ├── create_session(user: User) -> str
        └── validate_token(token: str) -> bool
    ```
- **Benefit:** 30-50% token reduction vs JSON.

### 2. Dependency Overlay (`--deps`) (Hybrid Strategy)
**Mission:** Explain *what* a function does using **Inline Annotations**.
- **Strategy:** Do not draw complex arrows. Use structured inline tags.
- **Output:**
    ```text
    └── process_payment() [Calls: Stripe.charge, DB.update] [Raises: PaymentFailed]
    ```
- **Benefit:** **Zero-Token Logic Inspection.** The Agent knows the side effects without spending tokens on the body.

### 3. Complexity & Size Metrics (`--meta`)
**Mission:** Warning signs for "Dragons".
- **Feature:** Annotate symbols with metadata.
- **Output:** `complex_algo() [Lines: 150] [Complexity: High]`
- **Benefit:** Signals the Agent to "Read carefully" or "Refactor this" before touching it.

### 4. Git Churn Intelligence (`--churn`)
**Mission:** Contextual awareness of recent activity.
- **Feature:** Mark symbols modified in the last N commits.
- **Output:** `new_feature() [Modified: 2h ago]`
- **Benefit:** Helps the Agent identify the "Active Work Zone" and potential instability.

### 5. Smart "Auto-Hydration"
**Mission:** Pre-emptive context loading.
- **Logic:** If `cerberus blueprint src/main.py` reveals that `main.py` heavily depends on `src/utils.py`, automatically append a *minified* summary of `src/utils.py` to the output.
- **Benefit:** Eliminates the "Read A -> See Import B -> Read B" exploration loop.

---

## 📉 Success Metrics
1.  **Token Efficiency:** Blueprint output must be < 60% of the token cost of the equivalent raw source code.
2.  **Parsing Accuracy:** LLMs must extract dependencies from the ASCII tree with > 98% accuracy (no hallucinated relationships).
3.  **Symbiosis:** The Visual Tree format matches the LLM's internal representation of code structure.

---

## 🔗 Connection to Mission
Phase 13 fulfills the "High Confidence / Low Token" promise by giving the Agent a **Map** instead of a **Flashlight**. We prioritize **Semantic Clarity** over "Pretty" output.