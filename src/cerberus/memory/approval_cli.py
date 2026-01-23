"""
Phase 4: CLI Approval Interface

Simple CLI interface for proposal approval.
Uses standard input() only - works in any terminal including Claude Code.

Zero token cost (pure UI).
"""

from dataclasses import dataclass
from typing import List, Set, Union
from datetime import datetime


@dataclass
class ApprovalResult:
    """Result of approval process."""
    approved_ids: List[str]
    rejected_ids: List[str]
    total: int
    approved_count: int
    rejected_count: int
    auto_approved_count: int = 0
    duration_seconds: float = 0.0


class ApprovalCLI:
    """
    CLI interface for memory proposal approval.

    Features:
    - Standard input() only (no keyboard library)
    - Bulk operations (all, none, 1,2,3)
    - Batch mode (auto-approve high confidence >= 0.9)
    - Works in any terminal
    """

    def __init__(self, auto_approve_threshold: float = 0.9):
        """
        Args:
            auto_approve_threshold: Confidence threshold for batch mode auto-approval (default: 0.9)
        """
        self.auto_approve_threshold = auto_approve_threshold

    def run(
        self,
        user_proposals: List,
        agent_proposals: List = None,
        interactive: bool = True,
        optimize: bool = True
    ) -> Union[ApprovalResult, List[str]]:
        """
        Run approval interface for proposals.

        Args:
            user_proposals: List of MemoryProposal from Phase 3
            agent_proposals: Optional list of AgentProposal from Phase 10
            interactive: If False, run in batch mode (auto-approve high confidence)
            optimize: If True, use Phase 18 optimized approval (default: True)

        Returns:
            ApprovalResult (Phase 4) OR List[str] (Phase 18 when called from optimizer)
        """
        start_time = datetime.now()

        # Combine proposals
        all_proposals = list(user_proposals)
        if agent_proposals:
            all_proposals.extend(agent_proposals)

        if not all_proposals:
            return ApprovalResult(
                approved_ids=[],
                rejected_ids=[],
                total=0,
                approved_count=0,
                rejected_count=0,
                duration_seconds=0.0
            )

        # Phase 18: Optimized approval
        if optimize:
            from cerberus.memory.approval_optimizer import (
                run_optimized_approval,
                get_all_approved_ids,
                ApprovalStrategy
            )

            strategy = ApprovalStrategy(
                auto_approve_threshold=self.auto_approve_threshold,
                review_threshold=0.6,
                skip_threshold=0.5,
                batch_similar=True
            )

            result = run_optimized_approval(
                all_proposals,
                strategy=strategy,
                interactive=interactive
            )

            # Convert Phase 18 result to Phase 4 format
            duration = (datetime.now() - start_time).total_seconds()

            return ApprovalResult(
                approved_ids=get_all_approved_ids(result),
                rejected_ids=result.user_rejected,
                total=result.stats.get("total", 0),
                approved_count=result.stats.get("auto", 0) + result.stats.get("approved", 0),
                rejected_count=result.stats.get("rejected", 0),
                auto_approved_count=result.stats.get("auto", 0),
                duration_seconds=duration
            )

        # Phase 4: Legacy approval (fallback)
        # Batch mode: auto-approve high confidence
        if not interactive:
            return self._batch_mode(all_proposals, start_time)

        # Interactive mode
        return self._interactive_mode(all_proposals, start_time)

    def _batch_mode(self, proposals: List, start_time: datetime) -> ApprovalResult:
        """
        Batch mode: auto-approve proposals >= threshold.

        Args:
            proposals: List of proposals
            start_time: Start timestamp

        Returns:
            ApprovalResult
        """
        approved = []
        rejected = []

        for proposal in proposals:
            if proposal.confidence >= self.auto_approve_threshold:
                approved.append(proposal.id)
            else:
                rejected.append(proposal.id)

        duration = (datetime.now() - start_time).total_seconds()

        return ApprovalResult(
            approved_ids=approved,
            rejected_ids=rejected,
            total=len(proposals),
            approved_count=len(approved),
            rejected_count=len(rejected),
            auto_approved_count=len(approved),
            duration_seconds=duration
        )

    def _interactive_mode(self, proposals: List, start_time: datetime) -> ApprovalResult:
        """
        Interactive mode: display proposals and get user input.

        Args:
            proposals: List of proposals
            start_time: Start timestamp

        Returns:
            ApprovalResult
        """
        print("\n" + "=" * 70)
        print("CERBERUS MEMORY PROPOSALS")
        print("=" * 70)
        print(f"\nFound {len(proposals)} proposal(s) to review.\n")

        # Display all proposals
        for i, proposal in enumerate(proposals, 1):
            self._display_proposal(i, proposal)

        print("=" * 70)
        print("\nApproval Options:")
        print("  all       - Approve all proposals")
        print("  none      - Reject all proposals")
        print("  1,2,3     - Approve specific proposals by number")
        print("  q/quit    - Quit without saving anything")
        print("=" * 70)

        # Get user input
        approved_indices = self._get_user_selection(len(proposals))

        # Process results
        approved = []
        rejected = []

        if approved_indices is None:
            # User quit - reject all
            rejected = [p.id for p in proposals]
        else:
            for i, proposal in enumerate(proposals):
                if i in approved_indices:
                    approved.append(proposal.id)
                else:
                    rejected.append(proposal.id)

        duration = (datetime.now() - start_time).total_seconds()

        # Display summary
        print(f"\nApproved: {len(approved)}/{len(proposals)}")
        print(f"Rejected: {len(rejected)}/{len(proposals)}")
        print(f"Duration: {duration:.1f}s")

        return ApprovalResult(
            approved_ids=approved,
            rejected_ids=rejected,
            total=len(proposals),
            approved_count=len(approved),
            rejected_count=len(rejected),
            duration_seconds=duration
        )

    def _display_proposal(self, index: int, proposal) -> None:
        """
        Display a single proposal.

        Args:
            index: Proposal number (1-indexed)
            proposal: MemoryProposal or AgentProposal
        """
        print(f"\n[{index}] {proposal.content}")
        print(f"    Scope:      {proposal.scope}")
        print(f"    Category:   {proposal.category}")
        print(f"    Confidence: {proposal.confidence:.0%}")
        print(f"    Rationale:  {proposal.rationale}")

        # Show source variants if available (MemoryProposal only)
        if hasattr(proposal, 'source_variants') and proposal.source_variants:
            if len(proposal.source_variants) <= 3:
                print(f"    Variants:   {', '.join(proposal.source_variants)}")
            else:
                print(f"    Variants:   {len(proposal.source_variants)} variations")

    def _get_user_selection(self, total: int) -> Union[Set[int], None]:
        """
        Get user selection via input().

        Args:
            total: Total number of proposals

        Returns:
            Set of 0-indexed proposal indices, or None if user quit
        """
        while True:
            try:
                user_input = input("\nYour choice: ").strip().lower()

                # Quit
                if user_input in ['q', 'quit', 'exit']:
                    print("\nQuitting without saving...")
                    return None

                # All
                if user_input == 'all':
                    return set(range(total))

                # None
                if user_input == 'none':
                    return set()

                # Specific numbers (1,2,3 or 1 2 3)
                if user_input:
                    # Parse comma or space separated numbers
                    user_input = user_input.replace(',', ' ')
                    numbers = user_input.split()

                    indices = set()
                    for num_str in numbers:
                        try:
                            num = int(num_str)
                            if 1 <= num <= total:
                                indices.add(num - 1)  # Convert to 0-indexed
                            else:
                                print(f"Invalid number: {num}. Must be between 1 and {total}.")
                                break
                        except ValueError:
                            print(f"Invalid input: '{num_str}'. Must be a number.")
                            break
                    else:
                        # All numbers parsed successfully
                        return indices

                # Invalid input
                print("Invalid input. Use 'all', 'none', '1,2,3', or 'q' to quit.")

            except KeyboardInterrupt:
                print("\n\nInterrupted. Quitting without saving...")
                return None
            except EOFError:
                print("\n\nEOF detected. Quitting without saving...")
                return None


def approve_proposals(
    user_proposals: List,
    agent_proposals: List = None,
    interactive: bool = True,
    auto_approve_threshold: float = 0.9,
    optimize: bool = True
) -> ApprovalResult:
    """
    Convenience function for proposal approval.

    Args:
        user_proposals: List of MemoryProposal from Phase 3
        agent_proposals: Optional list of AgentProposal from Phase 10
        interactive: If False, run in batch mode
        auto_approve_threshold: Confidence threshold for batch mode
        optimize: If True, use Phase 18 optimized approval (default: True)

    Returns:
        ApprovalResult with approved/rejected IDs
    """
    cli = ApprovalCLI(auto_approve_threshold=auto_approve_threshold)
    return cli.run(user_proposals, agent_proposals, interactive, optimize)


def create_test_scenarios():
    """
    Create test scenarios for validation.

    Returns:
        List of test scenario dictionaries
    """
    return [
        {
            "name": "All approved",
            "proposals_count": 5,
            "input": "all",
            "expected_approved": 5,
            "expected_rejected": 0
        },
        {
            "name": "None approved",
            "proposals_count": 5,
            "input": "none",
            "expected_approved": 0,
            "expected_rejected": 5
        },
        {
            "name": "Specific approved (comma)",
            "proposals_count": 5,
            "input": "1,3,5",
            "expected_approved": 3,
            "expected_rejected": 2
        },
        {
            "name": "Specific approved (space)",
            "proposals_count": 5,
            "input": "2 4",
            "expected_approved": 2,
            "expected_rejected": 3
        },
        {
            "name": "Batch mode high confidence",
            "proposals_count": 5,
            "confidences": [0.95, 0.85, 0.92, 0.88, 0.91],
            "threshold": 0.9,
            "batch_mode": True,
            "expected_approved": 3,  # 0.95, 0.92, 0.91
            "expected_rejected": 2   # 0.85, 0.88
        },
        {
            "name": "Quit without saving",
            "proposals_count": 3,
            "input": "q",
            "expected_approved": 0,
            "expected_rejected": 3  # All rejected on quit
        }
    ]
