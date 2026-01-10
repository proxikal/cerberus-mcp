"""
JIT Guidance (Whisper Protocol): Context-aware workflow hints.

Phase 12.5: Proactive teaching of next steps to eliminate syntax hallucination
across all AI models (Claude, Gemini, Codex).
"""

from typing import Optional, List, Dict, Any


class GuidanceProvider:
    """
    Provides context-aware guidance for AI agents.

    Phase 12.5: The "Whisper" Protocol - guides agents through workflows
    by suggesting next logical steps based on current command output.
    """

    # Workflow guidance mappings
    GUIDANCE_MAP = {
        # Search/Discovery commands
        "search": [
            "To view file structure: cerberus retrieval blueprint <file>",
            "To get symbol details: cerberus retrieval get-symbol <name>",
            "To see dependencies: cerberus symbolic deps <symbol>"
        ],
        "get-symbol": [
            "To edit this symbol: cerberus mutations edit <file> --symbol <name> --code '...'",
            "To see references: cerberus symbolic references --target <name>",
            "To view full file: cerberus dogfood read <file>"
        ],
        "blueprint": [
            "To edit a symbol: cerberus mutations edit <file> --symbol <name> --code '...'",
            "To see symbol deps: cerberus symbolic deps <symbol>",
            "To search within: cerberus retrieval search '<query>'"
        ],
        "read": [
            "To modify a symbol: cerberus mutations edit <file> --symbol <name> --code '...'",
            "To see structure: cerberus retrieval blueprint <file>",
            "To find symbol: cerberus retrieval get-symbol <name> --file <file>"
        ],
        "deps": [
            "To view definition: cerberus retrieval get-symbol <name>",
            "To see call graph: cerberus symbolic call-graph <symbol>",
            "To trace execution: cerberus symbolic trace-path <from> <to>"
        ],
        "references": [
            "To view source: cerberus retrieval get-symbol <name>",
            "To check safety: cerberus mutations delete <file> --symbol <name> (blocked if referenced)",
            "To see full graph: cerberus symbolic call-graph <symbol>"
        ],

        # Mutation commands
        "edit": [
            "To preview first: add --dry-run flag",
            "To undo later: cerberus mutations undo",
            "To verify changes: cerberus mutations batch-edit <ops> --verify 'pytest'"
        ],
        "delete": [
            "Note: Protected by Symbol Guard (blocks if referenced)",
            "To force delete: add --force flag",
            "To undo: cerberus mutations undo"
        ],
        "batch-edit": [
            "To preview first: add --preview flag",
            "To auto-verify: add --verify 'pytest tests/'",
            "To undo: cerberus mutations undo"
        ],
        "undo": [
            "To see history: cerberus mutations undo --list",
            "To keep N recent: cerberus mutations undo --clear --keep-last N"
        ],

        # Symbolic commands
        "call-graph": [
            "To see deps only: cerberus symbolic deps <symbol>",
            "To trace path: cerberus symbolic trace-path <from> <to>"
        ],
        "trace-path": [
            "To see full graph: cerberus symbolic call-graph <symbol>",
            "To view code: cerberus retrieval get-symbol <name>"
        ]
    }

    @classmethod
    def get_tip(cls, command: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Get a contextual tip for a command.

        Args:
            command: Command name (e.g., "search", "get-symbol")
            context: Optional context dictionary for smart tip selection

        Returns:
            Tip string or None
        """
        tips = cls.GUIDANCE_MAP.get(command)

        if not tips:
            return None

        # For now, return first tip. Could be enhanced with context-aware selection
        if context and "preferred_tip" in context:
            tip_index = context["preferred_tip"]
            if 0 <= tip_index < len(tips):
                return tips[tip_index]

        return tips[0] if tips else None

    @classmethod
    def get_all_tips(cls, command: str) -> List[str]:
        """
        Get all tips for a command.

        Args:
            command: Command name

        Returns:
            List of tip strings
        """
        return cls.GUIDANCE_MAP.get(command, [])

    @classmethod
    def format_tip(cls, tip: str, style: str = "footer") -> str:
        """
        Format a tip for display.

        Args:
            tip: Tip text
            style: Display style ("footer", "inline", "box")

        Returns:
            Formatted tip string
        """
        if style == "footer":
            return f"\n[Tip] {tip}"
        elif style == "inline":
            return f"[Tip] {tip}"
        elif style == "box":
            separator = "─" * (len(tip) + 8)
            return f"\n┌{separator}┐\n│ 💡 Tip: {tip} │\n└{separator}┘"
        else:
            return tip

    @classmethod
    def should_show_guidance(cls, is_machine_mode: bool, suppress_guidance: bool = False) -> bool:
        """
        Determine if guidance should be shown.

        Args:
            is_machine_mode: Whether in machine mode
            suppress_guidance: Whether guidance is explicitly suppressed

        Returns:
            True if guidance should be shown
        """
        # Don't show in machine mode or if suppressed
        return not is_machine_mode and not suppress_guidance
