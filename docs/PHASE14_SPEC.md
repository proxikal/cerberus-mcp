# Phase 14 Specification: Documentation Symbiosis (Complete Dogfooding)

**Status:** Proposed (To Follow Phase 13)
**Goal:** Close the final dogfooding gap by creating a dedicated `cerberus docs` subsystem for documentation files (`.md`, `.txt`, `.rst`). This enables **100% Cerberus-exclusive workflows** by eliminating the exception clause that currently permits `Read` tool usage on documentation.

---

## 🎯 Core Objectives

### 1. Documentation Indexing
**Mission:** Treat documentation as structured data, not plain text.
- **Indexing Strategy:**
  - Extract markdown headers (`#`, `##`, `###`) as "symbols"
  - Parse code blocks with language tags as references
  - Track internal links (`[link](#section)`) as dependencies
  - Index table of contents, metadata frontmatter
- **Schema Extension:**
  ```python
  class DocSymbol:
      header_level: int        # 1-6 for markdown hierarchy
      heading_text: str        # The actual header content
      section_start: int       # Line number where section begins
      section_end: int         # Line number where section ends
      parent_heading: str      # For nested sections
      code_blocks: List[str]   # Languages used in this section
  ```
- **Benefit:** Documentation becomes navigable like code (jump to sections, search headings)

### 2. `cerberus docs` Command Suite
**Mission:** Mirror the existing `retrieval` and `dogfood` commands for documentation.

**Core Commands:**
```bash
# READ (Section-based, not line-based)
cerberus docs read CERBERUS.md --section "ENFORCEMENT PROTOCOL"
cerberus docs read README.md --lines 1-50

# SEARCH (Semantic search across docs)
cerberus docs search "how to use batch-edit"
cerberus docs search "Phase 12" --type spec  # Search only PHASE*.md files

# STRUCTURE (Table of contents)
cerberus docs toc CERBERUS.md
# Output: Hierarchical list of all headers with line numbers

# NAVIGATION (Smart cross-reference)
cerberus docs references "Phase 12"
# Returns: All .md files that link to Phase 12

# BLUEPRINT (Documentation map)
cerberus docs blueprint docs/
# Output: Visual tree of all docs, headers, and cross-links
```

### 3. Section-Based Reading (Token Efficiency)
**Mission:** Read documentation by semantic sections, not arbitrary line ranges.
- **Smart Extraction:**
  ```bash
  cerberus docs read PHASE12_SPEC.md --section "Core Objectives"
  # Returns: Only the "Core Objectives" section + subsections
  ```
- **Auto-Expansion:**
  - If section has subsections, include them automatically
  - If section references another doc (`See PHASE11_SPEC.md`), show link with preview
- **Benefit:** Agents request "concepts" not "lines", matching how humans think

### 4. Cross-Document Intelligence
**Mission:** Understand documentation as an interconnected knowledge graph.
- **Link Resolution:**
  - Internal links (`#section`) → Resolve to actual content
  - Relative links (`../ROADMAP.md`) → Resolve to absolute paths
  - Phase references (`See Phase 11`) → Auto-link to `PHASE11_SPEC.md`
- **Dependency Tracking:**
  ```bash
  cerberus docs deps PHASE14_SPEC.md
  # Returns: [PHASE13_SPEC.md, CERBERUS.md] (documents it references)
  ```
- **Benefit:** Agents can traverse documentation like a graph, not a file tree

### 5. Validation & Linting
**Mission:** Ensure documentation quality matches code quality.
- **Checks:**
  - Broken internal links (`[link](#nonexistent)`)
  - Orphaned code blocks (no language tag)
  - Outdated phase references (mentions Phase 5 but Phase 12 exists)
  - Inconsistent header hierarchy (skips from `#` to `###`)
- **Command:**
  ```bash
  cerberus docs lint CERBERUS.md
  # Returns: List of issues with line numbers and fixes
  ```
- **Benefit:** Documentation stays synchronized with codebase evolution

### 6. Format Conversion (Optional Enhancement)
**Mission:** Generate documentation in multiple formats from single source.
- **Conversions:**
  - Markdown → Man pages (for `man cerberus-mutations`)
  - Markdown → HTML (for web docs)
  - Spec files → JSON schemas (machine-readable)
- **Command:**
  ```bash
  cerberus docs convert PHASE14_SPEC.md --to html
  ```
- **Benefit:** Single source of truth for all documentation formats

---

## 🏗 Implementation Strategy

### Phase 14.1: Foundation (Week 1-2)
- [ ] Extend `DocumentSymbol` schema in `schemas.py`
- [ ] Create `src/cerberus/parser/markdown_parser.py`
- [ ] Add `.md`, `.txt`, `.rst` support to scanner
- [ ] Basic `cerberus docs read` command (section-based)

### Phase 14.2: Search & Navigation (Week 3)
- [ ] Implement `cerberus docs search` (semantic + keyword)
- [ ] Add `cerberus docs toc` (table of contents)
- [ ] Cross-reference tracking (`docs references`)

### Phase 14.3: Intelligence Layer (Week 4)
- [ ] Smart section extraction with auto-expansion
- [ ] Dependency graph for documentation
- [ ] `cerberus docs blueprint` (visual documentation map)

### Phase 14.4: Quality Tools (Week 5)
- [ ] `cerberus docs lint` for validation
- [ ] Broken link detection
- [ ] Format conversion (markdown → HTML/man)

### Phase 14.5: Integration (Week 6)
- [ ] Update CERBERUS.md to remove exception clause
- [ ] Test suite for documentation commands
- [ ] Performance benchmarks (indexing 100+ .md files)

---

## 📉 Success Metrics

1. **Zero Exceptions:** Remove the documentation exception clause from CERBERUS.md (100% Cerberus dogfooding achieved)
2. **Token Efficiency:** Reading by section uses 40-60% fewer tokens than line-based reads
3. **Cross-Reference Accuracy:** Link resolution works for 100% of internal documentation links
4. **Search Quality:** Semantic search finds relevant docs with >90% precision
5. **Adoption:** All Cerberus development uses `cerberus docs` instead of `Read` tool

---

## 🔗 Connection to Mission

Phase 14 eliminates the final dogfooding exception, achieving **100% Cerberus Symbiosis**. By treating documentation as structured knowledge (headers, sections, links) instead of flat text, we enable Agents to navigate project context with the same precision they use for code. This closes the loop: **Code → Cerberus Commands → Documentation → Cerberus Commands → Complete Agent OS.**

---

## 🚧 Considerations & Risks

**Risks:**
- **Scope Creep:** Documentation parsing is complex (many markdown flavors, edge cases)
- **Index Bloat:** Adding .md files increases database size without code analysis value
- **Maintenance:** New documentation command surface area needs ongoing support

**Mitigations:**
- **Phased Rollout:** Start with basic read/search, add advanced features incrementally
- **Separate Index:** Store doc symbols in separate table/database to avoid code index pollution
- **Standard Compliance:** Use CommonMark spec exclusively (no exotic markdown extensions)

**Alternatives Considered:**
- **Do Nothing:** Keep exception clause (violates dogfooding mission)
- **External Tool:** Use `pandoc` or similar (breaks Cerberus-exclusive mandate)
- **LLM Parsing:** Use AI to extract structure (non-deterministic, breaks AST mandate)

**Decision:** Proceed with native implementation. Proper documentation handling is table stakes for a complete agent OS.
