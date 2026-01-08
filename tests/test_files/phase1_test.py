# Test file for Phase 1 integration testing
# This file tests recursive call graphs, type resolution, and import linkage

import os
from typing import List, Dict, Optional
from pathlib import Path

class DataProcessor:
    """Process data with type annotations."""

    def __init__(self, config: Dict[str, str]):
        self.config: Dict[str, str] = config
        self.cache: List[str] = []

    def process(self, data: str) -> str:
        """Process data and return result."""
        result = self.validate(data)
        self.cache.append(result)
        return result

    def validate(self, data: str) -> str:
        """Validate data before processing."""
        if not data:
            return ""
        return helper_function(data)

def helper_function(text: str) -> str:
    """Helper function called by DataProcessor."""
    return text.upper()

def main_entry_point() -> None:
    """Main entry point that starts the chain."""
    processor = DataProcessor({"mode": "test"})
    processor.process("hello")
    helper_function("world")
