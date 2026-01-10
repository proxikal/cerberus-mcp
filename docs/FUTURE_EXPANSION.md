# Phase 12 Specification: Future Expansion (Post-Core)

**Status:** Proposed / Long-Term
**Priority:** LOW
**Goal:** This phase consolidates all non-critical, future enhancements that extend Cerberus beyond its core "AI Operating System" mandate. These features are designed for human observability, enterprise compliance, and multi-language parity.

---

## 1. Visual Intelligence (The Human Interface)
*Formerly Phase 12*

**Mission:** Provide a human-readable visualization layer on top of the machine-first Cerberus engine.
- **Local Dashboard (`cerberus ui`):** A lightweight web server for interactive Call Graphs and Vector Space visualization.
- **VS Code Extension:** Native IDE integration for "Ghost Text" context and an in-editor Agent Sidebar.
- **Documentation Logic (`cerberus graph`):** Export Mermaid.js diagrams, SVGs, and PNGs for automated technical documentation.

## 2. Enhanced Security & Compliance (Enterprise)
*Formerly Phase 13*

**Mission:** Ensure Cerberus is safe for use in highly regulated enterprise environments.
- **Security Scanning:** Automated detection of PII (Personally Identifiable Information) and hardcoded secrets (API Keys) during the indexing pipeline.
- **Compliance Reporting:** Generate audit reports detailing which files contain sensitive patterns.
- **Safe Context Assembly:** Automatically redact detected sensitive data from the context sent to AI Agents.

## 3. Multi-Language Expansion (Parity)
*Formerly Phase 14*

**Mission:** Bring other languages to the same level of "Symbolic Intelligence" as Python.
- **Full TypeScript Support:** Complete AST skeletonization, advanced parsing, and type inference.
- **Rust Support:** Native parsing, trait resolution, and type inference.
- **Java/Go Support:** Class hierarchies, interface resolution, and package management integration.
- **Generic Language Protocol:** A plugin system allowing community contributions for new languages.

## 4. Documentation Symbiosis (Complete Dogfooding)
*Deferred from Phase 14*

**Mission:** Close the final dogfooding gap by treating documentation as structured data, not plain text.
- **Documentation Indexing:** Extract markdown headers as "symbols", parse code blocks, track internal links as dependencies
- **Section-Based Reading:** `cerberus docs read CERBERUS.md --section "ENFORCEMENT"` for semantic access (40-60% token savings vs line-based)
- **Semantic Search:** `cerberus docs search "batch-edit"` across all documentation
- **Table of Contents:** `cerberus docs toc` for hierarchical header navigation
- **Cross-Reference Tracking:** Link resolution and dependency graphs between documentation files

**Rationale for Deferral:**
- Current `Read` tool exception for `.md` files works adequately
- Higher ROI features (Style Guard, Context Anchors, Predictive Editing) provide immediate agent productivity gains
- Documentation parsing complexity (markdown flavors, edge cases) requires significant maintenance
- Can revisit with intelligence layer (staleness detection, code-doc bidirectional linking) for greater value

**Implementation Notes (When Resumed):**
- Keep scope minimal: section extraction + semantic search only
- Skip advanced features: format conversion, linting, blueprint visualization
- Use CommonMark spec exclusively to avoid markdown flavor complexity
- Store doc symbols in separate database table to avoid code index pollution

---

## 🔗 Connection to Mission
These expansions represent the "Maturation" of Cerberus. Once the core "Read-Think-Write" loop is perfected (Phases 1-11), these features will help Cerberus scale to larger teams, stricter environments, and more diverse codebases.
