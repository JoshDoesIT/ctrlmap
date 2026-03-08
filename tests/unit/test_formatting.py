"""Tests for ctrlmap.export._formatting utilities."""

from __future__ import annotations

from ctrlmap.export._formatting import truncate


class TestTruncate:
    """Tests for the shared truncate helper."""

    def test_short_text_unchanged(self) -> None:
        """Text under max_len is returned as-is."""
        assert truncate("hello", max_len=10) == "hello"

    def test_exact_length_unchanged(self) -> None:
        """Text exactly at max_len is not truncated."""
        text = "a" * 20
        assert truncate(text, max_len=20) == text

    def test_long_text_truncated(self) -> None:
        """Text over max_len is truncated with ellipsis."""
        text = "a" * 25
        result = truncate(text, max_len=20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_newlines_collapsed(self) -> None:
        """Newlines are replaced with spaces."""
        assert truncate("line1\nline2\nline3", max_len=150) == "line1 line2 line3"

    def test_whitespace_stripped(self) -> None:
        """Leading/trailing whitespace is stripped."""
        assert truncate("  hello  ", max_len=150) == "hello"

    def test_default_max_len(self) -> None:
        """Default max_len is 150."""
        text = "a" * 200
        result = truncate(text)
        assert len(result) == 150
