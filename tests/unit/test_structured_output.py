"""Tests for union-type structured LLM outputs.

TDD RED phase: Story #19, MappingRationale | InsufficientEvidence.
Ref: GitHub Issue #19.

All tests mock the Ollama client to avoid requiring a running instance.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from ctrlmap.models.schemas import ComplianceLevel, InsufficientEvidence, MappingRationale


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


class TestMajorityVoteAggregation:
    """P4: Rationale selection uses majority vote, not max-compliance."""

    def test_majority_fc_wins(self) -> None:
        """When majority of rationales are FC, result should be FC."""
        from ctrlmap.llm.structured_output import select_best_rationale

        rationales = [
            MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.FULLY_COMPLIANT,
                confidence_score=0.9,
                explanation="FC rationale 1",
            ),
            MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.FULLY_COMPLIANT,
                confidence_score=0.85,
                explanation="FC rationale 2",
            ),
            MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.FULLY_COMPLIANT,
                confidence_score=0.8,
                explanation="FC rationale 3",
            ),
            MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.PARTIALLY_COMPLIANT,
                confidence_score=0.95,
                explanation="PC rationale 1",
            ),
            MappingRationale(
                is_compliant=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                confidence_score=0.7,
                explanation="NC rationale 1",
            ),
        ]
        result = select_best_rationale(rationales)
        assert result is not None
        assert result.compliance_level == ComplianceLevel.FULLY_COMPLIANT

    def test_majority_nc_wins_over_single_fc(self) -> None:
        """Four NC + one FC should select NC, not the single FC."""
        from ctrlmap.llm.structured_output import select_best_rationale

        rationales = [
            MappingRationale(
                is_compliant=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                confidence_score=0.8,
                explanation="NC rationale",
            ),
            MappingRationale(
                is_compliant=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                confidence_score=0.7,
                explanation="NC rationale 2",
            ),
            MappingRationale(
                is_compliant=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                confidence_score=0.75,
                explanation="NC rationale 3",
            ),
            MappingRationale(
                is_compliant=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                confidence_score=0.65,
                explanation="NC rationale 4",
            ),
            MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.FULLY_COMPLIANT,
                confidence_score=0.95,
                explanation="Single FC (shouldn't win)",
            ),
        ]
        result = select_best_rationale(rationales)
        assert result is not None
        assert result.compliance_level == ComplianceLevel.NON_COMPLIANT

    def test_tie_breaks_conservative(self) -> None:
        """On a tie, prefer the LOWER compliance level (conservative)."""
        from ctrlmap.llm.structured_output import select_best_rationale

        rationales = [
            MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.PARTIALLY_COMPLIANT,
                confidence_score=0.8,
                explanation="PC rationale 1",
            ),
            MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.PARTIALLY_COMPLIANT,
                confidence_score=0.75,
                explanation="PC rationale 2",
            ),
            MappingRationale(
                is_compliant=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                confidence_score=0.9,
                explanation="NC rationale 1",
            ),
            MappingRationale(
                is_compliant=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                confidence_score=0.85,
                explanation="NC rationale 2",
            ),
        ]
        result = select_best_rationale(rationales)
        assert result is not None
        # Tie between 2 PC and 2 NC — conservative = non_compliant
        assert result.compliance_level == ComplianceLevel.NON_COMPLIANT

    def test_single_rationale_returns_itself(self) -> None:
        """A single rationale is returned regardless of level."""
        from ctrlmap.llm.structured_output import select_best_rationale

        rationale = MappingRationale(
            is_compliant=True,
            compliance_level=ComplianceLevel.PARTIALLY_COMPLIANT,
            confidence_score=0.7,
            explanation="Only rationale",
        )
        result = select_best_rationale([rationale])
        assert result is not None
        assert result.compliance_level == ComplianceLevel.PARTIALLY_COMPLIANT


class TestExplanationConsistencyGuard:
    """FC rationales with gap-admitting explanations must be downgraded to PC."""

    def test_fc_with_does_not_specify_is_downgraded(self) -> None:
        """'does not specify' in explanation should downgrade FC to PC."""
        from ctrlmap.llm.structured_output import _parse_response

        response = json.dumps({
            "type": "MappingRationale",
            "is_compliant": True,
            "compliance_level": "fully_compliant",
            "confidence_score": 0.85,
            "explanation": "The policy covers encryption but does not specify "
            "which cryptographic algorithms or protocols are approved.",
        })
        result = _parse_response(response)
        assert isinstance(result, MappingRationale)
        assert result.compliance_level == ComplianceLevel.PARTIALLY_COMPLIANT, (
            f"Expected PC due to 'does not specify', got {result.compliance_level}"
        )

    def test_fc_with_does_not_address_is_downgraded(self) -> None:
        """'does not address' in explanation should downgrade FC to PC."""
        from ctrlmap.llm.structured_output import _parse_response

        response = json.dumps({
            "type": "MappingRationale",
            "is_compliant": True,
            "compliance_level": "fully_compliant",
            "confidence_score": 0.80,
            "explanation": "The policy does not address the specific requirement "
            "of backing up audit log files to a central server.",
        })
        result = _parse_response(response)
        assert isinstance(result, MappingRationale)
        assert result.compliance_level == ComplianceLevel.PARTIALLY_COMPLIANT

    def test_fc_with_partially_covers_is_downgraded(self) -> None:
        """'partially covers' in explanation should downgrade FC to PC."""
        from ctrlmap.llm.structured_output import _parse_response

        response = json.dumps({
            "type": "MappingRationale",
            "is_compliant": True,
            "compliance_level": "fully_compliant",
            "confidence_score": 0.82,
            "explanation": "The policy partially covers the requirement "
            "but lacks specific details on implementation timelines.",
        })
        result = _parse_response(response)
        assert isinstance(result, MappingRationale)
        assert result.compliance_level == ComplianceLevel.PARTIALLY_COMPLIANT

    def test_fc_with_missing_is_downgraded(self) -> None:
        """'missing' in explanation should downgrade FC to PC."""
        from ctrlmap.llm.structured_output import _parse_response

        response = json.dumps({
            "type": "MappingRationale",
            "is_compliant": True,
            "compliance_level": "fully_compliant",
            "confidence_score": 0.78,
            "explanation": "The policy covers most requirements but is "
            "missing periodic inspection procedures.",
        })
        result = _parse_response(response)
        assert isinstance(result, MappingRationale)
        assert result.compliance_level == ComplianceLevel.PARTIALLY_COMPLIANT

    def test_clean_fc_explanation_stays_fc(self) -> None:
        """FC with a clean explanation should stay FC."""
        from ctrlmap.llm.structured_output import _parse_response

        response = json.dumps({
            "type": "MappingRationale",
            "is_compliant": True,
            "compliance_level": "fully_compliant",
            "confidence_score": 0.92,
            "explanation": "The policy fully addresses all aspects of this "
            "control through comprehensive access management procedures.",
        })
        result = _parse_response(response)
        assert isinstance(result, MappingRationale)
        assert result.compliance_level == ComplianceLevel.FULLY_COMPLIANT

    def test_pc_with_gap_phrases_stays_pc(self) -> None:
        """PC with gap phrases should remain PC (no double-downgrade)."""
        from ctrlmap.llm.structured_output import _parse_response

        response = json.dumps({
            "type": "MappingRationale",
            "is_compliant": True,
            "compliance_level": "partially_compliant",
            "confidence_score": 0.75,
            "explanation": "The policy does not specify periodic review timelines.",
        })
        result = _parse_response(response)
        assert isinstance(result, MappingRationale)
        assert result.compliance_level == ComplianceLevel.PARTIALLY_COMPLIANT


class TestAggregateExplanation:
    """Verify that aggregate_rationales preserves LLM explanations.

    The aggregation should use the best chunk's LLM-generated explanation
    as the primary text, not replace it with a synthetic 'Combined evidence
    from N chunks covers X/Y...' message that can contradict visible evidence.
    """

    def test_downgrade_preserves_best_explanation(self) -> None:
        """When aggregation downgrades FC → PC, the best rationale's
        explanation should be preserved (not replaced by synthetic text).
        """
        from ctrlmap.llm.structured_output import aggregate_rationales

        rationales = [
            MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.FULLY_COMPLIANT,
                confidence_score=0.9,
                explanation="The policy addresses encryption at rest comprehensively.",
            ),
        ]
        sub_reqs = [[
            {"requirement": "Encryption", "covered": True},
            {"requirement": "Key management", "covered": False},
        ]]
        result = aggregate_rationales(
            rationales=rationales, sub_requirements=sub_reqs,
        )
        assert result is not None
        # The best rationale's explanation should be preserved
        assert "addresses encryption at rest" in result.explanation
        # Should NOT start with the synthetic "Combined evidence" prefix
        assert not result.explanation.startswith("Combined evidence")

    def test_upgrade_uses_coverage_explanation(self) -> None:
        """When aggregation upgrades PC → FC, a coverage-based explanation
        should be generated (not the best chunk's gap-mentioning text).
        """
        from ctrlmap.llm.structured_output import aggregate_rationales

        rationales = [
            MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.PARTIALLY_COMPLIANT,
                confidence_score=0.9,
                explanation="The policy requires full-disk encryption on all endpoints.",
            ),
            MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.PARTIALLY_COMPLIANT,
                confidence_score=0.85,
                explanation="Key rotation is performed according to defined cryptoperiods.",
            ),
        ]
        sub_reqs = [
            [
                {"requirement": "Encryption", "covered": True},
                {"requirement": "Key management", "covered": False},
            ],
            [
                {"requirement": "Encryption", "covered": False},
                {"requirement": "Key management", "covered": True},
            ],
        ]
        result = aggregate_rationales(
            rationales=rationales, sub_requirements=sub_reqs,
        )
        assert result is not None
        # Upgrade explanation should list what's covered
        assert "all 2 sub-requirements" in result.explanation
        assert result.compliance_level == ComplianceLevel.FULLY_COMPLIANT


