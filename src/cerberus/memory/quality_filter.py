"""
Memory Quality Filter

Uses spaCy + textblob to filter conversational noise and non-actionable content.
Ensures only semantic codes and actionable memories get stored.

Zero token cost (local processing).
"""

from typing import Optional
import re
from dataclasses import dataclass

# Lazy imports to avoid startup cost
_nlp = None
_textblob_available = None


def _get_nlp():
    """Lazy load spaCy model."""
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except (ImportError, OSError):
            # Fallback: spaCy not installed or model not downloaded
            _nlp = False
    return _nlp


def _check_textblob():
    """Check if textblob is available."""
    global _textblob_available
    if _textblob_available is None:
        try:
            import textblob
            _textblob_available = True
        except ImportError:
            _textblob_available = False
    return _textblob_available


@dataclass
class QualityScore:
    """Quality assessment of memory content."""
    is_actionable: bool
    is_semantic_code: bool
    has_conversational_noise: bool
    has_question: bool
    subjectivity_score: float  # 0.0 = objective, 1.0 = subjective
    confidence: float  # Overall quality confidence
    rejection_reason: Optional[str] = None


class MemoryQualityFilter:
    """
    Filter conversational noise and non-actionable content.

    Uses:
    - spaCy: POS tagging, dependency parsing (imperative detection)
    - textblob: Subjectivity analysis (catches subtle conversational tone)
    - Regex: Pattern matching for semantic codes and explicit conversational markers

    Quality gates:
    1. Semantic codes (pref:X, decision:Y) → ACCEPT (already formatted)
    2. Questions → REJECT (regex)
    3. Conversational markers → REJECT (regex: "I think", "Let's", etc.)
    4. Uncertainty markers → REJECT (regex: "maybe", "probably")
    5. Ellipsis truncation → REJECT (regex)
    6. High subjectivity → REJECT (textblob: catches subtle tone without explicit markers)
    7. Imperatives/declaratives → ACCEPT (spaCy POS tagging)
    """

    # Semantic code patterns (already good format)
    SEMANTIC_CODE_PATTERN = re.compile(
        r'^(pref|preference|decision|correction|rule|impl|next):[a-z0-9_]+',
        re.IGNORECASE
    )

    # Conversational starters (always reject)
    CONVERSATIONAL_STARTERS = [
        "ok,", "yeah,", "well,", "so,", "actually,", "basically,",
        "i think", "i guess", "i suppose", "let's", "let me",
        "can you", "could you", "would you", "should i",
        "is there", "are there", "do you", "does this"
    ]

    # Question patterns (always reject)
    QUESTION_PATTERNS = [
        r'\?$',  # Ends with question mark
        r'^(what|where|when|why|how|who)\s',  # Question words
        r'^(is|are|does|do|can|could|would|should)\s',  # Yes/no questions
    ]

    # Uncertainty markers (reject)
    UNCERTAINTY_MARKERS = [
        "maybe", "perhaps", "might", "possibly", "probably",
        "i'm not sure", "not sure", "uncertain", "unclear"
    ]

    def __init__(self):
        """Initialize quality filter."""
        self.nlp = _get_nlp()
        self.has_textblob = _check_textblob()

    def assess_quality(self, content: str) -> QualityScore:
        """
        Assess memory content quality.

        Args:
            content: Memory content to assess

        Returns:
            QualityScore with assessment details
        """
        if not content or len(content.strip()) < 5:
            return QualityScore(
                is_actionable=False,
                is_semantic_code=False,
                has_conversational_noise=True,
                has_question=False,
                subjectivity_score=1.0,
                confidence=0.0,
                rejection_reason="too_short"
            )

        content_lower = content.lower().strip()

        # GATE 1: Check if already semantic code (ACCEPT immediately)
        if self.SEMANTIC_CODE_PATTERN.match(content):
            return QualityScore(
                is_actionable=True,
                is_semantic_code=True,
                has_conversational_noise=False,
                has_question=False,
                subjectivity_score=0.0,
                confidence=1.0
            )

        # GATE 2: Check for questions (REJECT)
        for pattern in self.QUESTION_PATTERNS:
            if re.search(pattern, content_lower):
                return QualityScore(
                    is_actionable=False,
                    is_semantic_code=False,
                    has_conversational_noise=True,
                    has_question=True,
                    subjectivity_score=1.0,
                    confidence=0.0,
                    rejection_reason="question"
                )

        # GATE 3: Check for conversational starters (REJECT)
        for starter in self.CONVERSATIONAL_STARTERS:
            if content_lower.startswith(starter):
                return QualityScore(
                    is_actionable=False,
                    is_semantic_code=False,
                    has_conversational_noise=True,
                    has_question=False,
                    subjectivity_score=1.0,
                    confidence=0.0,
                    rejection_reason="conversational"
                )

        # GATE 4: Check for uncertainty markers (REJECT)
        for marker in self.UNCERTAINTY_MARKERS:
            if marker in content_lower:
                return QualityScore(
                    is_actionable=False,
                    is_semantic_code=False,
                    has_conversational_noise=True,
                    has_question=False,
                    subjectivity_score=1.0,
                    confidence=0.0,
                    rejection_reason="uncertain"
                )

        # GATE 5: Check for ellipsis truncation (REJECT)
        if content.endswith("...") or "..." in content:
            return QualityScore(
                is_actionable=False,
                is_semantic_code=False,
                has_conversational_noise=True,
                has_question=False,
                subjectivity_score=1.0,
                confidence=0.0,
                rejection_reason="truncated"
            )

        # GATE 6: Subjectivity check (textblob) - catches subtle conversational tone
        subjectivity = 0.5  # Default neutral
        if self.has_textblob:
            try:
                from textblob import TextBlob
                blob = TextBlob(content)
                subjectivity = blob.sentiment.subjectivity

                # High subjectivity = conversational/opinion WITHOUT explicit markers (REJECT)
                # This catches: "That seems right", "This feels better", "X works well"
                if subjectivity > 0.7:
                    return QualityScore(
                        is_actionable=False,
                        is_semantic_code=False,
                        has_conversational_noise=True,
                        has_question=False,
                        subjectivity_score=subjectivity,
                        confidence=0.0,
                        rejection_reason="subjective"
                    )
            except Exception:
                # Textblob failed, continue with other checks
                pass

        # GATE 7: POS tagging (spaCy) - check for imperative/declarative
        is_actionable = False
        if self.nlp and self.nlp is not False:
            try:
                doc = self.nlp(content)

                # Check if starts with imperative verb (VB) or noun (actionable pattern)
                if len(doc) > 0:
                    first_token = doc[0]

                    # Imperative: starts with base verb (VB)
                    # Examples: "Use X", "Avoid Y", "Keep Z"
                    if first_token.pos_ == "VERB" and first_token.tag_ == "VB":
                        is_actionable = True

                    # Declarative with modal: "Never use X", "Always prefer Y"
                    # Check for adverbs like "never", "always"
                    if first_token.pos_ == "ADV" and first_token.text.lower() in ["never", "always", "prefer"]:
                        is_actionable = True

                    # Check for action verbs in first 3 tokens
                    action_verbs = {"use", "avoid", "prefer", "keep", "write", "split", "plan", "test", "ensure", "check"}
                    for token in doc[:3]:
                        if token.lemma_.lower() in action_verbs:
                            is_actionable = True
                            break
            except Exception:
                # spaCy failed, fall back to basic heuristics
                pass

        # Fallback: Check for action verb starters (regex)
        if not is_actionable:
            action_starters = r'^(use|avoid|prefer|keep|write|split|plan|test|ensure|check|never|always)\s'
            if re.search(action_starters, content_lower):
                is_actionable = True

        # Final assessment
        if not is_actionable:
            return QualityScore(
                is_actionable=False,
                is_semantic_code=False,
                has_conversational_noise=False,
                has_question=False,
                subjectivity_score=subjectivity,
                confidence=0.3,
                rejection_reason="not_imperative"
            )

        # ACCEPT: Actionable content
        return QualityScore(
            is_actionable=True,
            is_semantic_code=False,
            has_conversational_noise=False,
            has_question=False,
            subjectivity_score=subjectivity,
            confidence=0.8
        )

    def should_accept(self, content: str) -> bool:
        """
        Quick check: should this content be accepted?

        Args:
            content: Memory content

        Returns:
            True if content passes quality gates
        """
        score = self.assess_quality(content)
        return score.is_actionable or score.is_semantic_code

    def filter_batch(self, contents: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
        """
        Filter a batch of memory contents.

        Args:
            contents: List of memory content strings

        Returns:
            Tuple of (accepted_contents, rejected_with_reasons)
        """
        accepted = []
        rejected = []

        for content in contents:
            score = self.assess_quality(content)
            if score.is_actionable or score.is_semantic_code:
                accepted.append(content)
            else:
                rejected.append((content, score.rejection_reason or "Failed quality check"))

        return accepted, rejected
