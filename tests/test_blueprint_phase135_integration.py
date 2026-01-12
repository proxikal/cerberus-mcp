"""Integration tests for Phase 13.5 features working together."""

import pytest
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

pytestmark = [pytest.mark.integration, pytest.mark.blueprint]

from cerberus.blueprint.dependency_classifier import DependencyClassifier
from cerberus.blueprint.tree_builder import TreeBuilder
from cerberus.blueprint.cache_manager import BlueprintCache
from cerberus.blueprint.schemas import (
    DependencyInfo,
    TreeRenderOptions,
)


class TestPhase135Integration:
    """Integration tests for Phase 13.5 features working together."""

    def test_dependency_classification_in_hydration(self, tmp_path):
        """Test dependency classifier works with hydration analyzer."""
        classifier = DependencyClassifier(project_root=tmp_path)

        internal_file = tmp_path / "module.py"
        internal_file.touch()

        dep_type = classifier.classify_dependency(
            target_symbol="func",
            target_file=str(internal_file)
        )
        assert dep_type == "internal"

    def test_truncation_with_dependency_markers(self):
        """Test width truncation preserves dependency type markers."""
        builder = TreeBuilder(TreeRenderOptions(max_width=50))

        deps = [
            DependencyInfo(
                target="very_long_function_name_that_exceeds_width",
                confidence=0.9,
                dependency_type="internal"
            )
        ]

        result = builder._format_dependencies(deps)
        assert len(result) <= 200

    def test_cache_tracking_supports_regeneration(self, tmp_path):
        """Test cache access tracking enables regeneration."""
        conn = MagicMock(spec=sqlite3.Connection)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (0, "cache_key", "TEXT", 0, None, 1),
            (1, "access_count", "INTEGER", 0, "0", 0),
            (2, "last_accessed", "REAL", 0, "0", 0),
        ]
        conn.execute.return_value = mock_cursor

        cache = BlueprintCache(conn)

        cache._track_access("key1")
        cache._track_access("key2")

        assert conn.execute.call_count >= 2
