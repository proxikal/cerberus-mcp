"""
Corrections Module (Phase 18.2)

Tracks patterns that developers repeatedly fix in AI output.
Stored globally (not per-project) since corrections apply universally.

Key constraints:
- Max 10 corrections by frequency
- Frequency-ranked for context injection
- Store verbose, inject terse
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import date

from cerberus.memory.store import MemoryStore
from cerberus.logging_config import logger


@dataclass
class Correction:
    """A single correction pattern."""
    id: str
    pattern: str          # What the AI keeps doing wrong
    correction: str       # What it should do instead
    frequency: int = 1    # How many times this has been corrected
    last_occurred: str = ""
    note: str = ""        # Brief explanation

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "pattern": self.pattern,
            "correction": self.correction,
            "frequency": self.frequency,
            "last_occurred": self.last_occurred,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Correction":
        """Create Correction from dictionary."""
        return cls(
            id=data.get("id", ""),
            pattern=data.get("pattern", ""),
            correction=data.get("correction", ""),
            frequency=data.get("frequency", 1),
            last_occurred=data.get("last_occurred", ""),
            note=data.get("note", ""),
        )

    def to_terse(self) -> str:
        """Generate terse representation for context injection."""
        # Format: "- Note (corrected Nx)" or "- Pattern -> Correction (Nx)"
        if self.note:
            return f"- {self.note} (corrected {self.frequency}x)"
        else:
            # Truncate pattern/correction if too long
            pattern = self.pattern[:40] + "..." if len(self.pattern) > 40 else self.pattern
            correction = self.correction[:40] + "..." if len(self.correction) > 40 else self.correction
            return f"- {pattern} -> {correction} ({self.frequency}x)"

    def increment(self) -> None:
        """Increment the frequency counter."""
        self.frequency += 1
        self.last_occurred = date.today().isoformat()


@dataclass
class CorrectionStore:
    """Collection of all corrections."""
    schema_version: str = "corrections-v1"
    updated_at: str = ""
    corrections: List[Correction] = field(default_factory=list)

    # Maximum corrections to keep
    MAX_CORRECTIONS = 20  # Store more, show top 10 in context

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "$schema": self.schema_version,
            "updated_at": self.updated_at,
            "corrections": [c.to_dict() for c in self.corrections],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorrectionStore":
        """Create CorrectionStore from dictionary."""
        corrections = [Correction.from_dict(c) for c in data.get("corrections", [])]
        return cls(
            schema_version=data.get("$schema", "corrections-v1"),
            updated_at=data.get("updated_at", ""),
            corrections=corrections,
        )

    def get_by_frequency(self, count: int = 10) -> List[Correction]:
        """Get corrections sorted by frequency (highest first)."""
        sorted_corrections = sorted(
            self.corrections,
            key=lambda c: c.frequency,
            reverse=True
        )
        return sorted_corrections[:count]

    def find_similar(self, pattern: str) -> Optional[Correction]:
        """Find an existing correction with similar pattern."""
        pattern_lower = pattern.lower()
        for c in self.corrections:
            if pattern_lower in c.pattern.lower() or c.pattern.lower() in pattern_lower:
                return c
        return None


class CorrectionManager:
    """
    Manages correction patterns.

    Corrections are stored globally and ranked by frequency.
    When a similar correction is learned again, its frequency increases.
    """

    def __init__(self, store: Optional[MemoryStore] = None):
        """
        Initialize the correction manager.

        Args:
            store: MemoryStore instance (creates default if not provided)
        """
        self.store = store or MemoryStore()

    def load_corrections(self) -> CorrectionStore:
        """Load all corrections."""
        data = self.store.read_json(self.store.corrections_path)
        if data is None:
            return CorrectionStore()
        return CorrectionStore.from_dict(data)

    def save_corrections(self, corrections: CorrectionStore) -> bool:
        """Save corrections."""
        corrections.updated_at = MemoryStore.timestamp()
        return self.store.write_json(self.store.corrections_path, corrections.to_dict())

    def _generate_id(self, corrections: CorrectionStore) -> str:
        """Generate a unique correction ID."""
        existing_ids = {c.id for c in corrections.corrections}
        counter = len(corrections.corrections) + 1
        while f"cor-{counter:03d}" in existing_ids:
            counter += 1
        return f"cor-{counter:03d}"

    def learn_correction(
        self,
        text: str,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Learn a new correction pattern.

        Args:
            text: The correction description
                  Can be: "pattern -> correction" or just a description
            note: Optional brief note about the correction

        Returns:
            Dict with 'success', 'correction', 'message', 'is_new'
        """
        corrections = self.load_corrections()

        # Parse the text
        pattern, correction_text, parsed_note = self._parse_correction_text(text)

        # Use provided note or parsed note
        final_note = note or parsed_note or ""

        # Check for similar existing correction
        existing = corrections.find_similar(pattern)
        if existing:
            # Increment frequency of existing correction
            existing.increment()
            if final_note and not existing.note:
                existing.note = final_note
            self.save_corrections(corrections)
            return {
                "success": True,
                "correction": existing.to_dict(),
                "is_new": False,
                "message": f"Incremented correction frequency to {existing.frequency}x",
            }

        # Create new correction
        correction = Correction(
            id=self._generate_id(corrections),
            pattern=pattern,
            correction=correction_text,
            frequency=1,
            last_occurred=date.today().isoformat(),
            note=final_note,
        )

        # Add and maintain max limit
        corrections.corrections.append(correction)
        if len(corrections.corrections) > CorrectionStore.MAX_CORRECTIONS:
            # Remove lowest frequency corrections
            corrections.corrections = sorted(
                corrections.corrections,
                key=lambda c: c.frequency,
                reverse=True
            )[:CorrectionStore.MAX_CORRECTIONS]

        if self.save_corrections(corrections):
            return {
                "success": True,
                "correction": correction.to_dict(),
                "is_new": True,
                "message": f"Learned new correction: {final_note or pattern[:50]}",
            }
        else:
            return {
                "success": False,
                "message": "Failed to save correction",
            }

    def _parse_correction_text(self, text: str) -> tuple[str, str, str]:
        """
        Parse correction text into pattern, correction, and note.

        Handles formats:
        - "pattern -> correction"
        - "AI keeps doing X instead of Y"
        - "always log before throwing errors"
        """
        text = text.strip()

        # Check for explicit "pattern -> correction" format
        if " -> " in text:
            parts = text.split(" -> ", 1)
            return parts[0].strip(), parts[1].strip(), ""

        # Check for "X instead of Y" pattern
        if " instead of " in text.lower():
            parts = text.lower().split(" instead of ", 1)
            # The wrong pattern is what comes before, correction is what comes after
            pattern = parts[0].replace("ai keeps ", "").replace("keeps ", "").strip()
            correction = parts[1].strip()
            return pattern, correction, text

        # Check for "should X not Y" pattern
        if " not " in text.lower() and "should" in text.lower():
            # This is a note about what to do
            return text, "", text

        # Check for "always X" or "never X" patterns
        if text.lower().startswith(("always ", "never ")):
            return text, "", text

        # Default: treat as a note/description
        return text, "", text

    def forget_correction(self, correction_id: str) -> Dict[str, Any]:
        """
        Remove a correction by ID.

        Args:
            correction_id: The correction ID (e.g., "cor-001")

        Returns:
            Dict with 'success' and 'message'
        """
        corrections = self.load_corrections()

        for i, c in enumerate(corrections.corrections):
            if c.id == correction_id:
                removed = corrections.corrections.pop(i)
                self.save_corrections(corrections)
                return {
                    "success": True,
                    "message": f"Removed correction {correction_id}: {removed.note or removed.pattern[:30]}",
                }

        return {
            "success": False,
            "message": f"Correction {correction_id} not found",
        }

    def get_corrections_for_context(self, count: int = 5) -> List[str]:
        """
        Get terse correction strings for context injection.

        Args:
            count: Maximum number of corrections to include

        Returns:
            List of terse correction strings (frequency-ranked)
        """
        corrections = self.load_corrections()
        top_corrections = corrections.get_by_frequency(count)
        return [c.to_terse() for c in top_corrections]

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of stored corrections."""
        corrections = self.load_corrections()
        return {
            "total_count": len(corrections.corrections),
            "total_frequency": sum(c.frequency for c in corrections.corrections),
            "top_corrections": [
                {"id": c.id, "note": c.note or c.pattern[:30], "frequency": c.frequency}
                for c in corrections.get_by_frequency(5)
            ],
        }
