"""
Phase 15: Mode-Aware Context

Detects user intent mode and filters memory injection based on mode appropriateness.

Modes:
- prototype: Fast iteration, dirty code acceptable, no tests required
- production: Shipping to prod, high quality, tests required
- hotfix: Urgent bug fix, minimal changes, fast action
- refactor: Code cleanup, no new features, maintain behavior
- audit: Review existing code, no modifications
- exploration: Learning codebase, no specific goal

Phase 15A: Mode detection algorithm (keyword-based, 0 tokens)
Phase 15B: Integration with storage and injection
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


# Phase 15A: Mode Definitions
MODES = {
    "prototype": {
        "description": "Fast iteration, dirty code acceptable, no tests required",
        "rigor": "low",
        "indicators": [
            "quick", "hack", "try", "prototype", "poc", "draft",
            "experiment", "see if", "just want to"
        ],
        "scope_indicators": ["single file", "< 100 lines", "temporary"],
        "time_indicators": ["5 min", "quick", "fast"],
    },
    "production": {
        "description": "Shipping to prod, high quality, tests required, docs required",
        "rigor": "high",
        "indicators": [
            "production", "prod", "deploy", "release", "ship", "launch",
            "production-ready", "stable", "customer-facing"
        ],
        "scope_indicators": ["multiple files", "feature", "system"],
        "time_indicators": ["proper", "complete", "thorough"],
    },
    "hotfix": {
        "description": "Urgent bug fix, minimal changes, fast action",
        "rigor": "medium",
        "indicators": [
            "hotfix", "urgent", "critical", "bug", "fix", "broken", "down",
            "asap", "immediately", "emergency"
        ],
        "scope_indicators": ["specific function", "single issue", "targeted"],
        "time_indicators": ["urgent", "now", "asap", "immediately"],
    },
    "refactor": {
        "description": "Code cleanup, no new features, maintain behavior",
        "rigor": "high",
        "indicators": [
            "refactor", "cleanup", "improve", "restructure", "organize",
            "simplify", "optimize", "technical debt"
        ],
        "scope_indicators": ["existing code", "no new features"],
        "time_indicators": ["careful", "thorough"],
    },
    "audit": {
        "description": "Review existing code, no modifications",
        "rigor": "low",
        "indicators": [
            "review", "audit", "analyze", "understand", "explain",
            "how does", "what does", "walk me through"
        ],
        "scope_indicators": ["read-only", "no changes"],
        "time_indicators": [],
    },
    "exploration": {
        "description": "Learning codebase, no specific goal",
        "rigor": "low",
        "indicators": [
            "explore", "find", "search", "locate", "where is",
            "list", "what files"
        ],
        "scope_indicators": ["codebase", "project structure"],
        "time_indicators": [],
    },
}


@dataclass
class IntentMode:
    """Detected user intent mode."""
    mode: str  # "prototype", "production", "hotfix", "refactor", "audit", "exploration"
    confidence: float  # 0.0-1.0
    indicators: List[str]  # Evidence (e.g., ["urgent keyword", "small scope"])
    rigor_level: str  # "low", "medium", "high"


@dataclass
class ModeDetectionResult:
    """Result of mode detection."""
    primary_mode: IntentMode
    secondary_modes: List[IntentMode]  # Fallbacks (confidence > 0.3)
    context: Dict[str, Any]  # Raw context used for detection


class ModeDetector:
    """
    Detects user intent mode from prompt and context.

    Phase 15A: Mode detection algorithm.

    Strategy:
    1. Extract indicators from user prompt (keywords)
    2. Analyze scope (file count, LOC, complexity)
    3. Detect urgency keywords
    4. Score each mode
    5. Return primary + secondary modes

    Token cost: 0 tokens (pure keyword matching + scoring)
    """

    def detect(self, user_prompt: str, context: Optional[Dict[str, Any]] = None) -> ModeDetectionResult:
        """
        Detect mode from prompt and context.

        Args:
            user_prompt: Current user message
            context: Session context (files, tools used, history)
                - modified_files: List of file paths being modified
                - tools_used: List of tool names used in session
                - session_history: Past user messages

        Returns:
            ModeDetectionResult with primary and secondary modes
        """
        if context is None:
            context = {}

        # Step 1: Normalize prompt
        prompt_lower = user_prompt.lower()

        # Step 2: Score each mode
        mode_scores = {}

        for mode_name, mode_config in MODES.items():
            score = 0.0

            # Indicator matching (30% weight)
            for indicator in mode_config["indicators"]:
                if indicator in prompt_lower:
                    score += 0.3

            # Scope matching (30% weight)
            scope_score = self._analyze_scope(prompt_lower, context, mode_config["scope_indicators"])
            score += scope_score * 0.3

            # Time/urgency matching (20% weight)
            time_score = self._analyze_urgency(prompt_lower, mode_config["time_indicators"])
            score += time_score * 0.2

            # Context signals (20% weight)
            context_score = self._analyze_context_signals(context, mode_name)
            score += context_score * 0.2

            mode_scores[mode_name] = min(score, 1.0)

        # Step 3: Rank modes
        ranked = sorted(mode_scores.items(), key=lambda x: x[1], reverse=True)

        # Step 4: Build result
        primary = ranked[0]
        primary_mode = IntentMode(
            mode=primary[0],
            confidence=primary[1],
            indicators=self._extract_matched_indicators(prompt_lower, MODES[primary[0]]),
            rigor_level=MODES[primary[0]]["rigor"]
        )

        # Secondary modes (confidence > 0.3)
        secondary_modes = [
            IntentMode(
                mode=name,
                confidence=score,
                indicators=self._extract_matched_indicators(prompt_lower, MODES[name]),
                rigor_level=MODES[name]["rigor"]
            )
            for name, score in ranked[1:4]
            if score > 0.3
        ]

        return ModeDetectionResult(
            primary_mode=primary_mode,
            secondary_modes=secondary_modes,
            context=context
        )

    def _analyze_scope(self, prompt: str, context: Dict[str, Any], scope_indicators: List[str]) -> float:
        """
        Analyze scope from prompt and context.

        Signals:
        - "single file" vs "multiple files"
        - "< 100 lines" vs "entire system"
        - File count in context
        """
        score = 0.0

        # Prompt indicators
        for indicator in scope_indicators:
            if indicator in prompt:
                score += 0.5

        # Context signals
        file_count = len(context.get("modified_files", []))
        if file_count == 1:
            # Single file = prototype/hotfix more likely
            if "single file" in scope_indicators or "specific function" in scope_indicators:
                score += 0.3
        elif file_count > 5:
            # Multiple files = production/refactor more likely
            if "multiple files" in scope_indicators or "system" in scope_indicators:
                score += 0.3

        return min(score, 1.0)

    def _analyze_urgency(self, prompt: str, time_indicators: List[str]) -> float:
        """
        Analyze urgency/time constraints.

        Signals:
        - "urgent", "asap", "now" = hotfix
        - "quick", "fast" = prototype
        - "proper", "thorough" = production
        """
        score = 0.0

        for indicator in time_indicators:
            if indicator in prompt:
                score += 0.5

        return min(score, 1.0)

    def _analyze_context_signals(self, context: Dict[str, Any], mode: str) -> float:
        """
        Analyze context signals for mode.

        Signals:
        - Tool usage (Write = prototype, Edit = refactor)
        - File patterns (test files = production)
        - Session history (repeated corrections = refactor)
        """
        score = 0.0

        # Tool usage
        tools_used = context.get("tools_used", [])

        if mode == "prototype":
            if "Write" in tools_used:
                score += 0.3
        elif mode == "refactor":
            if "Edit" in tools_used and tools_used.count("Edit") > 3:
                score += 0.3
        elif mode == "production":
            if any("test" in f for f in context.get("modified_files", [])):
                score += 0.3
        elif mode == "audit":
            if "Read" in tools_used and "Edit" not in tools_used and "Write" not in tools_used:
                score += 0.3
        elif mode == "exploration":
            if "Grep" in tools_used or "Glob" in tools_used:
                score += 0.3

        return min(score, 1.0)

    def _extract_matched_indicators(self, prompt: str, mode_config: Dict[str, Any]) -> List[str]:
        """Extract which indicators matched."""
        matched = []
        for indicator in mode_config["indicators"]:
            if indicator in prompt:
                matched.append(indicator)
        return matched[:3]  # Top 3 only


class ModeTagging:
    """
    Auto-tag memories with valid modes.

    Phase 15B: Auto-tagging algorithm for memory storage.

    Rules:
    - "Always write tests" → production, refactor (NOT prototype, hotfix)
    - "Keep it short" → prototype, hotfix, exploration (ALL modes)
    - "Document public APIs" → production, refactor (NOT prototype)
    - "Use X pattern" → production, refactor (NOT hotfix)

    Token cost: 0 tokens (pure keyword matching)
    """

    def auto_tag(self, memory_content: str) -> List[str]:
        """
        Automatically infer valid modes for memory.

        Args:
            memory_content: Memory content to analyze

        Returns:
            List of valid mode names
        """
        content_lower = memory_content.lower()

        # Quality rules (production, refactor only)
        quality_keywords = [
            "test", "doc", "comment", "error handling", "validation",
            "logging", "type hint", "docstring"
        ]
        if any(kw in content_lower for kw in quality_keywords):
            return ["production", "refactor"]

        # Speed rules (prototype, hotfix, exploration)
        speed_keywords = ["quick", "fast", "short", "concise", "minimal", "simple"]
        if any(kw in content_lower for kw in speed_keywords):
            return ["prototype", "hotfix", "exploration"]

        # Pattern/architecture rules (production, refactor)
        pattern_keywords = [
            "pattern", "architecture", "structure", "design",
            "solid", "dry", "separation of concerns"
        ]
        if any(kw in content_lower for kw in pattern_keywords):
            return ["production", "refactor"]

        # Debugging/analysis rules (audit, exploration)
        analysis_keywords = ["analyze", "review", "understand", "explain"]
        if any(kw in content_lower for kw in analysis_keywords):
            return ["audit", "exploration"]

        # Emergency rules (hotfix only)
        emergency_keywords = ["urgent", "critical", "hotfix", "emergency"]
        if any(kw in content_lower for kw in emergency_keywords):
            return ["hotfix"]

        # Default: All modes except audit/exploration
        # (most rules apply to active coding)
        return ["prototype", "production", "hotfix", "refactor"]

    def calculate_mode_priority(self, memory_content: str, valid_modes: List[str]) -> Dict[str, int]:
        """
        Calculate priority for each mode.

        Priority scale: 1-10 (10 = highest)

        Args:
            memory_content: Memory content to analyze
            valid_modes: List of valid modes from auto_tag()

        Returns:
            Dict mapping mode to priority (1-10)
        """
        content_lower = memory_content.lower()
        priorities = {}

        for mode in valid_modes:
            # Default priority
            priority = 5

            # Boost for explicit mode mentions
            if mode in content_lower:
                priority += 2

            # Quality rules have higher priority in production
            if mode == "production" and any(kw in content_lower for kw in ["test", "doc", "error"]):
                priority += 2

            # Speed rules have higher priority in prototype
            if mode == "prototype" and any(kw in content_lower for kw in ["quick", "fast", "simple"]):
                priority += 2

            # Urgency boosts hotfix priority
            if mode == "hotfix" and any(kw in content_lower for kw in ["urgent", "critical"]):
                priority += 3

            priorities[mode] = min(priority, 10)

        return priorities


# Standalone functions for easy integration

def detect_mode(user_prompt: str, context: Optional[Dict[str, Any]] = None) -> ModeDetectionResult:
    """
    Detect user intent mode from prompt.

    Convenience function for Phase 15B integration.

    Args:
        user_prompt: User's current message
        context: Optional session context

    Returns:
        ModeDetectionResult with detected mode
    """
    detector = ModeDetector()
    return detector.detect(user_prompt, context)


def auto_tag_memory(memory_content: str) -> tuple[List[str], Dict[str, int]]:
    """
    Auto-tag memory with valid modes and priorities.

    Convenience function for Phase 15B storage integration.

    Args:
        memory_content: Memory content to tag

    Returns:
        Tuple of (valid_modes, mode_priority)
    """
    tagger = ModeTagging()
    valid_modes = tagger.auto_tag(memory_content)
    mode_priority = tagger.calculate_mode_priority(memory_content, valid_modes)
    return valid_modes, mode_priority
