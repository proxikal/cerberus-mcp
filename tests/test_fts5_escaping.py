"""
Tests for FTS5 query escaping.

Verifies that special characters in search queries are properly escaped
to prevent FTS5 syntax errors.
"""

import pytest
from cerberus.storage.sqlite.symbols import escape_fts5_query


class TestFTS5QueryEscaping:
    """Test FTS5 query escaping logic."""

    def test_simple_query_unchanged(self):
        """Test that simple queries pass through unchanged."""
        query = "authenticate"
        result = escape_fts5_query(query)
        assert result == "authenticate"

    def test_multi_word_unchanged(self):
        """Test that multi-word queries without special chars are unchanged."""
        query = "user authentication service"
        result = escape_fts5_query(query)
        assert result == "user authentication service"

    def test_at_symbol_escaped(self):
        """Test that @ symbol is escaped by wrapping in quotes."""
        query = "@mcp.tool"
        result = escape_fts5_query(query)
        assert result == '"@mcp.tool"'

    def test_decorator_pattern_escaped(self):
        """Test that decorator patterns are escaped."""
        query = "@decorator"
        result = escape_fts5_query(query)
        assert result == '"@decorator"'

    def test_asterisk_escaped(self):
        """Test that asterisk is escaped."""
        query = "test*"
        result = escape_fts5_query(query)
        assert result == '"test*"'

    def test_parentheses_escaped(self):
        """Test that parentheses are escaped."""
        query = "func()"
        result = escape_fts5_query(query)
        assert result == '"func()"'

    def test_colon_escaped(self):
        """Test that colon is escaped."""
        query = "symbols:name"
        result = escape_fts5_query(query)
        assert result == '"symbols:name"'

    def test_caret_escaped(self):
        """Test that caret is escaped."""
        query = "^start"
        result = escape_fts5_query(query)
        assert result == '"^start"'

    def test_plus_minus_escaped(self):
        """Test that +/- are escaped."""
        query = "+required -excluded"
        result = escape_fts5_query(query)
        assert result == '"+required -excluded"'

    def test_double_quotes_escaped(self):
        """Test that double quotes are escaped within phrase search."""
        query = 'class "Foo"'
        result = escape_fts5_query(query)
        # Double quotes should be doubled and wrapped
        assert result == '"class ""Foo"""'

    def test_advanced_and_query_unchanged(self):
        """Test that intentional AND queries are preserved."""
        query = "function AND parse"
        result = escape_fts5_query(query)
        assert result == "function AND parse"

    def test_advanced_or_query_unchanged(self):
        """Test that intentional OR queries are preserved."""
        query = "read OR write"
        result = escape_fts5_query(query)
        assert result == "read OR write"

    def test_advanced_not_query_unchanged(self):
        """Test that intentional NOT queries are preserved."""
        query = "symbol NOT test"
        result = escape_fts5_query(query)
        assert result == "symbol NOT test"

    def test_complex_query_with_special_chars(self):
        """Test complex query with multiple special characters."""
        query = "@app.route(/api/*)"
        result = escape_fts5_query(query)
        assert result == '"@app.route(/api/*)"'

    def test_empty_query(self):
        """Test that empty query is handled."""
        query = ""
        result = escape_fts5_query(query)
        assert result == ""

    def test_query_with_only_special_chars(self):
        """Test query with only special characters."""
        query = "@@@@"
        result = escape_fts5_query(query)
        assert result == '"@@@@"'


class TestFTS5SearchIntegration:
    """Integration tests with actual SQLite FTS5."""

    def test_escape_function_in_real_query(self):
        """Test that the escape function works correctly in practice."""
        # These would have crashed FTS5 before the fix
        problematic_queries = [
            ("@mcp.tool", '"@mcp.tool"'),
            ("func()", '"func()"'),
            ("test*", '"test*"'),
            ("name:value", '"name:value"'),
        ]

        for original, expected in problematic_queries:
            escaped = escape_fts5_query(original)
            assert escaped == expected

    def test_advanced_queries_preserved(self):
        """Test that advanced FTS5 queries are not mangled."""
        advanced_queries = [
            "function AND parse",
            "read OR write",
            "symbol NOT test",
            "auth AND (user OR admin)",
        ]

        for query in advanced_queries:
            # Advanced queries should pass through unchanged
            escaped = escape_fts5_query(query)
            # They should remain unchanged (no wrapping in quotes)
            assert '"' not in escaped or "AND" in query or "OR" in query or "NOT" in query


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
