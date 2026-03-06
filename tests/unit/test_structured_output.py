"""Tests for union-type structured LLM outputs.

TDD RED phase: Story #19, MappingRationale | InsufficientEvidence.
Ref: GitHub Issue #19.

All tests mock the Ollama client to avoid requiring a running instance.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from ctrlmap.models.schemas import InsufficientEvidence, MappingRationale


class TestStructuredOutput:
    """Story #19: Union-type structured outputs."""

    def test_structured_output_returns_mapping_rationale(self) -> None:
        """When evidence is sufficient, returns MappingRationale."""
        from ctrlmap.llm.structured_output import generate_rationale

        llm_response = json.dumps(
            {
                "type": "MappingRationale",
                "is_compliant": True,
                "confidence_score": 0.92,
                "explanation": "Policy requires quarterly account reviews.",
            }
        )

        with patch("ctrlmap.llm.structured_output.OllamaClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.generate.return_value = llm_response

            result = generate_rationale(
                control_text="AC-2: Account Management.",
                chunk_text="All user accounts must be reviewed quarterly.",
            )
            assert isinstance(result, MappingRationale)
            assert result.is_compliant is True
            assert result.confidence_score == 0.92

    def test_structured_output_returns_insufficient_evidence(self) -> None:
        """When evidence is insufficient, returns InsufficientEvidence."""
        from ctrlmap.llm.structured_output import generate_rationale

        llm_response = json.dumps(
            {
                "type": "InsufficientEvidence",
                "reason": "No policy chunks reference encryption at rest.",
                "required_context": "Policy language addressing data encryption.",
            }
        )

        with patch("ctrlmap.llm.structured_output.OllamaClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.generate.return_value = llm_response

            result = generate_rationale(
                control_text="SC-28: Protection of Information at Rest.",
                chunk_text="Standard operational procedures for data handling.",
            )
            assert isinstance(result, InsufficientEvidence)
            assert "encryption" in result.reason.lower()

    def test_structured_output_validates_pydantic_schema(self) -> None:
        """Invalid LLM output triggers fallback to InsufficientEvidence."""
        from ctrlmap.llm.structured_output import generate_rationale

        # Invalid JSON, missing required fields
        llm_response = json.dumps({"type": "MappingRationale", "garbage": True})

        with patch("ctrlmap.llm.structured_output.OllamaClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.generate.return_value = llm_response

            result = generate_rationale(
                control_text="AC-1: Policy.",
                chunk_text="Some policy text for testing this scenario.",
            )
            # Should fall back to InsufficientEvidence on validation failure
            assert isinstance(result, InsufficientEvidence)

    def test_structured_output_prevents_hallucination(self) -> None:
        """Non-JSON or completely invalid output falls back safely."""
        from ctrlmap.llm.structured_output import generate_rationale

        with patch("ctrlmap.llm.structured_output.OllamaClient") as MockClient:
            mock_instance = MockClient.return_value
            # LLM returns plain text instead of JSON
            mock_instance.generate.return_value = "I think this policy is compliant."

            result = generate_rationale(
                control_text="AC-1: Policy.",
                chunk_text="Some policy text.",
            )
            assert isinstance(result, InsufficientEvidence)
            assert "parse" in result.reason.lower() or "invalid" in result.reason.lower()


class TestGapRationale:
    """Gap rationale generation for controls with no supporting evidence."""

    def test_generate_gap_rationale_returns_mapping_rationale(self) -> None:
        """When LLM responds correctly, returns a valid MappingRationale."""
        from ctrlmap.llm.structured_output import generate_gap_rationale

        llm_response = json.dumps(
            {
                "type": "MappingRationale",
                "is_compliant": False,
                "confidence_score": 0.10,
                "explanation": "No policy documentation addresses this control.",
            }
        )

        with patch("ctrlmap.llm.structured_output.OllamaClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.generate_gap.return_value = llm_response

            result = generate_gap_rationale(
                control_text="6.2.1: Secure development practices.",
            )
            assert isinstance(result, MappingRationale)
            assert result.is_compliant is False

    def test_generate_gap_rationale_falls_back_on_invalid_output(self) -> None:
        """Falls back to InsufficientEvidence when LLM output is invalid."""
        from ctrlmap.llm.structured_output import generate_gap_rationale

        with patch("ctrlmap.llm.structured_output.OllamaClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.generate_gap.return_value = "Not valid JSON at all."

            result = generate_gap_rationale(
                control_text="6.2.1: Secure development.",
            )
            assert isinstance(result, InsufficientEvidence)
