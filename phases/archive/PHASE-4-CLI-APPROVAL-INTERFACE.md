# PHASE 4: APPROVAL INTERFACE

**Rollout Phase:** Alpha (Weeks 1-2)
**Status:** Implement after Phase 3

## Prerequisites

- ✅ Phase 3 complete (proposals generated)

---

## Objective
Simple CLI interface for proposal approval. No special dependencies, works everywhere.

---

## Implementation Location

**File:** `src/cerberus/memory/approval_cli.py`

---

## Requirements

**Critical Constraints:**
- No special dependencies (keyboard, curses, etc.)
- Works in any terminal (including Claude Code)
- Uses standard `input()` for all interaction
- Fast and simple

---

## Data Structures

```python
@dataclass
class ProposalView:
    """Single proposal display state."""
    proposal: Union[MemoryProposal, AgentProposal]
    index: int
    approved: bool
    source: str  # "user" or "agent"
```

---

## CLI Approval Interface

**Library:** `rich` (for formatting only, optional)

```python
from typing import List, Union, Optional

class ApprovalCLI:
    """
    Simple CLI for proposal approval.
    Uses input() only, no keyboard library.
    """

    def run(
        self,
        user_proposals: List[MemoryProposal],
        agent_proposals: List[AgentProposal]
    ) -> List[str]:
        """
        Run CLI approval, return list of approved proposal IDs.
        """
        all_proposals = user_proposals + agent_proposals

        if not all_proposals:
            return []

        # Display header
        print(f"\n{'='*60}")
        print(f"SESSION LEARNING PROPOSALS")
        print(f"{'='*60}")
        print(f"User corrections: {len(user_proposals)}")
        print(f"Agent patterns: {len(agent_proposals)}")
        print(f"Total: {len(all_proposals)}\n")

        # Display all proposals
        for i, prop in enumerate(all_proposals, 1):
            source = "USER" if i <= len(user_proposals) else "AGENT"
            print(f"[{i}] ({source}) {prop.content}")
            if hasattr(prop, "rationale") and prop.rationale:
                print(f"    Why: {prop.rationale}")
            if hasattr(prop, "evidence") and prop.evidence:
                print(f"    Evidence: {prop.evidence[0]}")
            print()

        # Get approval input
        return self._get_approval_input(all_proposals)

    def _get_approval_input(self, proposals: List) -> List[str]:
        """
        Get approval input from user.
        Returns list of approved proposal IDs.
        """
        print("Commands:")
        print("  all     - Approve all proposals")
        print("  none    - Reject all proposals")
        print("  1,2,3   - Approve specific proposals by number")
        print("  q       - Quit without saving")
        print()

        while True:
            response = input("Approve: ").strip().lower()

            if response == "all":
                print(f"✓ Approved all {len(proposals)} proposals")
                return [p.id for p in proposals]

            elif response == "none":
                print("✓ No proposals approved")
                return []

            elif response == "q":
                print("✓ Cancelled, no proposals saved")
                return []

            elif response:
                # Parse indices
                try:
                    indices = [int(x.strip()) for x in response.split(",")]
                    valid_ids = []
                    for i in indices:
                        if 0 < i <= len(proposals):
                            valid_ids.append(proposals[i-1].id)
                        else:
                            print(f"  Warning: {i} out of range, skipping")

                    if valid_ids:
                        print(f"✓ Approved {len(valid_ids)} proposals")
                        return valid_ids
                    else:
                        print("  No valid indices, try again")
                except ValueError:
                    print("  Invalid input. Use 'all', 'none', 'q', or numbers like '1,2,3'")
```

---

## Batch Mode (No Interaction)

```python
class BatchApproval:
    """
    Non-interactive approval for automation.
    """

    def auto_approve_high_confidence(
        self,
        proposals: List[Union[MemoryProposal, AgentProposal]],
        threshold: float = 0.9
    ) -> List[str]:
        """
        Auto-approve proposals with confidence >= threshold.
        """
        approved = []
        for prop in proposals:
            if hasattr(prop, "confidence") and prop.confidence >= threshold:
                approved.append(prop.id)
        return approved

    def auto_approve_all(
        self,
        proposals: List[Union[MemoryProposal, AgentProposal]]
    ) -> List[str]:
        """
        Auto-approve all proposals.
        """
        return [p.id for p in proposals]
```

---

## Integration with Phase 3

```python
def on_session_end(interactive: bool = True, auto_approve_threshold: float = 0.9):
    """
    End of session approval flow.

    Args:
        interactive: If True, show CLI for user approval. If False, auto-approve.
        auto_approve_threshold: Confidence threshold for auto-approval (0.0-1.0, default 0.9)
    """
    # Generate proposals (Phase 3)
    user_proposals = generate_user_proposals()
    agent_proposals = generate_agent_proposals()

    all_proposals = user_proposals + agent_proposals

    if not all_proposals:
        print("No proposals generated")
        return

    # Approval
    if interactive:
        cli = ApprovalCLI()
        approved_ids = cli.run(user_proposals, agent_proposals)
    else:
        # Non-interactive: auto-approve high confidence
        batch = BatchApproval()
        approved_ids = batch.auto_approve_high_confidence(
            all_proposals,
            threshold=auto_approve_threshold
        )

    # Storage (Phase 5)
    if approved_ids:
        store_approved_proposals(approved_ids)
```

---

## MCP Tool Integration

```python
def memory_approve(proposal_ids: Optional[List[str]] = None) -> Dict:
    """
    MCP tool for proposal approval.
    If proposal_ids provided, approve those.
    If None, show pending proposals and prompt.
    """
    pending = get_pending_proposals()

    if not pending:
        return {"status": "no_pending", "message": "No pending proposals"}

    if proposal_ids is None:
        # Show proposals, let skill handle interaction
        return {
            "status": "pending",
            "proposals": [
                {
                    "id": p.id,
                    "content": p.content,
                    "category": p.category,
                    "confidence": getattr(p, "confidence", 1.0),
                    "source": "user" if isinstance(p, MemoryProposal) else "agent"
                }
                for p in pending
            ]
        }
    else:
        # Approve specified proposals
        approved = approve_proposals(proposal_ids)
        return {
            "status": "approved",
            "count": len(approved),
            "approved_ids": approved
        }
```

---

## Token Budget Impact

**CLI itself: 0 tokens** (pure UI, no LLM)

**Benefit:** Fast approval = more proposals reviewed = better learning

With $0.10 budget, can now generate:
- User proposals: 10 (was 5) = 2000 tokens
- Agent proposals: 10 (was 5) = 2000 tokens
- Total: 20 proposals, fast CLI approval

---

## Exit Criteria

```
✓ ApprovalCLI class implemented
✓ Uses standard input() only
✓ No special dependencies
✓ Batch mode for automation
✓ MCP tool integration
✓ Works in any terminal
✓ Integration with Phase 3 complete
✓ Tests: 5 interaction scenarios
```

---

## Test Scenarios

```python
# Scenario 1: Approve all
proposals: 10 total
input: "all"
→ expect: all 10 approved

# Scenario 2: Approve none
proposals: 8 total
input: "none"
→ expect: 0 approved

# Scenario 3: Selective approval
proposals: 5 total
input: "1,3,5"
→ expect: proposals 1, 3, 5 approved

# Scenario 4: Quit without saving
proposals: 10 total
input: "q"
→ expect: 0 saved

# Scenario 5: Invalid then valid
proposals: 5 total
input: "invalid", then "1,2"
→ expect: error message, then proposals 1, 2 approved
```

---

## Dependencies

```bash
pip install rich  # Optional, for formatting
```

No keyboard library. No curses. No root privileges.

---

## Performance

- Display: < 50ms
- Input response: instant (standard input)
- Total approval time: 5-30 seconds
