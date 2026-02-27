"""Tests for the Ollama LLM client.

TDD RED phase: Story #18 — ollama-python SDK integration.
Ref: GitHub Issue #18.

All tests mock the Ollama server to avoid requiring a running instance.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestOllamaClient:
    """Story #18: Ollama LLM integration for rationale generation."""

    def test_ollama_connection_check(self) -> None:
        """Client verifies Ollama is reachable before generating."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama") as mock_ollama:
            mock_ollama.list.return_value = MagicMock(models=[{"name": "llama3"}])
            client = OllamaClient()
            assert client.is_available() is True

    def test_ollama_not_running_raises_descriptive_error(self) -> None:
        """When Ollama is not running, a clear error is raised."""
        from ctrlmap.llm.client import OllamaClient, OllamaConnectionError

        with patch("ctrlmap.llm.client.ollama") as mock_ollama:
            mock_ollama.list.side_effect = Exception("Connection refused")
            client = OllamaClient()
            with pytest.raises(OllamaConnectionError, match="not running"):
                client.check_connection()

    def test_generate_rationale_returns_string(self) -> None:
        """generate() returns the LLM response content as a string."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama") as mock_ollama:
            mock_ollama.chat.return_value = MagicMock(
                message=MagicMock(content="This policy addresses the control requirement.")
            )
            client = OllamaClient(model="llama3")
            result = client.generate(
                control_text="AC-1: Access Control Policy.",
                chunk_text="All employees must follow access control procedures.",
            )
            assert isinstance(result, str)
            assert len(result) > 0

    def test_configurable_model_selection(self) -> None:
        """Client uses the configured model name in chat calls."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama") as mock_ollama:
            mock_ollama.chat.return_value = MagicMock(message=MagicMock(content="Response text."))
            client = OllamaClient(model="phi2")
            client.generate(
                control_text="SC-28: Protection of Information at Rest.",
                chunk_text="Encrypt all data at rest.",
            )
            call_args = mock_ollama.chat.call_args
            assert call_args.kwargs.get("model") == "phi2" or call_args[1].get("model") == "phi2"
