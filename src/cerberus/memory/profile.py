"""
Profile Management Module

Handles developer profile schema, parsing, and operations.
The profile stores global preferences that apply across all projects.

Key constraints:
- Max profile size: 1KB / 50 lines
- Store verbose, inject terse
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from cerberus.memory.store import MemoryStore
from cerberus.logging_config import logger


class PreferenceCategory(Enum):
    """Categories for organizing preferences."""
    CODING_STYLE = "coding_style"
    NAMING = "naming_conventions"
    ANTI_PATTERNS = "anti_patterns"
    LANGUAGES = "languages"
    GENERAL = "general"


@dataclass
class Profile:
    """
    Developer profile schema.

    This represents the full stored profile (verbose).
    Context injection will compress this to ~10% of size.
    """
    schema_version: str = "profile-v1"
    updated_at: str = ""

    # Coding style preferences
    coding_style: Dict[str, Any] = field(default_factory=dict)

    # Naming conventions
    naming_conventions: Dict[str, str] = field(default_factory=dict)

    # Anti-patterns to avoid
    anti_patterns: List[str] = field(default_factory=list)

    # Language preferences
    languages: Dict[str, List[str]] = field(default_factory=dict)

    # General preferences (free-form)
    general: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "$schema": self.schema_version,
            "updated_at": self.updated_at,
            "coding_style": self.coding_style,
            "naming_conventions": self.naming_conventions,
            "anti_patterns": self.anti_patterns,
            "languages": self.languages,
            "general": self.general,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Profile":
        """Create Profile from dictionary."""
        return cls(
            schema_version=data.get("$schema", "profile-v1"),
            updated_at=data.get("updated_at", ""),
            coding_style=data.get("coding_style", {}),
            naming_conventions=data.get("naming_conventions", {}),
            anti_patterns=data.get("anti_patterns", []),
            languages=data.get("languages", {}),
            general=data.get("general", []),
        )

    def is_empty(self) -> bool:
        """Check if profile has any content."""
        return (
            not self.coding_style
            and not self.naming_conventions
            and not self.anti_patterns
            and not self.languages
            and not self.general
        )


class ProfileManager:
    """
    Manages the developer profile.

    Handles:
    - Parsing natural language preferences
    - Categorizing and storing preferences
    - Retrieving profile for context injection
    """

    # Known coding style patterns (keyword -> style key)
    STYLE_PATTERNS = {
        # Returns
        r"\bearly\s+returns?\b": ("prefer_early_returns", True),
        r"\bnested\s+conditionals?\b": ("prefer_early_returns", True),
        r"\bguard\s+clauses?\b": ("prefer_early_returns", True),

        # Async
        r"\basync[\s/]+await\b": ("async_style", "async_await"),
        r"\bpromises?\b(?!.*async)": ("async_style", "promises"),

        # Error handling
        r"\blog\s+(?:before|then)\s+throw": ("error_handling", "log_then_throw"),
        r"\balways\s+log\s+errors?\b": ("error_handling", "log_then_throw"),

        # Imports
        r"\bnamed\s+imports?\b": ("imports", "named_over_default"),
        r"\bdefault\s+imports?\b": ("imports", "default_preferred"),

        # Quotes
        r"\bsingle\s+quotes?\b": ("quotes", "single"),
        r"\bdouble\s+quotes?\b": ("quotes", "double"),

        # Line length
        r"\bmax\s+(?:line\s+)?(?:length|width)[:\s]+(\d+)": ("max_line_length", None),  # Capture group
        r"\b(\d+)\s+(?:char(?:acter)?s?|columns?)\s+(?:max|limit)": ("max_line_length", None),
    }

    # Anti-pattern keywords
    ANTI_PATTERN_KEYWORDS = [
        r"\bnever\b",
        r"\bavoid\b",
        r"\bdon'?t\b",
        r"\bhate\b",
        r"\banti[- ]?pattern\b",
        r"\bbad\s+practice\b",
    ]

    # Naming convention patterns
    NAMING_PATTERNS = {
        r"\bPascal\s*Case\b": "PascalCase",
        r"\bcamel\s*Case\b": "camelCase",
        r"\bsnake[_\s]*case\b": "snake_case",
        r"\bSCREAMING[_\s]*SNAKE\b": "SCREAMING_SNAKE",
        r"\bkebab[_\s-]*case\b": "kebab-case",
    }

    def __init__(self, store: Optional[MemoryStore] = None):
        """
        Initialize the profile manager.

        Args:
            store: MemoryStore instance (creates default if not provided)
        """
        self.store = store or MemoryStore()

    def load_profile(self) -> Profile:
        """Load the profile from storage."""
        data = self.store.read_json(self.store.profile_path)
        if data is None:
            return Profile()
        return Profile.from_dict(data)

    def save_profile(self, profile: Profile) -> bool:
        """
        Save the profile to storage.

        Returns:
            True if saved successfully, False if size limit exceeded
        """
        profile.updated_at = MemoryStore.timestamp()
        return self.store.write_json(
            self.store.profile_path,
            profile.to_dict(),
            check_size=True,
            max_size=MemoryStore.MAX_PROFILE_SIZE
        )

    def learn(self, text: str) -> Dict[str, Any]:
        """
        Learn a preference from natural language input.

        This parses the text, categorizes it, and adds it to the profile.

        Args:
            text: Natural language preference (e.g., "prefer early returns")

        Returns:
            Dict with 'success', 'category', 'key', 'value', 'message'
        """
        profile = self.load_profile()
        text_lower = text.lower().strip()

        # Try to match coding style patterns
        for pattern, (key, value) in self.STYLE_PATTERNS.items():
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                # Handle patterns with capture groups (like line length)
                if value is None and match.groups():
                    value = int(match.group(1))

                profile.coding_style[key] = value
                if self.save_profile(profile):
                    return {
                        "success": True,
                        "category": PreferenceCategory.CODING_STYLE.value,
                        "key": key,
                        "value": value,
                        "message": f"Learned coding style: {key} = {value}",
                    }
                else:
                    return {
                        "success": False,
                        "category": PreferenceCategory.CODING_STYLE.value,
                        "message": "Profile size limit exceeded (1KB max)",
                    }

        # Check for anti-patterns
        for anti_pattern in self.ANTI_PATTERN_KEYWORDS:
            if re.search(anti_pattern, text_lower):
                # Extract the anti-pattern description
                # Remove the keyword and clean up
                cleaned = re.sub(r"|".join(self.ANTI_PATTERN_KEYWORDS), "", text, flags=re.IGNORECASE).strip()
                if cleaned and cleaned not in profile.anti_patterns:
                    profile.anti_patterns.append(cleaned)
                    if self.save_profile(profile):
                        return {
                            "success": True,
                            "category": PreferenceCategory.ANTI_PATTERNS.value,
                            "key": None,
                            "value": cleaned,
                            "message": f"Learned anti-pattern: {cleaned}",
                        }
                    else:
                        return {
                            "success": False,
                            "category": PreferenceCategory.ANTI_PATTERNS.value,
                            "message": "Profile size limit exceeded (1KB max)",
                        }

        # Check for naming conventions
        for pattern, convention in self.NAMING_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                # Try to find what the convention applies to
                context_patterns = [
                    (r"\bcomponents?\b", "components"),
                    (r"\bfunctions?\b", "functions"),
                    (r"\bclass(?:es)?\b", "classes"),
                    (r"\bconstants?\b", "constants"),
                    (r"\bvariables?\b", "variables"),
                    (r"\bmethods?\b", "methods"),
                    (r"\bprivate\b", "private_methods"),
                ]

                for ctx_pattern, ctx_name in context_patterns:
                    if re.search(ctx_pattern, text_lower):
                        profile.naming_conventions[ctx_name] = convention
                        if self.save_profile(profile):
                            return {
                                "success": True,
                                "category": PreferenceCategory.NAMING.value,
                                "key": ctx_name,
                                "value": convention,
                                "message": f"Learned naming: {ctx_name} = {convention}",
                            }
                        else:
                            return {
                                "success": False,
                                "category": PreferenceCategory.NAMING.value,
                                "message": "Profile size limit exceeded (1KB max)",
                            }

        # Fallback: add as general preference
        if text not in profile.general:
            profile.general.append(text)
            if self.save_profile(profile):
                return {
                    "success": True,
                    "category": PreferenceCategory.GENERAL.value,
                    "key": None,
                    "value": text,
                    "message": f"Learned general preference: {text}",
                }
            else:
                return {
                    "success": False,
                    "category": PreferenceCategory.GENERAL.value,
                    "message": "Profile size limit exceeded (1KB max)",
                }

        return {
            "success": False,
            "category": None,
            "message": "Preference already exists in profile",
        }

    def forget(self, text: str) -> Dict[str, Any]:
        """
        Remove a preference from the profile.

        Args:
            text: The preference text to remove

        Returns:
            Dict with 'success' and 'message'
        """
        profile = self.load_profile()
        text_lower = text.lower().strip()

        # Check coding style
        for key in list(profile.coding_style.keys()):
            if key.lower() == text_lower or text_lower in key.lower():
                del profile.coding_style[key]
                self.save_profile(profile)
                return {"success": True, "message": f"Removed coding style: {key}"}

        # Check naming conventions
        for key in list(profile.naming_conventions.keys()):
            if key.lower() == text_lower or text_lower in key.lower():
                del profile.naming_conventions[key]
                self.save_profile(profile)
                return {"success": True, "message": f"Removed naming convention: {key}"}

        # Check anti-patterns
        for i, ap in enumerate(profile.anti_patterns):
            if text_lower in ap.lower():
                removed = profile.anti_patterns.pop(i)
                self.save_profile(profile)
                return {"success": True, "message": f"Removed anti-pattern: {removed}"}

        # Check general
        for i, pref in enumerate(profile.general):
            if text_lower in pref.lower():
                removed = profile.general.pop(i)
                self.save_profile(profile)
                return {"success": True, "message": f"Removed preference: {removed}"}

        return {"success": False, "message": f"Preference not found: {text}"}

    def get_profile_summary(self) -> Dict[str, Any]:
        """Get a summary of the profile for display."""
        profile = self.load_profile()

        return {
            "updated_at": profile.updated_at,
            "coding_style_count": len(profile.coding_style),
            "naming_conventions_count": len(profile.naming_conventions),
            "anti_patterns_count": len(profile.anti_patterns),
            "general_count": len(profile.general),
            "is_empty": profile.is_empty(),
        }
