"""Tests for the Ollama LLM client.

TDD RED phase: Story #18, ollama-python SDK integration.
Ref: GitHub Issue #18.

All tests mock the Ollama server to avoid requiring a running instance.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

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

    def test_relevance_prompt_includes_subject_mismatch_rule(self) -> None:
        """Relevance prompt must instruct the LLM to reject subject/object mismatches.

        E.g., 'reviewing access rights' is NOT evidence for 'reviewing the
        information security policy' — the ACTION is the same (reviewing)
        but the SUBJECT is different (access rights vs. the policy itself).
        """
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama") as mock_ollama:
            mock_ollama.chat.return_value = MagicMock(
                message=MagicMock(content='{"relevant": false}')
            )
            client = OllamaClient()
            client.verify_chunk_relevance(
                control_text=(
                    "The information security policy is: Reviewed at least once every 12 months."
                ),
                chunk_text=("User access rights must be reviewed at least every six months."),
                requirement_family="Requirement 12",
            )

            # Verify the prompt sent to the LLM contains subject-mismatch guidance
            call_args = mock_ollama.chat.call_args
            messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
            prompt_text = messages[0]["content"].lower()
            assert "subject" in prompt_text or "object of the action" in prompt_text, (
                "Relevance prompt must include subject/object mismatch guidance"
            )

    def test_rationale_prompt_includes_subject_mismatch_rule(self) -> None:
        """Rationale prompt must warn against conflating similar verbs with
        different subjects (e.g., 'review policy' vs. 'review access')."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama") as mock_ollama:
            mock_ollama.chat.return_value = MagicMock(
                message=MagicMock(content='{"type": "MappingRationale"}')
            )
            client = OllamaClient()
            client.generate(
                control_text="The information security policy is reviewed annually.",
                chunk_text="User access rights are reviewed every six months.",
            )

            call_args = mock_ollama.chat.call_args
            messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
            prompt_text = messages[0]["content"].lower()
            assert "subject" in prompt_text or "object of the action" in prompt_text, (
                "Rationale prompt must include subject/object mismatch guidance"
            )


class TestOllamaDeterminism:
    """Temperature=0 must be set on all LLM calls for reproducibility."""

    def test_generate_uses_temperature_zero(self) -> None:
        """generate() passes temperature:0 to ollama for deterministic output."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama") as mock_ollama:
            mock_ollama.chat.return_value = MagicMock(
                message=MagicMock(content='{"type": "MappingRationale"}')
            )
            client = OllamaClient()
            client.generate(
                control_text="AC-1: Access Control Policy.",
                chunk_text="All employees must follow access control procedures.",
            )

            call_args = mock_ollama.chat.call_args
            options = call_args.kwargs.get("options") or call_args[1].get("options", {})
            assert options.get("temperature") == 0, (
                "generate() must pass temperature=0 for deterministic output"
            )

    def test_generate_gap_uses_temperature_zero(self) -> None:
        """generate_gap() passes temperature:0 to ollama for deterministic output."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama") as mock_ollama:
            mock_ollama.chat.return_value = MagicMock(
                message=MagicMock(content='{"type": "MappingRationale"}')
            )
            client = OllamaClient()
            client.generate_gap(control_text="SC-28: Protection of Information at Rest.")

            call_args = mock_ollama.chat.call_args
            options = call_args.kwargs.get("options") or call_args[1].get("options", {})
            assert options.get("temperature") == 0, (
                "generate_gap() must pass temperature=0 for deterministic output"
            )


class TestOllamaStructuredLogging:
    """Structured JSON logging must be emitted for every LLM call."""

    def test_generate_emits_structured_log(self, caplog: pytest.LogCaptureFixture) -> None:
        """generate() logs a structured JSON entry with method, model, and latency."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama") as mock_ollama:
            mock_ollama.chat.return_value = MagicMock(
                message=MagicMock(content='{"type": "MappingRationale"}')
            )
            with caplog.at_level(logging.DEBUG, logger="ctrlmap.llm"):
                client = OllamaClient()
                client.generate(
                    control_text="AC-1: Access Control Policy.",
                    chunk_text="All employees must follow access control procedures.",
                )

        log_entries = [r for r in caplog.records if r.name == "ctrlmap.llm"]
        assert len(log_entries) >= 1, "generate() must emit a structured log entry"
        log_data = json.loads(log_entries[0].message)
        assert log_data["method"] == "generate"
        assert "model" in log_data
        assert "latency_ms" in log_data

    def test_verify_chunk_relevance_emits_structured_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """verify_chunk_relevance() logs a structured JSON entry."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama") as mock_ollama:
            mock_ollama.chat.return_value = MagicMock(
                message=MagicMock(content='{"relevant": true}')
            )
            with caplog.at_level(logging.DEBUG, logger="ctrlmap.llm"):
                client = OllamaClient()
                client.verify_chunk_relevance(
                    control_text="AC-1: Access Control Policy.",
                    chunk_text="All employees must follow access control procedures.",
                )

        log_entries = [r for r in caplog.records if r.name == "ctrlmap.llm"]
        assert len(log_entries) >= 1
        log_data = json.loads(log_entries[0].message)
        assert log_data["method"] == "verify_chunk_relevance"

    def test_classify_control_type_emits_structured_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """classify_control_type() logs a structured JSON entry."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama") as mock_ollama:
            mock_ollama.chat.return_value = MagicMock(
                message=MagicMock(content='{"is_meta": false}')
            )
            with caplog.at_level(logging.DEBUG, logger="ctrlmap.llm"):
                client = OllamaClient()
                client.classify_control_type(
                    control_text="AC-1: Access Control Policy.",
                )

        log_entries = [r for r in caplog.records if r.name == "ctrlmap.llm"]
        assert len(log_entries) >= 1
        log_data = json.loads(log_entries[0].message)
        assert log_data["method"] == "classify_control_type"

    def test_generate_gap_emits_structured_log(self, caplog: pytest.LogCaptureFixture) -> None:
        """generate_gap() logs a structured JSON entry."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama") as mock_ollama:
            mock_ollama.chat.return_value = MagicMock(
                message=MagicMock(content='{"type": "MappingRationale"}')
            )
            with caplog.at_level(logging.DEBUG, logger="ctrlmap.llm"):
                client = OllamaClient()
                client.generate_gap(
                    control_text="SC-28: Protection of Information at Rest.",
                )

        log_entries = [r for r in caplog.records if r.name == "ctrlmap.llm"]
        assert len(log_entries) >= 1
        log_data = json.loads(log_entries[0].message)
        assert log_data["method"] == "generate_gap"


class TestOllamaAsyncClient:
    """Async LLM client methods for concurrent enrichment pipeline."""

    @pytest.mark.asyncio()
    async def test_call_llm_async_returns_string(self) -> None:
        """call_llm_async() returns the LLM response as a string."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama.AsyncClient") as mock_async_cls:
            mock_instance = MagicMock()
            mock_instance.chat = AsyncMock(
                return_value=MagicMock(message=MagicMock(content="response text"))
            )
            mock_async_cls.return_value = mock_instance

            client = OllamaClient(model="llama3")
            result = await client.call_llm_async("test prompt", "test_method")
            assert isinstance(result, str)
            assert result == "response text"

    @pytest.mark.asyncio()
    async def test_call_llm_async_uses_temperature_zero(self) -> None:
        """Async LLM calls pass temperature=0 for deterministic output."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama.AsyncClient") as mock_async_cls:
            mock_instance = MagicMock()
            mock_instance.chat = AsyncMock(
                return_value=MagicMock(message=MagicMock(content="response"))
            )
            mock_async_cls.return_value = mock_instance

            client = OllamaClient()
            await client.call_llm_async("prompt", "test")

            call_args = mock_instance.chat.call_args
            options = call_args.kwargs.get("options") or call_args[1].get("options", {})
            assert options.get("temperature") == 0

    @pytest.mark.asyncio()
    async def test_verify_chunk_relevance_async_returns_bool(self) -> None:
        """verify_chunk_relevance_async() returns True/False like its sync counterpart."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama.AsyncClient") as mock_async_cls:
            mock_instance = MagicMock()
            mock_instance.chat = AsyncMock(
                return_value=MagicMock(message=MagicMock(content='{"relevant": true}'))
            )
            mock_async_cls.return_value = mock_instance

            client = OllamaClient()
            result = await client.verify_chunk_relevance_async(
                control_text="AC-1: Policy.",
                chunk_text="All employees must follow access control procedures.",
            )
            assert result is True

    @pytest.mark.asyncio()
    async def test_generate_async_returns_string(self) -> None:
        """generate_async() returns the raw LLM response."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama.AsyncClient") as mock_async_cls:
            mock_instance = MagicMock()
            mock_instance.chat = AsyncMock(
                return_value=MagicMock(message=MagicMock(content="rationale text"))
            )
            mock_async_cls.return_value = mock_instance

            client = OllamaClient()
            result = await client.generate_async(
                control_text="AC-1: Policy.",
                chunk_text="All employees must follow access control procedures.",
            )
            assert result == "rationale text"

    @pytest.mark.asyncio()
    async def test_classify_control_type_async_returns_bool(self) -> None:
        """classify_control_type_async() returns True/False."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama.AsyncClient") as mock_async_cls:
            mock_instance = MagicMock()
            mock_instance.chat = AsyncMock(
                return_value=MagicMock(message=MagicMock(content='{"is_meta": false}'))
            )
            mock_async_cls.return_value = mock_instance

            client = OllamaClient()
            result = await client.classify_control_type_async(
                control_text="AC-1: Access Control Policy.",
            )
            assert result is False

    @pytest.mark.asyncio()
    async def test_generate_gap_async_returns_string(self) -> None:
        """generate_gap_async() returns the raw LLM response."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama.AsyncClient") as mock_async_cls:
            mock_instance = MagicMock()
            mock_instance.chat = AsyncMock(
                return_value=MagicMock(message=MagicMock(content="gap rationale"))
            )
            mock_async_cls.return_value = mock_instance

            client = OllamaClient()
            result = await client.generate_gap_async(
                control_text="SC-28: Protection of Information at Rest.",
            )
            assert result == "gap rationale"

    @pytest.mark.asyncio()
    async def test_call_llm_async_emits_structured_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Async LLM calls emit structured JSON logs like sync calls."""
        from ctrlmap.llm.client import OllamaClient

        with patch("ctrlmap.llm.client.ollama.AsyncClient") as mock_async_cls:
            mock_instance = MagicMock()
            mock_instance.chat = AsyncMock(
                return_value=MagicMock(message=MagicMock(content="response"))
            )
            mock_async_cls.return_value = mock_instance

            with caplog.at_level(logging.DEBUG, logger="ctrlmap.llm"):
                client = OllamaClient()
                await client.call_llm_async("prompt", "test_method")

        log_entries = [r for r in caplog.records if r.name == "ctrlmap.llm"]
        assert len(log_entries) >= 1
        log_data = json.loads(log_entries[0].message)
        assert log_data["method"] == "test_method"
        assert "latency_ms" in log_data

    @pytest.mark.asyncio()
    async def test_evaluate_chunk_async_returns_rationale_for_relevant(self) -> None:
        """evaluate_chunk_async() returns MappingRationale for relevant chunks."""
        from ctrlmap.llm.client import OllamaClient
        from ctrlmap.models.schemas import MappingRationale

        rationale_json = json.dumps(
            {
                "type": "MappingRationale",
                "is_compliant": True,
                "compliance_level": "fully_compliant",
                "confidence_score": 0.95,
                "sub_requirements": [],
                "explanation": "The policy addresses the control.",
            }
        )

        with patch("ctrlmap.llm.client.ollama.AsyncClient") as mock_async_cls:
            mock_instance = MagicMock()
            mock_instance.chat = AsyncMock(
                return_value=MagicMock(message=MagicMock(content=rationale_json))
            )
            mock_async_cls.return_value = mock_instance

            client = OllamaClient()
            result = await client.evaluate_chunk_async(
                control_text="AC-1: Access Control Policy.",
                chunk_text="All employees must follow access control procedures.",
            )
            assert isinstance(result, MappingRationale)
            assert result.is_compliant is True

    @pytest.mark.asyncio()
    async def test_evaluate_chunk_async_returns_insufficient_for_irrelevant(self) -> None:
        """evaluate_chunk_async() returns InsufficientEvidence for irrelevant chunks."""
        from ctrlmap.llm.client import OllamaClient
        from ctrlmap.models.schemas import InsufficientEvidence

        insufficient_json = json.dumps(
            {
                "type": "InsufficientEvidence",
                "reason": "The chunk is about cafeteria hours.",
                "required_context": "Policy about access control.",
            }
        )

        with patch("ctrlmap.llm.client.ollama.AsyncClient") as mock_async_cls:
            mock_instance = MagicMock()
            mock_instance.chat = AsyncMock(
                return_value=MagicMock(message=MagicMock(content=insufficient_json))
            )
            mock_async_cls.return_value = mock_instance

            client = OllamaClient()
            result = await client.evaluate_chunk_async(
                control_text="AC-1: Access Control Policy.",
                chunk_text="The cafeteria is open Monday through Friday.",
            )
            assert isinstance(result, InsufficientEvidence)
