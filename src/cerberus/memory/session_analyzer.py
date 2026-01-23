"""
Phase 1: Session Correction Detection

Detects when user corrects AI behavior without manual memory_learn() calls.
Uses 4 detection patterns: direct negation, repetition, post-action, multi-turn.

Zero token cost - pure regex and keyword matching.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple
import re


@dataclass
class CorrectionCandidate:
    """Represents a potential user correction detected during the session."""
    turn_number: int
    user_message: str
    ai_response: str
    correction_type: str  # "style", "behavior", "rule", "preference"
    confidence: float  # 0.7-1.0
    context_before: List[str] = field(default_factory=list)  # Previous 3 turns

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "turn": self.turn_number,
            "user_message": self.user_message,
            "ai_response": self.ai_response,
            "correction_type": self.correction_type,
            "confidence": self.confidence,
            "context": self.context_before
        }


@dataclass
class SessionCorrections:
    """Container for all corrections detected in a session."""
    session_id: str
    timestamp: datetime
    candidates: List[CorrectionCandidate] = field(default_factory=list)
    project: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "project": self.project,
            "candidates": [c.to_dict() for c in self.candidates]
        }


class SessionAnalyzer:
    """
    Real-time session correction detector.

    Detects 4 patterns:
    1. Direct negation: "don't do X", "never Y"
    2. Repetition: Same correction 2+ times
    3. Post-action: Correction after AI action
    4. Multi-turn: Correction across multiple turns

    Zero token cost - uses regex and keywords only.
    """

    def __init__(self):
        """Initialize the session analyzer with empty buffers."""
        self.conversation_buffer: List[Tuple[str, str]] = []  # (role, message)
        self.candidates: List[CorrectionCandidate] = []

        # Detection patterns
        self.negation_words = {
            "don't", "dont", "never", "stop", "avoid", "not",
            "no", "nope", "incorrect", "wrong"
        }

        self.correction_indicators = {
            "again", "told you", "said", "mentioned", "asked",
            "already", "repeated", "keep telling", "stop doing"
        }

        self.post_action_phrases = {
            "actually", "instead", "change that", "modify",
            "no that's wrong", "that's incorrect", "fix that",
            "better approach", "should be", "should have"
        }

        self.repetition_threshold = 2  # Minimum repetitions to detect

    def analyze_turn(
        self,
        user_msg: str,
        ai_response: str
    ) -> Optional[CorrectionCandidate]:
        """
        Analyze a conversation turn for potential corrections.

        Args:
            user_msg: User's message
            ai_response: AI's response

        Returns:
            CorrectionCandidate if correction detected, None otherwise
        """
        # Add to conversation buffer
        self.conversation_buffer.append(("user", user_msg))
        self.conversation_buffer.append(("assistant", ai_response))

        turn_number = len(self.conversation_buffer) // 2

        # Check patterns in priority order
        # Post-action has highest priority (most specific context)
        # Pattern 3: Post-action correction
        candidate = self._detect_post_action(user_msg, ai_response, turn_number)
        if candidate:
            self.candidates.append(candidate)
            return candidate

        # Pattern 4: Multi-turn correction
        candidate = self._detect_multi_turn(user_msg, ai_response, turn_number)
        if candidate:
            self.candidates.append(candidate)
            return candidate

        # Pattern 2: Repetition detection
        candidate = self._detect_repetition(user_msg, ai_response, turn_number)
        if candidate:
            self.candidates.append(candidate)
            return candidate

        # Pattern 1: Direct negation (checked last - least specific)
        candidate = self._detect_direct_negation(user_msg, ai_response, turn_number)
        if candidate:
            self.candidates.append(candidate)
            return candidate

        return None

    def _detect_direct_negation(
        self,
        user_msg: str,
        ai_response: str,
        turn_number: int
    ) -> Optional[CorrectionCandidate]:
        """
        Pattern 1: Direct command (negation or affirmative).

        Negation examples:
        - "don't write verbose explanations"
        - "never exceed 200 lines"
        - "stop adding comments"

        Affirmative examples:
        - "always validate input"
        - "make sure to check errors"
        """
        msg_lower = user_msg.lower()

        # Check for command words (negation or affirmative)
        command_words = self.negation_words | {"always", "must", "should", "make sure", "ensure"}
        has_command = any(word in msg_lower for word in command_words)

        if not has_command:
            return None

        # Check for command structure (imperative mood)
        if not self._has_command_structure(user_msg):
            return None

        # Filter false positives (questions, statements)
        if self._is_false_positive(user_msg):
            return None

        return CorrectionCandidate(
            turn_number=turn_number,
            user_message=user_msg,
            ai_response=ai_response,
            correction_type="behavior",
            confidence=0.9,
            context_before=self._get_context(3)
        )

    def _detect_repetition(
        self,
        user_msg: str,
        ai_response: str,
        turn_number: int
    ) -> Optional[CorrectionCandidate]:
        """
        Pattern 2: User repeats similar instruction 2+ times.

        Examples:
        - "keep it short" (turn 1)
        - "be concise" (turn 4)
        - "terse output" (turn 7)
        """
        # Use lower threshold for repetition detection
        # Users may rephrase the same idea with different words
        similar = self._find_similar_messages(user_msg, threshold=0.5)

        if len(similar) >= self.repetition_threshold:
            return CorrectionCandidate(
                turn_number=turn_number,
                user_message=user_msg,
                ai_response=ai_response,
                correction_type="style",
                confidence=0.8,
                context_before=similar
            )

        return None

    def _detect_post_action(
        self,
        user_msg: str,
        ai_response: str,
        turn_number: int
    ) -> Optional[CorrectionCandidate]:
        """
        Pattern 3: Correction immediately after AI action.

        Examples:
        - AI writes 300-line file
        - User: "never exceed 200 lines"
        - User: "actually, keep it under 100"
        """
        if len(self.conversation_buffer) < 3:
            return None

        # Check if previous AI message took action
        prev_ai = self.conversation_buffer[-3][1] if len(self.conversation_buffer) >= 3 else ""
        if not self._ai_took_action(prev_ai):
            return None

        # If AI took action, check if user message contains correction/rule language
        msg_lower = user_msg.lower()

        # Explicit correction language
        has_correction_language = (
            any(ind in msg_lower for ind in self.correction_indicators) or
            any(phrase in msg_lower for phrase in self.post_action_phrases)
        )

        # Or strong command structure (rules after actions)
        has_rule_structure = (
            any(word in msg_lower for word in ["never", "always", "must", "should"]) and
            self._has_command_structure(user_msg)
        )

        if has_correction_language or has_rule_structure:
            return CorrectionCandidate(
                turn_number=turn_number,
                user_message=user_msg,
                ai_response=ai_response,
                correction_type="rule",
                confidence=1.0,
                context_before=self._get_context(2)
            )

        return None

    def _detect_multi_turn(
        self,
        user_msg: str,
        ai_response: str,
        turn_number: int
    ) -> Optional[CorrectionCandidate]:
        """
        Pattern 4: Correction that builds across multiple turns.

        Examples:
        - User: "fix the bug"
        - AI: <attempts fix>
        - User: "no, I meant do Y not X"
        - AI: <attempts Y>
        - User: "yes, always do Y for this case"
        """
        if len(self.conversation_buffer) < 6:  # Need at least 3 turns
            return None

        msg_lower = user_msg.lower()

        # Look for confirmation + rule establishment
        has_confirmation = any(word in msg_lower for word in ["yes", "correct", "right", "exactly"])
        has_rule_language = any(word in msg_lower for word in ["always", "never", "should", "must"])

        # Check if previous turns contained corrections
        prev_had_correction = any(
            "no" in self.conversation_buffer[i][1].lower() or
            "not" in self.conversation_buffer[i][1].lower()
            for i in range(-6, -1, 2)  # Check last 3 user messages
            if i < len(self.conversation_buffer) and self.conversation_buffer[i][0] == "user"
        )

        if has_confirmation and has_rule_language and prev_had_correction:
            return CorrectionCandidate(
                turn_number=turn_number,
                user_message=user_msg,
                ai_response=ai_response,
                correction_type="rule",
                confidence=0.95,
                context_before=self._get_context(4)
            )

        return None

    # Helper methods

    def _has_command_structure(self, msg: str) -> bool:
        """Check if message has imperative mood (command structure)."""
        msg_lower = msg.lower().strip()

        # Questions are not commands
        if msg_lower.endswith("?"):
            return False

        # Questions starting with question words
        question_starters = ["what", "why", "how", "when", "where", "who", "which", "can", "could", "would", "should i"]
        if any(msg_lower.startswith(q) for q in question_starters):
            return False

        # Direct command starters
        command_starters = [
            "don't", "dont", "never", "always", "stop", "keep",
            "make sure", "ensure", "avoid", "please don't", "please"
        ]

        # Check if starts with command word
        if any(msg_lower.startswith(cmd) for cmd in command_starters):
            return True

        # Check for command patterns anywhere in short messages
        # (imperative sentences can have the verb not at start)
        if len(msg.split()) <= 8:  # Short messages
            command_words = {"never", "always", "must"}
            words = set(msg_lower.split())
            if command_words & words:  # Intersection
                return True

        return False

    def _is_false_positive(self, msg: str) -> bool:
        """Filter false positives (questions, casual statements)."""
        msg_lower = msg.lower().strip()

        # Questions
        if msg_lower.endswith("?"):
            return True

        # Casual statements without commands
        false_positive_patterns = [
            "i don't know",
            "i don't understand",
            "don't worry",
            "that's not what",
            "not sure"
        ]

        return any(pattern in msg_lower for pattern in false_positive_patterns)

    def _find_similar_messages(self, msg: str, threshold: float) -> List[str]:
        """
        Find similar previous user messages using keyword overlap.

        Simple Jaccard similarity for Phase 1.
        Phase 2 will use TF-IDF for better semantic matching.
        """
        similar = []

        # Extract keywords (words > 3 chars, excluding common words)
        stop_words = {"this", "that", "with", "from", "have", "been", "were", "will"}
        keywords = set(
            word.lower() for word in msg.split()
            if len(word) > 3 and word.lower() not in stop_words
        )

        if not keywords:
            return similar

        # Check previous user messages (skip last 2 entries which are current turn)
        for role, prev_msg in self.conversation_buffer[:-2]:
            if role == "user":
                prev_keywords = set(
                    word.lower() for word in prev_msg.split()
                    if len(word) > 3 and word.lower() not in stop_words
                )

                if not prev_keywords:
                    continue

                # Jaccard similarity
                union = keywords | prev_keywords
                if len(union) == 0:
                    continue

                overlap = len(keywords & prev_keywords) / len(union)
                if overlap > threshold:
                    similar.append(prev_msg)

        return similar

    def _ai_took_action(self, ai_msg: str) -> bool:
        """Check if AI response indicates an action was taken."""
        action_markers = [
            "<invoke",  # Tool use
            "```",  # Code block
            "I've",  # Past action
            "I'll",  # Future action
            "Let me",  # Initiating action
            "I'm going to",  # Planned action
            "Created",  # Completed action
            "Modified",  # Completed action
            "Deleted"  # Completed action
        ]

        return any(marker in ai_msg for marker in action_markers)

    def _get_context(self, n: int) -> List[str]:
        """Get last n user messages for context."""
        context = []
        count = 0

        # Walk backwards through conversation buffer
        for i in range(len(self.conversation_buffer) - 1, -1, -1):
            role, msg = self.conversation_buffer[i]
            if role == "user":
                context.append(msg)
                count += 1
                if count >= n:
                    break

        # Reverse to chronological order
        return list(reversed(context))

    def get_session_corrections(
        self,
        session_id: str,
        project: Optional[str] = None
    ) -> SessionCorrections:
        """
        Get all corrections detected in this session.

        Args:
            session_id: Unique session identifier
            project: Optional project path

        Returns:
            SessionCorrections object with all detected candidates
        """
        return SessionCorrections(
            session_id=session_id,
            timestamp=datetime.now(),
            candidates=self.candidates,
            project=project
        )

    def clear(self):
        """Clear session state (call at session end)."""
        self.conversation_buffer.clear()
        self.candidates.clear()


# Module-level convenience functions

def analyze_conversation(
    conversation: List[Tuple[str, str]],
    session_id: str,
    project: Optional[str] = None
) -> SessionCorrections:
    """
    Analyze an entire conversation history for corrections.

    Args:
        conversation: List of (user_msg, ai_response) tuples
        session_id: Unique session identifier
        project: Optional project path

    Returns:
        SessionCorrections with all detected candidates
    """
    analyzer = SessionAnalyzer()

    for user_msg, ai_response in conversation:
        analyzer.analyze_turn(user_msg, ai_response)

    return analyzer.get_session_corrections(session_id, project)


def create_test_scenarios() -> List[Tuple[str, str, Optional[str]]]:
    """
    Create test scenarios for validation.

    Returns:
        List of (user_msg, ai_response, expected_type) tuples
    """
    return [
        # Scenario 1: Direct negation
        (
            "don't write verbose explanations",
            "I've written a detailed explanation of the code.",
            "behavior"
        ),

        # Scenario 2: Post-action
        (
            "never exceed 200 lines per file",
            "<invoke name='Write'><parameter name='file_path'>test.py</parameter><parameter name='content'>...300 lines...</parameter></invoke>",
            "rule"
        ),

        # Scenario 3: False positive (should NOT detect)
        (
            "I don't know what to do",
            "Let me help you figure that out.",
            None
        ),

        # Scenario 4: Another false positive
        (
            "Don't worry about it",
            "Okay, moving on.",
            None
        ),

        # Scenario 5: Direct negation with command
        (
            "never use emojis in code",
            "I've added some emojis to make it friendly! 😊",
            "behavior"
        ),
    ]
