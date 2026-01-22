# PHASE 4: TUI APPROVAL INTERFACE

## Objective
Inline TUI for instant proposal approval. Arrow keys, no typing, same terminal session.

---

## Implementation Location

**File:** `src/cerberus/memory/approval_tui.py`

---

## Requirements

**Critical Constraints:**
- Lives in same terminal session (not separate window)
- Inline rendering (clears and redraws in place)
- Arrow key navigation (no typing unless editing)
- Fast (<1 second to render, instant response)
- Graceful fallback to CLI if TUI unavailable

---

## Data Structures

```python
@dataclass
class ProposalView:
    """Single proposal display state."""
    proposal: Union[MemoryProposal, AgentProposal]
    index: int
    selected: bool
    approved: bool
    source: str  # "user" or "agent"

@dataclass
class TUIState:
    """TUI application state."""
    proposals: List[ProposalView]
    current_index: int
    scroll_offset: int
    mode: str  # "review", "confirm", "done"
    approved_count: int
```

---

## TUI Framework

**Library:** `rich` (already lightweight, no curses complexity)

```python
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
import keyboard  # For arrow key detection

class ApprovalTUI:
    """
    Inline TUI for proposal approval.
    """

    def __init__(self):
        self.console = Console()
        self.state: Optional[TUIState] = None

    def run(
        self,
        user_proposals: List[MemoryProposal],
        agent_proposals: List[AgentProposal]
    ) -> List[str]:
        """
        Run TUI, return list of approved proposal IDs.
        """
        # Convert to views
        views = []
        for i, prop in enumerate(user_proposals):
            views.append(ProposalView(
                proposal=prop,
                index=i,
                selected=False,
                approved=False,
                source="user"
            ))
        for i, prop in enumerate(agent_proposals):
            views.append(ProposalView(
                proposal=prop,
                index=len(user_proposals) + i,
                selected=False,
                approved=False,
                source="agent"
            ))

        # Initialize state
        self.state = TUIState(
            proposals=views,
            current_index=0,
            scroll_offset=0,
            mode="review",
            approved_count=0
        )

        # Run interactive loop
        try:
            return self._interactive_loop()
        except KeyboardInterrupt:
            return []

    def _interactive_loop(self) -> List[str]:
        """
        Main interaction loop with Live rendering.
        """
        with Live(self._render(), console=self.console, refresh_per_second=10) as live:
            while self.state.mode != "done":
                # Wait for key
                key = keyboard.read_event()

                if key.event_type == keyboard.KEY_DOWN:
                    self._handle_key(key.name, live)

        # Return approved IDs
        return [
            view.proposal.id
            for view in self.state.proposals
            if view.approved
        ]

    def _handle_key(self, key: str, live: Live):
        """
        Handle keyboard input.
        """
        if self.state.mode == "review":
            if key == "down":
                self._move_down()
            elif key == "up":
                self._move_up()
            elif key == "space":
                self._toggle_current()
            elif key == "a":
                self._approve_all()
            elif key == "n":
                self._approve_none()
            elif key == "enter":
                self._confirm()
        elif self.state.mode == "confirm":
            if key == "y":
                self.state.mode = "done"
            elif key == "n":
                self.state.mode = "review"

        # Update display
        live.update(self._render())

    def _move_down(self):
        """Move cursor down."""
        if self.state.current_index < len(self.state.proposals) - 1:
            self.state.current_index += 1

            # Scroll if needed (show 10 at a time)
            if self.state.current_index >= self.state.scroll_offset + 10:
                self.state.scroll_offset += 1

    def _move_up(self):
        """Move cursor up."""
        if self.state.current_index > 0:
            self.state.current_index -= 1

            # Scroll if needed
            if self.state.current_index < self.state.scroll_offset:
                self.state.scroll_offset -= 1

    def _toggle_current(self):
        """Toggle approval of current proposal."""
        view = self.state.proposals[self.state.current_index]
        view.approved = not view.approved

        # Update count
        self.state.approved_count = sum(1 for v in self.state.proposals if v.approved)

    def _approve_all(self):
        """Approve all proposals."""
        for view in self.state.proposals:
            view.approved = True
        self.state.approved_count = len(self.state.proposals)

    def _approve_none(self):
        """Approve no proposals."""
        for view in self.state.proposals:
            view.approved = False
        self.state.approved_count = 0

    def _confirm(self):
        """Move to confirmation."""
        self.state.mode = "confirm"

    def _render(self) -> Panel:
        """
        Render current TUI state.
        """
        if self.state.mode == "review":
            return self._render_review()
        elif self.state.mode == "confirm":
            return self._render_confirm()
        else:
            return self._render_done()

    def _render_review(self) -> Panel:
        """
        Render review mode (proposal list).
        """
        # Visible proposals (10 at a time)
        visible = self.state.proposals[
            self.state.scroll_offset:self.state.scroll_offset + 10
        ]

        lines = []
        for view in visible:
            # Format line
            cursor = "→ " if view.index == self.state.current_index else "  "
            check = "[✓]" if view.approved else "[ ]"
            source = "USER" if view.source == "user" else "AGENT"
            content = view.proposal.content[:60]  # Truncate

            line = f"{cursor}{check} [{source}] {content}"
            lines.append(line)

        # Add controls
        lines.append("")
        lines.append("Controls: ↑/↓=move  SPACE=toggle  A=all  N=none  ENTER=confirm")

        # Create panel
        title = f"Session Learning Proposals ({self.state.approved_count}/{len(self.state.proposals)} approved)"
        return Panel(
            "\n".join(lines),
            title=title,
            border_style="green"
        )

    def _render_confirm(self) -> Panel:
        """
        Render confirmation mode.
        """
        lines = [
            f"Approve {self.state.approved_count} proposals?",
            "",
            "Y = Yes, save memories",
            "N = No, go back"
        ]

        return Panel(
            "\n".join(lines),
            title="Confirm",
            border_style="yellow"
        )

    def _render_done(self) -> Panel:
        """
        Render done mode.
        """
        lines = [
            f"✓ Saved {self.state.approved_count} memories"
        ]

        return Panel(
            "\n".join(lines),
            title="Complete",
            border_style="green"
        )
```

---

## Detailed View (On-Demand)

```python
def show_proposal_detail(self, proposal_view: ProposalView):
    """
    Show full proposal details (press 'i' for info).
    Overlays on top of main view.
    """
    prop = proposal_view.proposal

    lines = [
        f"Source: {proposal_view.source.upper()}",
        f"Category: {prop.category}",
        f"Scope: {prop.scope}",
        f"",
        f"Rule: {prop.content}",
        f"",
    ]

    # Add evidence if agent proposal
    if hasattr(prop, "evidence"):
        lines.append("Evidence:")
        for ev in prop.evidence[:3]:
            lines.append(f"  - {ev}")

    # Add rationale if user proposal
    if hasattr(prop, "rationale"):
        lines.append(f"Why: {prop.rationale}")

    self.console.print(Panel(
        "\n".join(lines),
        title=f"Proposal {proposal_view.index + 1}",
        border_style="blue"
    ))

    # Wait for key to close
    keyboard.read_event()
```

---

## Fallback: CLI Mode

```python
class CLIApprovalFallback:
    """
    Fallback to simple CLI if TUI unavailable.
    """

    def run(
        self,
        user_proposals: List[MemoryProposal],
        agent_proposals: List[AgentProposal]
    ) -> List[str]:
        """
        CLI approval interface.
        """
        all_proposals = user_proposals + agent_proposals

        print(f"\n{'='*60}")
        print(f"SESSION LEARNING PROPOSALS")
        print(f"{'='*60}")
        print(f"User corrections: {len(user_proposals)}")
        print(f"Agent patterns: {len(agent_proposals)}")
        print(f"Total: {len(all_proposals)}\n")

        # Show all
        for i, prop in enumerate(all_proposals, 1):
            source = "USER" if i <= len(user_proposals) else "AGENT"
            print(f"[{i}] ({source}) {prop.content}")
            if hasattr(prop, "rationale"):
                print(f"    Why: {prop.rationale}")
            if hasattr(prop, "evidence"):
                print(f"    Evidence: {prop.evidence[0]}")
            print()

        # Get approval
        response = input("Approve: (1,2,3 or 'all' or 'none'): ").strip().lower()

        if response == "all":
            return [p.id for p in all_proposals]
        elif response == "none":
            return []
        else:
            # Parse indices
            try:
                indices = [int(x.strip()) for x in response.split(",")]
                return [
                    all_proposals[i-1].id
                    for i in indices
                    if 0 < i <= len(all_proposals)
                ]
            except:
                print("Invalid input, skipping all.")
                return []
```

---

## Integration with Phase 3

```python
def on_session_end():
    # Generate proposals (Phase 3)
    user_proposals = generate_user_proposals()
    agent_proposals = generate_agent_proposals()

    # TUI approval (Phase 4)
    try:
        tui = ApprovalTUI()
        approved_ids = tui.run(user_proposals, agent_proposals)
    except Exception:
        # Fallback to CLI
        cli = CLIApprovalFallback()
        approved_ids = cli.run(user_proposals, agent_proposals)

    # Storage (Phase 5)
    store_approved_proposals(approved_ids)
```

---

## Enhanced Controls

**Additional keybindings:**
```
i = Show info (detailed view of current proposal)
e = Edit current proposal content (inline edit)
d = Delete current proposal (remove from list)
s = Skip to next source (jump to first agent proposal)
? = Show help overlay
q = Quit without saving
```

---

## Token Budget Impact

**TUI itself: 0 tokens** (pure UI, no LLM)

**Benefit:** Faster approval = more proposals reviewed = better learning

With $0.10 budget, can now generate:
- User proposals: 10 (was 5) = 2000 tokens
- Agent proposals: 10 (was 5) = 2000 tokens
- Total: 20 proposals, fast TUI approval

---

## Exit Criteria

```
✓ ApprovalTUI class implemented
✓ Arrow key navigation working
✓ Space toggle working
✓ Bulk operations (all/none) working
✓ Inline rendering (no flicker)
✓ Detailed view (i key) working
✓ CLI fallback implemented
✓ Integration with Phase 3 complete
✓ Performance: < 1 second render
✓ Tests: 5 interaction scenarios
```

---

## Test Scenarios

```python
# Scenario 1: Basic navigation
proposals: 10 total
actions: down x3, space, down x2, space, enter, y
→ expect: proposals 3 and 5 approved

# Scenario 2: Bulk approve
proposals: 15 total
actions: a, enter, y
→ expect: all 15 approved

# Scenario 3: Bulk reject
proposals: 8 total
actions: n, enter, y
→ expect: 0 approved

# Scenario 4: Detailed view
proposals: 5 total
actions: i, <any key>, space, enter, y
→ expect: showed detail, then approved current

# Scenario 5: Quit without saving
proposals: 10 total
actions: space x5, q
→ expect: 0 saved (quit before confirm)
```

---

## Dependencies

```bash
pip install rich keyboard
```

---

## Performance

- Render: < 50ms (rich is fast)
- Key response: < 10ms (instant)
- Total approval time: 5-30 seconds (vs 30-120 seconds for CLI typing)

---

## UX Impact

**Before (CLI):**
- Type indices: "1,3,5,7,9"
- Error prone (typos)
- Slow (30+ seconds)

**After (TUI):**
- Arrow + space
- Visual feedback
- Fast (5-10 seconds)

**Result:** 6x faster approval, 0 typos, better experience
