"""Tests for JSON extraction utilities.

TDD RED phase: fix CoT-induced batch parse failures where reasoning
text before the JSON array contains brackets like [topic].
"""

from __future__ import annotations

from ctrlmap.llm._json_utils import extract_json_array, extract_json_object


class TestExtractJsonArray:
    """extract_json_array must handle chain-of-thought preamble."""

    def test_plain_json_array(self) -> None:
        """Direct JSON array should parse cleanly."""
        raw = '[{"verdict": "Relevant"}]'
        result = extract_json_array(raw)
        assert len(result) == 1
        assert result[0]["verdict"] == "Relevant"

    def test_cot_reasoning_with_brackets_before_array(self) -> None:
        """CoT text containing brackets must not fool the parser.

        The LLM may emit reasoning like:
            Chunk 1 is about [access control] which is relevant...
            [{"verdict": "Relevant", ...}]
        The parser must pick the JSON array, not "[access control]".
        """
        raw = (
            "Let me analyze each chunk.\n"
            "Chunk 1 discusses [access control policies] which is relevant.\n"
            "Chunk 2 covers [network segmentation] which is not.\n\n"
            '[{"chunk_index": 1, "verdict": "Relevant"}, '
            '{"chunk_index": 2, "verdict": "InsufficientEvidence"}]'
        )
        result = extract_json_array(raw)
        assert len(result) == 2
        assert result[0]["verdict"] == "Relevant"
        assert result[1]["verdict"] == "InsufficientEvidence"

    def test_markdown_fenced_array(self) -> None:
        """Array inside markdown code fences should be extracted."""
        raw = "Here is the result:\n```json\n" '[{"v": "ok"}]\n' "```"
        result = extract_json_array(raw)
        assert len(result) == 1
        assert result[0]["v"] == "ok"

    def test_empty_string_returns_empty(self) -> None:
        """Empty input should return empty list."""
        assert extract_json_array("") == []

    def test_no_json_returns_empty(self) -> None:
        """Plain text with no JSON should return empty list."""
        assert extract_json_array("No JSON here.") == []


class TestExtractJsonObject:
    """extract_json_object handles preamble and fences."""

    def test_plain_json_object(self) -> None:
        """Direct JSON object should be returned."""
        raw = '{"key": "value"}'
        result = extract_json_object(raw)
        assert result == '{"key": "value"}'

    def test_cot_preamble_before_object(self) -> None:
        """CoT reasoning before JSON object should not break extraction."""
        raw = (
            "Analyzing the control...\n"
            "The policy [access control] appears relevant.\n\n"
            '{"is_compliant": true, "explanation": "Policy covers AC."}'
        )
        result = extract_json_object(raw)
        parsed = __import__("json").loads(result)
        assert parsed["is_compliant"] is True
