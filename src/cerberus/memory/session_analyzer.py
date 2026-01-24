"""
Phase 1: Session Correction Detection

Detects when user corrects AI behavior without manual memory_learn() calls.
Uses 4 detection patterns: direct negation, repetition, post-action, multi-turn.

Zero token cost - pure regex and keyword matching.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import os
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

    Detects 5 patterns:
    1. Direct negation: "don't do X", "never Y"
    2. Repetition: Same correction 2+ times
    3. Post-action: Correction after AI action
    4. Multi-turn: Correction across multiple turns
    5. Preference: "I prefer X over Y", "I like X"

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

        # Early filter: Skip false positives
        if self._is_false_positive(user_msg):
            return None

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

        # Pattern 5: Preference statements
        candidate = self._detect_preference(user_msg, ai_response, turn_number)
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

    def _detect_preference(
        self,
        user_msg: str,
        ai_response: str,
        turn_number: int
    ) -> Optional[CorrectionCandidate]:
        """
        Pattern 5: Preference statements.

        Examples:
        - "I prefer Snowflake IDs over UUIDs"
        - "I like using semantic versioning"
        - "I want tests in separate files"
        - "would rather use TypeScript than JavaScript"
        """
        msg_lower = user_msg.lower()

        # Preference indicators
        preference_patterns = [
            ("i prefer", "over"),
            ("i'd prefer", "over"),
            ("i like", None),
            ("i'd like", None),
            ("i want", None),
            ("i'd want", None),
            ("would rather", "than"),
            ("would prefer", "over"),
            ("prefer to use", None),
            ("like to use", None),
        ]

        # Check if message contains preference pattern
        has_preference = False
        for pattern, contrast_word in preference_patterns:
            if pattern in msg_lower:
                has_preference = True
                break

        if not has_preference:
            return None

        # Filter out questions
        if msg_lower.strip().endswith("?"):
            return None

        # Filter out hypotheticals and conditionals
        hypothetical_markers = ["if i", "what if", "suppose", "imagine", "let's say"]
        if any(marker in msg_lower for marker in hypothetical_markers):
            return None

        return CorrectionCandidate(
            turn_number=turn_number,
            user_message=user_msg,
            ai_response=ai_response,
            correction_type="preference",
            confidence=0.85,
            context_before=self._get_context(3)
        )

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

        # Questions (ending with ? or containing question marks)
        if "?" in msg_lower:
            # Allow if it's a rhetorical question with strong command language
            has_strong_command = any(
                cmd in msg_lower for cmd in ["never", "always", "must", "ensure", "make sure"]
            )
            if not has_strong_command:
                return True

        # Casual statements without commands
        false_positive_patterns = [
            "i don't know",
            "i don't understand",
            "don't worry",
            "that's not what",
            "not sure",
            "i'm confused",
            "am i confused",
            "if i am confused",
            "sorry if"
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

    def get_candidates(self) -> List[CorrectionCandidate]:
        """
        Get all detected correction candidates.

        This is called at session end to retrieve corrections that were
        detected during the session and stored in SQLite.

        Returns:
            List of CorrectionCandidate objects
        """
        return self.candidates


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


# ============================================================================
# Transcript Parsing (Session End Analysis)
# ============================================================================

def parse_claude_code_transcript(transcript_path: Path) -> List[Tuple[str, str]]:
    """
    Parse Claude Code transcript JSONL file for user/assistant messages.

    Args:
        transcript_path: Path to .jsonl transcript file

    Returns:
        List of (user_msg, assistant_msg) tuples
    """
    messages = []

    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)

                    # Check if entry has a message field (Claude Code format)
                    message = entry.get('message')
                    if not message:
                        continue

                    role = message.get('role')
                    if role not in ('user', 'assistant'):
                        continue

                    content = message.get('content', [])

                    # Handle string content (simple user messages)
                    if isinstance(content, str):
                        messages.append((role, content))
                        continue

                    # Handle array content (assistant messages with tool use, thinking, etc)
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'text':
                            text_parts.append(block.get('text', ''))

                    if text_parts:
                        message_text = '\n'.join(text_parts)
                        messages.append((role, message_text))

                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        return []

    # Pair user messages with following assistant messages
    conversations = []
    i = 0
    while i < len(messages):
        role, text = messages[i]
        if role == 'user':
            # Look for next assistant message
            for j in range(i + 1, len(messages)):
                next_role, next_text = messages[j]
                if next_role == 'assistant':
                    conversations.append((text, next_text))
                    i = j + 1
                    break
            else:
                # No assistant response found
                i += 1
        else:
            i += 1

    return conversations


def find_current_transcript() -> Optional[Path]:
    """
    Find the current session's transcript file.

    Claude Code stores transcripts in:
    ~/.claude/projects/{working-dir-hash}/{session-id}.jsonl

    Returns:
        Path to transcript, or None if not found
    """
    # Get working directory hash
    cwd = Path.cwd()
    cwd_hash = str(cwd).replace('/', '-')

    # Claude Code project directory
    projects_dir = Path.home() / ".claude" / "projects" / cwd_hash

    if not projects_dir.exists():
        return None

    # Find most recent .jsonl file
    jsonl_files = list(projects_dir.glob("*.jsonl"))
    if not jsonl_files:
        return None

    # Return most recently modified
    return max(jsonl_files, key=lambda p: p.stat().st_mtime)


def analyze_session_from_transcript() -> List[CorrectionCandidate]:
    """
    Analyze current session from transcript at session end.

    This is called by propose_hook() to detect corrections from the
    conversation history.

    Returns:
        List of detected CorrectionCandidate objects
    """
    # Find transcript
    transcript = find_current_transcript()
    if not transcript:
        return []

    # Parse conversations
    conversations = parse_claude_code_transcript(transcript)
    if not conversations:
        return []

    # Replay through analyzer
    analyzer = SessionAnalyzer()
    for user_msg, ai_response in conversations:
        analyzer.analyze_turn(user_msg, ai_response)

    # Deduplicate by turn number and message content
    seen = set()
    unique_candidates = []
    for candidate in analyzer.candidates:
        key = (candidate.turn_number, candidate.user_message[:100])
        if key not in seen:
            seen.add(key)
            unique_candidates.append(candidate)

    return unique_candidates


# ============================================================================
# Session Context Extraction (Work Summary)
# ============================================================================

def extract_tool_calls_from_transcript(transcript_path: Path) -> List[Dict[str, str]]:
    """
    Extract tool calls (Edit, Write, Bash) from transcript.

    Returns:
        List of {tool: str, params: dict} dicts
    """
    tool_calls = []

    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    message = entry.get('message', {})
                    content = message.get('content', [])

                    # Look for tool_use blocks in assistant messages
                    if message.get('role') == 'assistant':
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'tool_use':
                                tool_calls.append({
                                    'tool': block.get('name', ''),
                                    'params': block.get('input', {})
                                })
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass

    return tool_calls


def extract_session_codes() -> List[str]:
    """
    Extract FULL session context from transcript (AI-only format).

    Hierarchical codes with context:
    - migrate:what:from-to (major work streams)
    - impl:file:what-was-added (file modifications with context)
    - fix:system:issue:solution (bug fixes with details)
    - dec:decision:reason (decisions with rationale)
    - block:what:detail (blockers with specifics)
    - next:action:context (next steps with context)
    - done:what:detail (completions with context)

    Target: 80-120 codes = ~1000-1500 tokens (full session context)

    Strategy: Hierarchical context, no prose, AI-readable.
    """
    transcript = find_current_transcript()
    if not transcript:
        return []

    codes = []

    # Parse conversations first (needed for context)
    conversations = parse_claude_code_transcript(transcript)

    # Helper: Extract keywords from text (remove stop words, keep meaningful terms)
    def extract_keywords(text: str, max_words: int = 6) -> str:
        """Extract key words/phrases, remove filler and special chars."""
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'this',
            'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'may', 'might', 'must', 'can', 'just', 'also', 'now',
            'so', 'then', 'very', 'too', 'i', 'you', 'we', 'me', 'us', 'my', 'our',
            'it', 'its', 'there', 'their', 'them', 'they'
        }

        # Clean text: remove special chars, keep only alphanumeric and spaces
        cleaned = re.sub(r'[^\w\s-]', ' ', text.lower())

        words = cleaned.split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2][:max_words]
        return '-'.join(keywords) if keywords else ''

    # 1. Extract MAJOR WORK STREAMS from conversations
    # Look for the big picture work across multiple messages
    major_work_found = {
        'session_migration': False,
        'search_fix': False,
        'config_system': False,
        'extraction_impl': False
    }

    for user_msg, ai_msg in conversations:
        combined = (user_msg + ' ' + ai_msg).lower()

        # Session tracking migration (JSON to SQLite)
        if not major_work_found['session_migration']:
            if ('session' in combined and 'sqlite' in combined) or \
               ('session' in combined and 'json' in combined and ('remove' in combined or 'migrate' in combined)):
                codes.append("migrate:session-tracking:json-to-sqlite")
                major_work_found['session_migration'] = True

        # Search/Cerberus fix
        if not major_work_found['search_fix']:
            if ('search' in combined or 'cerberus' in combined) and \
               ('broken' in combined or 'failing' in combined or 'empty' in combined) and \
               ('fts5' in combined or 'index' in combined or 'file' in combined):
                codes.append("fix:cerberus-search:empty-results:added-filepath-fts5")
                major_work_found['search_fix'] = True

        # Config system implementation
        if not major_work_found['config_system']:
            if 'config' in combined and 'hierarchical' in combined:
                codes.append("implement:hierarchical-config:global-and-project")
                major_work_found['config_system'] = True

        # Session extraction implementation
        if not major_work_found['extraction_impl']:
            if ('transcript' in combined and 'parsing' in combined) or \
               ('nlp' in combined and 'extraction' in combined) or \
               ('comprehensive' in combined and 'extraction' in combined):
                codes.append("implement:session-extraction:transcript-nlp-codes")
                major_work_found['extraction_impl'] = True

    # 2. Extract tool calls WITH CONTEXT from surrounding messages
    tool_calls = extract_tool_calls_from_transcript(transcript)
    file_context = {}  # Maps filename -> list of contexts

    # Build context map from conversations
    for i, (user_msg, ai_msg) in enumerate(conversations):
        msg_text = (user_msg + ' ' + ai_msg).lower()

        # Extract what work is being discussed
        work_contexts = []
        if 'transcript' in msg_text and 'parsing' in msg_text:
            work_contexts.append('transcript-parsing')
        if 'nlp' in msg_text or 'extraction' in msg_text or 'keyword' in msg_text:
            work_contexts.append('nlp-extraction')
        if 'quality' in msg_text and ('filter' in msg_text or 'check' in msg_text):
            work_contexts.append('quality-filter')
        if 'dedupe' in msg_text or 'duplicate' in msg_text:
            work_contexts.append('deduplication')
        if 'delete' in msg_text and 'read' in msg_text:
            work_contexts.append('delete-on-read')
        if 'semantic' in msg_text:
            work_contexts.append('semantic-analysis')
        if 'fts5' in msg_text or 'index' in msg_text:
            work_contexts.append('fts5-index')
        if 'config' in msg_text and ('user' in msg_text or 'hierarchical' in msg_text):
            work_contexts.append('config-system')
        if 'hook' in msg_text and 'session' in msg_text:
            work_contexts.append('session-hooks')
        if 'sqlite' in msg_text:
            work_contexts.append('sqlite-backend')
        if 'comprehensive' in msg_text:
            work_contexts.append('comprehensive-extraction')
        if 'pattern' in msg_text:
            work_contexts.append('pattern-matching')

        # Map contexts to files mentioned
        for context in work_contexts:
            # Look for file mentions in next few tool calls
            for j in range(max(0, i-2), min(len(tool_calls), i+3)):
                if j < len(tool_calls):
                    call = tool_calls[j]
                    if call['tool'] in ('Edit', 'Write'):
                        file_path = call['params'].get('file_path', '')
                        if file_path:
                            filename = Path(file_path).name
                            if filename not in file_context:
                                file_context[filename] = []
                            if context not in file_context[filename]:
                                file_context[filename].append(context)

    # Generate impl: codes with context
    files_processed = set()
    for call in tool_calls:
        tool = call['tool']
        params = call['params']

        if tool in ('Edit', 'Write'):
            file_path = params.get('file_path', '')
            if file_path:
                filename = Path(file_path).name
                if filename in files_processed:
                    continue
                files_processed.add(filename)

                # Add context if we have it
                contexts = file_context.get(filename, [])
                if contexts:
                    for ctx in contexts[:3]:  # Max 3 contexts per file
                        codes.append(f"impl:{filename}:{ctx}")
                else:
                    # Fallback: just filename
                    codes.append(f"impl:{filename}")

    # Analyze bash commands for completions
    bash_commands = [call['params'].get('command', '') for call in tool_calls if call['tool'] == 'Bash']
    for cmd in bash_commands:
        cmd_lower = cmd.lower()
        if 'pytest' in cmd_lower or 'test' in cmd_lower:
            codes.append("done:tests:pytest")
        elif 'git commit' in cmd_lower:
            codes.append("done:git:commit")
        elif 'git push' in cmd_lower:
            codes.append("done:git:push")
        elif 'build' in cmd_lower or 'compile' in cmd_lower:
            codes.append("done:build")

    # 3. Extract DECISIONS with context and rationale
    decision_patterns_contextual = [
        # With reason/alternative
        (r'use\s+(\w+(?:\s+\w+){0,2})\s+instead\s+of\s+(\w+(?:\s+\w+){0,2})',
         lambda m: f"dec:use-{extract_keywords(m.group(1), 2)}:not-{extract_keywords(m.group(2), 2)}"),
        (r'(?:removed|deleted)\s+(?:completely\s+)?after\s+(?:being\s+)?(?:read|injected)',
         lambda m: f"dec:delete-on-read:prevent-bloat"),
        (r"(?:make\s+sure\s+)?(?:no|there'?s\s+no)\s+more\s+(.{5,30}?)(?:\s+files?|\s+or|\.|$)",
         lambda m: f"dec:remove-{extract_keywords(m.group(1), 2)}:cleanup"),
        (r'(?:within|under)\s+(?:the\s+)?(\d+(?:-\d+)?k?)\s+tokens?',
         lambda m: f"dec:token-limit:{m.group(1)}"),
        (r'compact.*ai\s+only',
         lambda m: f"dec:ai-only-format:no-human-prose"),
        (r'sqlite\s+(?:for|database|backend)',
         lambda m: f"dec:sqlite-backend:not-json"),
        (r'needs?\s+to\s+be\s+(perfect|accurate|compact|clear)',
         lambda m: f"dec:quality-{m.group(1)}"),
        (r'hierarchical.*config',
         lambda m: f"dec:hierarchical-config:global-and-project"),
        (r'(?:config|configuration)\s+option',
         lambda m: f"dec:add-config-option:user-control"),
    ]

    for user_msg, ai_msg in conversations:
        if len(user_msg) < 20:
            continue

        msg_lower = user_msg.lower()
        ai_lower = ai_msg.lower() if ai_msg else ''

        # Extract DECISIONS with context
        for pattern, formatter in decision_patterns_contextual:
            match = re.search(pattern, msg_lower, re.IGNORECASE)
            if match:
                try:
                    code = formatter(match)
                    if code and len(code) > 10:
                        codes.append(code)
                except:
                    pass

        # Extract FIXES from assistant messages (what was fixed + how)
        fix_patterns = [
            (r'fixed\s+(.{10,40}?)\s+by\s+(.{10,50}?)(?:\.|$)',
             lambda m: f"fix:{extract_keywords(m.group(1), 3)}:{extract_keywords(m.group(2), 4)}"),
            (r'(?:search|cerberus)\s+(?:was\s+)?(?:failing|broken).*(?:added|fixed)\s+(.{10,40}?)(?:\.|$)',
             lambda m: f"fix:search:{extract_keywords(m.group(1), 4)}"),
        ]

        for pattern, formatter in fix_patterns:
            match = re.search(pattern, ai_lower, re.IGNORECASE)
            if match:
                try:
                    code = formatter(match)
                    if code and len(code) > 12:
                        codes.append(code)
                except:
                    pass

        # Extract BLOCKERS with specifics
        blocker_patterns_contextual = [
            (r'(?:session\s+)?end\s+hook.*error(?:ing)?',
             'block:session-end-hook:erroring'),
            (r'(?:cerberus|search)\s+(?:is\s+)?broken.*(?:search|empty|failing)',
             'block:cerberus-search:empty-results'),
            (r"can'?t\s+(.{10,40}?)\s+(?:because|until)\s+(.{10,40}?)(?:\.|$)",
             lambda m: f"block:{extract_keywords(m.group(1), 3)}:needs-{extract_keywords(m.group(2), 3)}"),
        ]

        for pattern, formatter in blocker_patterns_contextual:
            match = re.search(pattern, msg_lower, re.IGNORECASE)
            if match:
                if callable(formatter):
                    try:
                        code = formatter(match)
                        if len(code) > 12:
                            codes.append(code)
                    except:
                        pass
                else:
                    codes.append(formatter)

        # Extract NEXT ACTIONS with context
        next_patterns_contextual = [
            (r'(?:we\s+)?need\s+to\s+(.{10,50}?)(?:\.|,|$)',
             lambda m: f"next:{extract_keywords(m.group(1), 5)}"),
            (r'figure\s+out\s+(.{10,50}?)(?:\.|$)',
             lambda m: f"next:investigate-{extract_keywords(m.group(1), 5)}"),
            (r'(?:run\s+through|audit)\s+(.{10,40}?)(?:\.|$)',
             lambda m: f"next:audit-{extract_keywords(m.group(1), 4)}"),
        ]

        for pattern, formatter in next_patterns_contextual:
            match = re.search(pattern, msg_lower, re.IGNORECASE)
            if match:
                try:
                    code = formatter(match)
                    if code and len(code) > 10:
                        codes.append(code)
                except:
                    pass

        # Extract COMPLETIONS with context
        completion_patterns_contextual = [
            (r'(?:awesome|great).*(?:now|so)\s+(.{10,40}?)\s+(?:is\s+)?(?:working|functional)',
             lambda m: f"done:{extract_keywords(m.group(1), 3)}:working"),
            (r'(?:so\s+)?memories\s+(?:are\s+)?working',
             'done:memories:functional'),
        ]

        for pattern, formatter in completion_patterns_contextual:
            match = re.search(pattern, msg_lower, re.IGNORECASE)
            if match:
                if callable(formatter):
                    try:
                        code = formatter(match)
                        if code:
                            codes.append(code)
                    except:
                        pass
                else:
                    codes.append(formatter)

        # Extract completions from AI messages
        ai_completion_patterns = [
            (r'(?:successfully\s+)?(?:implemented|migrated|fixed|removed)\s+(.{10,50}?)(?:\.|$)',
             lambda m: f"done:{extract_keywords(m.group(1), 5)}"),
            (r'removed\s+all\s+(.{10,40}?)(?:\s+references|\s+code|\.| $)',
             lambda m: f"done:removed-{extract_keywords(m.group(1), 3)}"),
        ]

        for pattern, formatter in ai_completion_patterns:
            match = re.search(pattern, ai_lower, re.IGNORECASE)
            if match:
                try:
                    code = formatter(match)
                    if code and len(code) > 10:
                        codes.append(code)
                except:
                    pass

    # 4. Quality filter and deduplicate
    def is_meaningful(code: str) -> bool:
        """Filter out fragmented or meaningless codes."""
        if not code or ':' not in code:
            return False

        parts = code.split(':')
        category = parts[0]

        # Minimum length
        if len(code) < 12:
            return False

        # Filter codes with question marks (not actual actions)
        if '?' in code:
            return False

        # Filter meaningless single-word fragments
        meaningless_patterns = [
            ':now:', ':then:', ':ok:', ':yes:', ':no:', ':fix:',
            ':what:', ':this:', ':that:'
        ]
        if any(pattern in code for pattern in meaningless_patterns):
            return False

        return True

    def semantic_dedupe(codes_list: List[str]) -> List[str]:
        """Remove semantically duplicate codes."""
        unique = []
        seen = set()

        for code in codes_list:
            if ':' not in code:
                continue

            # Exact duplicate check
            if code in seen:
                continue

            # For hierarchical codes, check for semantic duplicates
            # E.g., "impl:file.py:feature-a" vs "impl:file.py:feature-a" (exact)
            # But allow "impl:file.py:feature-a" and "impl:file.py:feature-b" (different)

            # Get normalized form (lowercase, collapse multiple colons)
            normalized = code.lower().strip()

            # Check if very similar code exists
            is_duplicate = False
            for existing in seen:
                # If 90%+ character overlap and same category, likely duplicate
                if existing.split(':')[0] == normalized.split(':')[0]:  # Same category
                    existing_content = ':'.join(existing.split(':')[1:])
                    current_content = ':'.join(normalized.split(':')[1:])

                    if existing_content and current_content:
                        # Character-level similarity
                        shorter = min(len(existing_content), len(current_content))
                        longer = max(len(existing_content), len(current_content))

                        # Count matching characters
                        matches = sum(1 for a, b in zip(existing_content, current_content) if a == b)
                        similarity = matches / longer if longer > 0 else 0

                        if similarity > 0.85:
                            is_duplicate = True
                            break

            if not is_duplicate:
                unique.append(code)
                seen.add(normalized)

        return unique

    # Apply quality filter
    quality_codes = [c for c in codes if is_meaningful(c)]

    # Deduplicate
    unique_codes = semantic_dedupe(quality_codes)

    # Limit to 150 codes (~1500 tokens target)
    return unique_codes[:150]


def extract_session_details() -> str:
    """
    Extract structured details for hybrid session summary.

    Provides why/how/where context to complement semantic codes.
    Format: Clean structured bullets focusing on explanations.
    Target: ~500-800 tokens (vs 2500+ prose, 200 codes-only).

    Returns:
        Structured text with bullets explaining key work
    """
    transcript = find_current_transcript()
    if not transcript:
        return ""

    conversations = parse_claude_code_transcript(transcript)
    tool_calls = extract_tool_calls_from_transcript(transcript)

    sections = {
        'bugs': [],
        'investigations': [],
        'files': set()
    }

    # Track what's been documented
    seen = set()

    # Helper: Clean and deduplicate line
    def add_unique(category: str, text: str, max_len: int = 100):
        """Add text to section if unique and meaningful."""
        text = text.strip()
        if not text or len(text) < 10:
            return

        # Remove markdown and special chars
        text = re.sub(r'[*_#`]', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = text[:max_len]

        # Filter out code-like patterns after cleaning (word:word:word)
        # These are semantic codes, not explanations
        code_pattern = re.search(r'[\w-]+:[\w-]+:[\w-]+', text)
        if code_pattern:
            # If the code takes up most of the text, skip it
            code_ratio = len(code_pattern.group(0)) / len(text)
            if code_ratio > 0.5:
                return

        # Skip lines that are mostly file paths
        if text.count('/') > 2 or text.endswith(('.py', '.md', '.txt', '.json')):
            return

        # Deduplicate
        normalized = text.lower()
        if normalized not in seen:
            sections[category].append(text)
            seen.add(normalized)

    # Extract bug fixes and their context
    for user_msg, ai_msg in conversations:
        combined_lower = (user_msg + ' ' + ai_msg).lower()

        # Only process conversations about bugs/fixes
        if not any(keyword in combined_lower for keyword in ['bug', 'fix', 'broken', 'issue', 'error', 'fail']):
            continue

        lines = ai_msg.split('\n')
        for line in lines:
            line_clean = line.strip()
            if not line_clean or len(line_clean) < 15:
                continue

            line_lower = line_clean.lower()

            # Extract root causes
            if any(marker in line_lower for marker in ['root cause:', 'why it', 'because', 'the problem']):
                # Clean up and format
                text = re.sub(r'^[-*•]\s*', '', line_clean)
                if not text.lower().startswith('root'):
                    text = f"Root: {text}"
                add_unique('bugs', text, 120)

            # Extract solutions/fixes
            elif any(marker in line_lower for marker in ['fix:', 'solution:', 'added', 'modified']):
                text = re.sub(r'^[-*•]\s*', '', line_clean)
                if not text.lower().startswith(('fix', 'solution')):
                    text = f"Fix: {text}"
                add_unique('bugs', text, 120)

    # Extract investigation results/conclusions
    for user_msg, ai_msg in conversations:
        ai_lower = ai_msg.lower()

        # Look for conclusion patterns
        if any(marker in ai_lower for marker in ['conclusion:', 'working as designed', 'verified:', 'confirmed:']):
            lines = ai_msg.split('\n')
            for line in lines:
                line_clean = line.strip()
                if not line_clean or len(line_clean) < 15:
                    continue

                line_lower = line_clean.lower()
                if any(marker in line_lower for marker in ['conclusion:', 'working as', 'verified', 'confirmed']):
                    text = re.sub(r'^[-*•]\s*', '', line_clean)
                    add_unique('investigations', text, 150)

    # Extract modified files
    for call in tool_calls:
        if call.get('name') in ['Edit', 'Write', 'NotebookEdit']:
            params = call.get('params', {})
            file_path = params.get('file_path', '')
            if file_path:
                # Get just filename
                filename = file_path.split('/')[-1]
                sections['files'].add(filename)

    # Format output
    output = []

    # Bugs/Fixes section
    if sections['bugs']:
        output.append("Bugs/Fixes:")
        for item in sections['bugs'][:8]:  # Limit to 8 items
            output.append(f"- {item}")

    # Investigations section
    if sections['investigations']:
        if output:
            output.append("")
        output.append("Investigations:")
        for item in sections['investigations'][:5]:  # Limit to 5 items
            output.append(f"- {item}")

    # Files section
    if sections['files']:
        if output:
            output.append("")
        output.append("Files Modified:")
        for filename in sorted(sections['files'])[:10]:  # Limit to 10 files
            output.append(f"- {filename}")

    return '\n'.join(output) if output else ""


def save_session_context_to_db():
    """
    Save session context codes + structured details to SQLite sessions table.

    Called at session end to persist hybrid work summary.
    """
    from cerberus.memory.session_continuity import detect_session_scope
    import sqlite3
    import uuid

    codes = extract_session_codes()
    if not codes:
        return

    scope, project_path = detect_session_scope()

    # Build context_data JSON - preserve ALL codes with categories
    context_data = {
        "work_streams": [c for c in codes if c.startswith(("migrate:", "implement:", "fix:", "integrate:", "add:", "remove:"))],
        "files": [c for c in codes if c.startswith("impl:")],
        "completed": [c for c in codes if c.startswith("done:")],
        "decisions": [c for c in codes if c.startswith("dec:")],
        "blockers": [c for c in codes if c.startswith("block:")],
        "next_actions": [c for c in codes if c.startswith("next:")],
    }

    # Extract structured details (hybrid format)
    details = extract_session_details()

    # Store in sessions table
    db_path = Path.home() / ".cerberus" / "memory.db"
    conn = sqlite3.connect(db_path)

    try:
        # Check if active session exists
        row = conn.execute("""
            SELECT id FROM sessions
            WHERE scope = ? AND status = 'active'
        """, (scope,)).fetchone()

        if row:
            # Update existing session
            conn.execute("""
                UPDATE sessions
                SET context_data = ?, summary_details = ?, last_activity = CURRENT_TIMESTAMP
                WHERE scope = ? AND status = 'active'
            """, (json.dumps(context_data), details, scope))
        else:
            # Create new session
            session_id = f"session-{uuid.uuid4().hex[:12]}"
            conn.execute("""
                INSERT INTO sessions (id, scope, project_path, status, context_data, summary_details)
                VALUES (?, ?, ?, 'active', ?, ?)
            """, (session_id, scope, project_path, json.dumps(context_data), details))

        conn.commit()
    finally:
        conn.close()
