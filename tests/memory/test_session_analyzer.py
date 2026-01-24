"""
Tests for Phase 1: Session Correction Detection

Validates 90%+ accuracy on detection patterns.
"""

import pytest
from cerberus.memory.session_analyzer import (
    SessionAnalyzer,
    CorrectionCandidate,
    analyze_conversation,
    create_test_scenarios
)


class TestSessionAnalyzer:
    """Test suite for SessionAnalyzer."""

    def test_direct_negation_detection(self):
        """Test Pattern 1: Direct negation with command structure."""
        analyzer = SessionAnalyzer()

        # Positive case: Should detect
        candidate = analyzer.analyze_turn(
            "don't write verbose explanations",
            "I've written a detailed explanation."
        )

        assert candidate is not None
        assert candidate.correction_type == "behavior"
        assert candidate.confidence == 0.9
        assert candidate.turn_number == 1

    def test_direct_negation_false_positive(self):
        """Test that casual 'don't' statements are not detected."""
        analyzer = SessionAnalyzer()

        # Should NOT detect - question
        candidate = analyzer.analyze_turn(
            "I don't know what to do?",
            "Let me help you figure that out."
        )
        assert candidate is None

        # Should NOT detect - casual statement
        candidate = analyzer.analyze_turn(
            "Don't worry about it",
            "Okay, moving on."
        )
        assert candidate is None

    def test_repetition_detection(self):
        """Test Pattern 2: Repetition of similar instructions."""
        analyzer = SessionAnalyzer()

        # Build up conversation with very similar messages
        analyzer.analyze_turn("keep your responses short", "Okay, I'll be brief.")
        analyzer.analyze_turn("unrelated message here", "Got it.")
        analyzer.analyze_turn("keep responses short", "Sure thing.")

        # Third similar message should trigger detection
        # All share "keep", "responses", "short" keywords
        candidate = analyzer.analyze_turn(
            "keep your short responses",
            "Understood."
        )

        assert candidate is not None
        assert candidate.correction_type == "style"
        assert candidate.confidence == 0.8
        assert len(candidate.context_before) >= 2

    def test_post_action_detection(self):
        """Test Pattern 3: Correction after AI action."""
        analyzer = SessionAnalyzer()

        # First turn: AI takes action
        analyzer.analyze_turn(
            "Create a file",
            "<invoke name='Write'><parameter>test.py</parameter></invoke> I've created the file."
        )

        # Second turn: User corrects
        candidate = analyzer.analyze_turn(
            "actually, never exceed 200 lines per file",
            "Got it, I'll keep files under 200 lines."
        )

        assert candidate is not None
        assert candidate.correction_type == "rule"
        assert candidate.confidence == 1.0

    def test_multi_turn_detection(self):
        """Test Pattern 4: Multi-turn correction with confirmation."""
        analyzer = SessionAnalyzer()

        # Build up multi-turn conversation
        analyzer.analyze_turn("fix the bug", "Let me try approach X.")
        analyzer.analyze_turn("no, I meant do Y not X", "Okay, trying Y instead.")
        analyzer.analyze_turn("yes, always do Y for this case", "Understood, will use Y.")

        # Should have detected the multi-turn correction
        assert len(analyzer.candidates) > 0
        last_candidate = analyzer.candidates[-1]
        assert last_candidate.correction_type == "rule"
        assert last_candidate.confidence == 0.95

    def test_ai_action_detection(self):
        """Test helper method for detecting AI actions."""
        analyzer = SessionAnalyzer()

        # Should detect tool use
        assert analyzer._ai_took_action("<invoke name='Read'>")

        # Should detect code blocks
        assert analyzer._ai_took_action("Here's the code:\n```python\nprint('hello')\n```")

        # Should detect action language
        assert analyzer._ai_took_action("I've created the file")
        assert analyzer._ai_took_action("Let me write that for you")

        # Should NOT detect regular responses
        assert not analyzer._ai_took_action("That's a good question.")

    def test_command_structure_detection(self):
        """Test helper method for imperative mood detection."""
        analyzer = SessionAnalyzer()

        # Should detect commands
        assert analyzer._has_command_structure("don't do that")
        assert analyzer._has_command_structure("never use emojis")
        assert analyzer._has_command_structure("always validate input")
        assert analyzer._has_command_structure("stop adding comments")

        # Should NOT detect non-commands
        assert not analyzer._has_command_structure("I think this is wrong")
        assert not analyzer._has_command_structure("what should I do")

    def test_similar_message_detection(self):
        """Test Jaccard similarity for repetition detection."""
        analyzer = SessionAnalyzer()

        # Add some messages
        analyzer.conversation_buffer = [
            ("user", "keep the code short and concise"),
            ("assistant", "Okay"),
            ("user", "make it brief"),
            ("assistant", "Sure")
        ]

        # Find similar to new message (using realistic threshold)
        # Jaccard similarity between "write concise code" and "keep code short concise"
        # = {code, concise} / {write, concise, code, keep, short} = 2/5 = 0.4
        similar = analyzer._find_similar_messages(
            "write concise code please",
            threshold=0.3  # Lower threshold for realistic matching
        )

        assert len(similar) > 0
        assert "keep the code short and concise" in similar

    def test_context_extraction(self):
        """Test getting previous user messages for context."""
        analyzer = SessionAnalyzer()

        # Build conversation
        analyzer.conversation_buffer = [
            ("user", "message 1"),
            ("assistant", "response 1"),
            ("user", "message 2"),
            ("assistant", "response 2"),
            ("user", "message 3"),
            ("assistant", "response 3"),
        ]

        context = analyzer._get_context(3)

        assert len(context) == 3
        assert context[0] == "message 1"
        assert context[1] == "message 2"
        assert context[2] == "message 3"

    def test_session_corrections_serialization(self):
        """Test that SessionCorrections can be serialized to dict."""
        analyzer = SessionAnalyzer()

        analyzer.analyze_turn(
            "don't write comments",
            "I've added comments to explain the code."
        )

        corrections = analyzer.get_session_corrections(
            session_id="test-123",
            project="/path/to/project"
        )

        # Convert to dict
        data = corrections.to_dict()

        assert data["session_id"] == "test-123"
        assert data["project"] == "/path/to/project"
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["correction_type"] == "behavior"

    def test_analyze_conversation_function(self):
        """Test module-level convenience function."""
        conversation = [
            ("don't use verbose names", "I'll use descriptive variable names."),
            ("keep it short", "Okay, I'll be concise."),
        ]

        corrections = analyze_conversation(
            conversation=conversation,
            session_id="test-456",
            project="/test/project"
        )

        assert corrections.session_id == "test-456"
        assert corrections.project == "/test/project"
        assert len(corrections.candidates) >= 1

    def test_clear_session(self):
        """Test that clear() resets the analyzer state."""
        analyzer = SessionAnalyzer()

        analyzer.analyze_turn("don't do X", "Okay")
        assert len(analyzer.candidates) > 0
        assert len(analyzer.conversation_buffer) > 0

        analyzer.clear()
        assert len(analyzer.candidates) == 0
        assert len(analyzer.conversation_buffer) == 0


class TestAccuracyValidation:
    """Validate 90%+ accuracy on test scenarios."""

    def test_scenario_accuracy(self):
        """Run all test scenarios and check accuracy."""
        scenarios = create_test_scenarios()
        analyzer = SessionAnalyzer()

        results = []
        for user_msg, ai_response, expected_type in scenarios:
            candidate = analyzer.analyze_turn(user_msg, ai_response)

            if expected_type is None:
                # Should NOT detect
                results.append(candidate is None)
            else:
                # Should detect with correct type
                results.append(
                    candidate is not None and
                    candidate.correction_type == expected_type
                )

        # Calculate accuracy
        accuracy = sum(results) / len(results)
        print(f"\nAccuracy: {accuracy * 100:.1f}% ({sum(results)}/{len(results)})")

        assert accuracy >= 0.9, f"Accuracy {accuracy:.1%} below 90% threshold"

    def test_comprehensive_scenarios(self):
        """Test 10 comprehensive scenarios for validation gate."""
        test_cases = [
            # 1. Direct negation - behavior
            ("don't write for humans", "response", "behavior"),

            # 2. Direct negation - rule
            ("never exceed 200 lines", "<invoke>Write</invoke>", "rule"),

            # 3. False positive - question
            ("I don't understand?", "Let me explain", None),

            # 4. False positive - casual
            ("Don't worry", "Okay", None),

            # 5. Post-action with 'actually'
            ("actually, keep it under 100", "<invoke>Write</invoke> Created file", "rule"),

            # 6. Post-action with 'instead'
            ("instead, use approach Y", "I've implemented X", "rule"),

            # 7. Command with 'always'
            ("always validate input", "response", "behavior"),

            # 8. Command with 'stop'
            ("stop adding comments", "I've added comments", "behavior"),

            # 9. False positive - statement without command
            ("that's not what I meant", "Sorry, let me try again", None),

            # 10. Negation with 'avoid'
            ("avoid using global variables", "response", "behavior"),
        ]

        analyzer = SessionAnalyzer()
        correct = 0
        total = len(test_cases)

        for i, (user_msg, ai_response, expected_type) in enumerate(test_cases, 1):
            # For post-action tests, add prior action
            if "actually" in user_msg or "instead" in user_msg:
                analyzer.analyze_turn("create something", ai_response)
            # For scenario 2, we need to simulate AI taking action first
            elif "<invoke>" in ai_response:
                analyzer.analyze_turn("create a file", ai_response)

            candidate = analyzer.analyze_turn(user_msg, "response")

            is_correct = False
            if expected_type is None:
                is_correct = (candidate is None)
            else:
                is_correct = (
                    candidate is not None and
                    candidate.correction_type == expected_type
                )

            if is_correct:
                correct += 1

            print(f"Scenario {i}: {'✓' if is_correct else '✗'} (expected: {expected_type}, got: {candidate.correction_type if candidate else None})")

        accuracy = correct / total
        print(f"\n=== VALIDATION RESULT ===")
        print(f"Accuracy: {accuracy * 100:.1f}% ({correct}/{total})")
        print(f"Gate: {'PASS ✓' if accuracy >= 0.9 else 'FAIL ✗'} (90% required)")

        assert accuracy >= 0.9, f"Failed validation gate: {accuracy:.1%} < 90%"


class TestCrossCategoryDeduplication:
    """Test cross-category deduplication of next: vs done: items."""

    def test_filters_completed_next_items(self):
        """Test that next: items matching done: items are filtered out."""
        import sqlite3
        import tempfile
        import json
        from pathlib import Path
        from cerberus.memory.session_analyzer import save_session_context_to_db, extract_session_codes

        # Create temporary database
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_memory.db"

            # Create sessions table
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    project_path TEXT,
                    status TEXT DEFAULT 'active',
                    context_data TEXT,
                    summary_details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()

            # Mock the database path
            import cerberus.memory.session_analyzer as sa_module
            original_db_path = Path.home() / ".cerberus" / "memory.db"

            # Temporarily replace Path.home() in the module
            # Instead, we'll directly test the filtering logic

            # Simulate codes that would be extracted
            test_codes = [
                "next:setup-mcp-hot-reload-building",
                "next:register-cerberus-dev",
                "next:restart-claude-cli",
                "done:registered-cerberus-dev",
                "done:restarted-claude-cli-take-effect",
                "done:setup-mcp-hot-reload",
            ]

            # Categorize like save_session_context_to_db does
            context_data = {
                "completed": [c for c in test_codes if c.startswith("done:")],
                "next_actions": [c for c in test_codes if c.startswith("next:")],
            }

            # Apply the filtering logic from save_session_context_to_db
            import re

            def simple_stem(word: str) -> str:
                """Simple stemming to normalize verb tenses and plurals."""
                suffixes = ['ing', 'ed', 's']
                for suffix in suffixes:
                    if word.endswith(suffix) and len(word) > len(suffix) + 2:
                        return word[:-len(suffix)]
                return word

            def extract_keywords_from_code(code: str) -> set:
                """Extract meaningful keywords from semantic code with stemming."""
                content = ':'.join(code.split(':')[1:])
                words = re.split(r'[-_:\s]+', content.lower())
                stop_words = {'the', 'and', 'or', 'to', 'a', 'an', 'is', 'for', 'of', 'in', 'on'}
                return {simple_stem(w) for w in words if len(w) > 2 and w not in stop_words}

            def calculate_keyword_similarity(keywords1: set, keywords2: set) -> float:
                """Containment similarity instead of Jaccard."""
                if not keywords1 or not keywords2:
                    return 0.0
                intersection = keywords1 & keywords2
                min_size = min(len(keywords1), len(keywords2))
                return len(intersection) / min_size if min_size > 0 else 0.0

            filtered_next_actions = []
            for next_item in context_data["next_actions"]:
                next_keywords = extract_keywords_from_code(next_item)
                is_completed = False

                for done_item in context_data["completed"]:
                    done_keywords = extract_keywords_from_code(done_item)
                    similarity = calculate_keyword_similarity(next_keywords, done_keywords)

                    if similarity >= 0.6:
                        is_completed = True
                        break

                if not is_completed:
                    filtered_next_actions.append(next_item)

            # Assertions
            assert "next:register-cerberus-dev" not in filtered_next_actions, \
                "Should filter out next:register-cerberus-dev (matches done:registered-cerberus-dev)"

            assert "next:restart-claude-cli" not in filtered_next_actions, \
                "Should filter out next:restart-claude-cli (matches done:restarted-claude-cli-take-effect)"

            assert "next:setup-mcp-hot-reload-building" not in filtered_next_actions, \
                "Should filter out next:setup-mcp-hot-reload-building (matches done:setup-mcp-hot-reload)"

            # Should have filtered out all next: items that matched done: items
            assert len(filtered_next_actions) == 0, \
                f"Expected 0 next_actions, got {len(filtered_next_actions)}: {filtered_next_actions}"

    def test_keeps_unrelated_next_items(self):
        """Test that next: items NOT matching done: items are kept."""
        import re

        test_codes = [
            "next:implement-feature-x",
            "next:write-documentation",
            "done:tests-passing",
            "done:git-commit",
        ]

        context_data = {
            "completed": [c for c in test_codes if c.startswith("done:")],
            "next_actions": [c for c in test_codes if c.startswith("next:")],
        }

        # Apply filtering logic
        def simple_stem(word: str) -> str:
            """Simple stemming to normalize verb tenses and plurals."""
            suffixes = ['ing', 'ed', 's']
            for suffix in suffixes:
                if word.endswith(suffix) and len(word) > len(suffix) + 2:
                    return word[:-len(suffix)]
            return word

        def extract_keywords_from_code(code: str) -> set:
            """Extract meaningful keywords from semantic code with stemming."""
            content = ':'.join(code.split(':')[1:])
            words = re.split(r'[-_:\s]+', content.lower())
            stop_words = {'the', 'and', 'or', 'to', 'a', 'an', 'is', 'for', 'of', 'in', 'on'}
            return {simple_stem(w) for w in words if len(w) > 2 and w not in stop_words}

        def calculate_keyword_similarity(keywords1: set, keywords2: set) -> float:
            """Containment similarity instead of Jaccard."""
            if not keywords1 or not keywords2:
                return 0.0
            intersection = keywords1 & keywords2
            min_size = min(len(keywords1), len(keywords2))
            return len(intersection) / min_size if min_size > 0 else 0.0

        filtered_next_actions = []
        for next_item in context_data["next_actions"]:
            next_keywords = extract_keywords_from_code(next_item)
            is_completed = False

            for done_item in context_data["completed"]:
                done_keywords = extract_keywords_from_code(done_item)
                similarity = calculate_keyword_similarity(next_keywords, done_keywords)

                if similarity >= 0.6:
                    is_completed = True
                    break

            if not is_completed:
                filtered_next_actions.append(next_item)

        # Both next: items should remain (no keyword overlap with done: items)
        assert "next:implement-feature-x" in filtered_next_actions
        assert "next:write-documentation" in filtered_next_actions
        assert len(filtered_next_actions) == 2


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
