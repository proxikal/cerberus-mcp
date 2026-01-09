# Phase 9 Specification: The Cerberus Daemon (Cognitive Cortex)

**Status:** Active Design
**Goal:** Transition Cerberus from a "Passive Tool" (CLI) to an "Active Cortex" (Daemon/Server) to eliminate the "Startup Tax," offload memory state from the Agent, and provide millisecond-latency intelligence through a natural, agent-native protocol.

---

## 🤖 AI-Agent Symbiosis & CERBERUS.md Update
**Mission:** Formalize the transition from "Tool" to "Cortex."
- **CERBERUS.md Alignment:** The agent MUST ensure that `CERBERUS.md` is updated to reflect the Phase 9 reality.
- **Symbiosis Rules:** All interaction protocols must shift from "Agent uses Cerberus" to "Agent *is* Cerberus-integrated."
- **Strict Dogfooding:** The updated `CERBERUS.md` must enforce a **100% Cerberus-only exploration policy**. Any deviation (using `cat`, `grep`, etc.) without a documented "Gap Report" to the user is considered a protocol failure.

---

## 🚨 The Problem Analysis

### 1. "Context Bloat" & System Heat
**Observation:** The Agent Process (e.g., Claude) accumulates massive memory usage (600MB+) and generates heat.
**Root Cause:**
- **State Duplication:** The Agent loads code into its context window (RAM) to understand it.
- **Stateless Tooling:** The CLI dies after every command. The Agent *must* hold the state because the tool doesn't.

### 2. The "Startup Tax" (Performance Bottleneck)
**Benchmark Discovery:**
- **Native `grep`:** 0.052s
- **Cerberus CLI:** 3.119s (~60x slower)
**Analysis:** 99% of Cerberus execution time is **Python Startup + Library Loading**. The actual search is microseconds.
**Implication:** To match native tool speed, the Python process **must remain resident**.

### 3. The "Unnatural" Interface (Token Friction)
**Observation:** Agents currently parse ASCII tables and Markdown formatting intended for human eyes.
**Impact:** Wasted tokens, slower processing, and "formatting friction" that prevents the agent from "feeling" the code naturally.

---

## 🎯 The Phase 9 Solution: "Headless Intelligence"

### 1. Architecture: The Cortex Daemon (`cerberus serve`)
**Mission:** A persistent background process that holds the Project Graph in RAM/SQLite.
- **Description:** A lightweight HTTP/JSON-RPC server (FastAPI or Unix Socket).
- **Mechanism:**
    - **One-Time Boot:** Pays the 3-second startup tax *once*.
    - **Hot State:** Keeps SQLite connections and Indices open/cached.
    - **Unified Watcher:** Absorbs the Phase 3 `watcher` logic to update the graph in real-time.
- **Benefit:** Queries become instant (< 50ms) because the engine is already warm.

### 2. The Thin Client (`cerberus`)
**Mission:** A lightweight wrapper that talks to the Daemon.
- **Shift:** The `cerberus` command becomes a thin client.
- **Logic:**
    - **Check:** Is Daemon running?
    - **If Yes:** Send JSON-RPC request -> Print Response. (Time: ~10ms)
    - **If No:** Auto-spawn Daemon -> Send Request.
- **Impact:** Eliminates the 3-second boot time for user interactions.

### 3. The Cognitive Protocol (JSON-RPC)
**Mission:** Standardize Agent-Cerberus communication as *strict, unformatted data*.
- **Shift:** Return **JSON Objects**, never **Markdown Tables**.
- **Rule:** "Raw Data for Agents; Pretty Print only for Humans (client-side rendering)."
- **Example:**
    - *Request:* `get_definition("MyClass")`
    - *Response:* `{"symbol": "MyClass", "file": "src/main.py", "line": 42, "doc": "...", "complexity": 5}`
- **Agent Benefit:** Data maps directly to internal cognitive structures. Zero parsing overhead.

### 4. Stateful "Keep-Alive" Sessions
**Mission:** Eliminate redundant context transmission.
- **Description:** The Daemon maintains a `session_id` for the active agent.
- **Mechanism:**
    - Tracks a "Seen Set" of symbols sent to the agent.
    - If Agent requests `User` class again:
    - *Daemon:* `{"ref": "User", "status": "unchanged", "hash": "abc1234"}`
- **Benefit:** Prevents "Session Amnesia" and stops context bloat. The Agent works with "Pointers" rather than reloading "Data."

### 5. Proactive "Proprioception" (Notifications)
**Mission:** Give the Agent a "Sixth Sense" for codebase changes.
- **Shift:** From "Polling" to "Pushing."
- **Mechanism:**
    - Daemon watches the graph for impact analysis.
    - *Event:* `User.py` modified.
    - *Notification:* `{"event": "reference_break", "source": "User.py", "impacted": ["Auth.py", "Admin.py"], "severity": "high"}`
- **Benefit:** The Agent "feels" the breakage instantly, rather than discovering it 5 minutes later during tests.

### 6. Active Resource Monitoring ("The Thermostat")
**Mission:** Cerberus protects the Host System.
- **Feature:** `cerberus system-check`
- **Logic:**
    - Daemon monitors Agent Process (PID) memory/CPU.
    - **Trigger:** If Agent Memory > 2GB or CPU > 80%.
    - **Action:** Daemon sends a "High Load Warning" to the Agent, advising a Context Prune/Restart.

### 7. "Shadow Workspace" (Sandboxed Execution)
**Mission:** Safe, isolated execution of code changes.
- **Description:** Daemon maintains a "Shadow" copy of the codebase for dry-runs.
- **Workflow:**
    1. Agent requests change.
    2. Daemon applies to Shadow.
    3. Daemon runs tests on Shadow.
    4. **Success:** Daemon syncs to Real File System.
    5. **Failure:** Daemon reports error; Real File System untouched.
- **Benefit:** Prevents "Broken State" loops that cause Agents to spin and overheat.

### 8. Daemon Resource Governance (The "Tiered Intelligence" Architecture)
**Mission:** Enable massive scalability (10,000+ files) without "Cache Thrashing" or RAM bloat. The Daemon manages memory using a strict Tiered Strategy.

#### Tier 1: The "Skeleton Index" (Always in RAM)
- **Content:** File Paths + Top-Level Symbol Names (Classes/Functions) + Signatures.
- **Cost:** Extremely Low (~5MB for 10k files).
- **Function:** Instantly answers navigation queries ("Where is X?", "List files in Y") without disk I/O.
- **Policy:** **NEVER Evicted.** Always available for 0-latency routing.

#### Tier 2: The "Hot Working Set" (LRU Cache in RAM)
- **Content:** Full ASTs, resolved types, and import graphs for *active* files.
- **Cost:** Medium (~1MB per 20 active files).
- **Function:** Provides instant "Get Definition" and "Type Resolution" for the code the Agent is actively reading/editing.
- **Policy:** **LRU Eviction.** Size is dynamic based on available RAM (default limit: 256MB).
    - **Pinning:** Files modified in the last hour are pinned.
    - **Predictive Prefetching:** When `A.py` is accessed, its direct imports (`B.py`, `C.py`) are quietly pre-loaded.

#### Tier 3: The "Cold Storage" (SQLite on SSD)
- **Content:** Full ASTs, docstrings, vector embeddings, and historical diffs for the entire repository.
- **Cost:** **0 Bytes RAM.**
- **Function:** The "Encyclopedia." Used for deep searches ("Find references in legacy modules") and hydration of Tier 2.
- **Policy:** **Single Source of Truth.** SQLite FTS5 provides microsecond access, ensuring the system remains fast even when RAM is full.

### 9. Security & Multi-Agent Swarm (Safety Protocol)
**Mission:** Ensure Cerberus is secure by default and ready for multi-agent collaboration.
- **Localhost Lock:**
    - The Daemon binds **ONLY** to a Unix Domain Socket (Mac/Linux) or Named Pipe (Windows).
    - **No TCP/IP.** Prevents accidental network exposure.
    - **Benefit:** Physical security isolation.
- **Immutability Guard:**
    - Default State: **Read-Only**.
    - Write operations require an explicit `--allow-write` flag or a cryptographic session token.
    - **Benefit:** Prevents hallucinating agents from deleting project files.
- **Swarm Intelligence:**
    - **AsyncIO Core:** The Daemon uses `asyncio` to handle multiple concurrent connections.
    - **Agent Namespaces:** Support for `cerberus serve --max-agents 5`.
    - **Benefit:** Allows Claude (Frontend) and Gemini (Backend) to query the same Cortex simultaneously without blocking each other.

**Result:** A 100,000-file codebase feels as light as a 10-file script. The Agent "surfs" on top of the massive archive.

---

## 🔄 Integration Plan

### Superseding Phase 3 Watcher
- **Current:** `cerberus watcher` is a standalone script (Read-Only).
- **New:** `cerberus serve` **is** the Watcher + The Server.
- **Migration:**
    - Refactor `src/cerberus/watcher/filesystem_monitor.py` into `src/cerberus/daemon/monitor.py`.
    - Ensure `cerberus serve` starts the monitor thread on boot.

---

## 📉 Success Metrics
1.  **Latency:** Symbol lookup < **0.05s** (matching native `grep`).
2.  **Agent Memory:** Stable < 500MB (by offloading context).
3.  **System Heat:** CPU idle during "thinking" (no repeated index loading).
4.  **Autonomy:** Agent relies on Daemon for "Memory," not its own context window.

---

## 🔗 Connection to Mission
This fulfills the **"AI Symbiosis"** mandate by making Cerberus the **runtime OS** for the Agent, not just a CLI tool.
