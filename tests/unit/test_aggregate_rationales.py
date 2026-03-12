"""Tests for sub-requirement aggregation across multiple chunk rationales."""

from __future__ import annotations

from ctrlmap.models.schemas import ComplianceLevel, MappingRationale


class TestAggregateRationales:
    """Tests for aggregate_rationales() — merging sub-req coverage across chunks."""

    def test_combines_coverage_from_multiple_chunks(self) -> None:
        """Two partial rationales covering different sub-reqs → fully_compliant."""
        from ctrlmap.llm.structured_output import aggregate_rationales

        # Chunk 1 covers sub-reqs A and B
        r1 = MappingRationale(
            is_compliant=True,
            compliance_level=ComplianceLevel.PARTIALLY_COMPLIANT,
            confidence_score=0.9,
            explanation="Covers testing for wireless APs quarterly.",
        )
        sub1 = [
            {"requirement": "Test for wireless APs", "covered": True, "evidence": "quoted text"},
            {"requirement": "Detect unauthorized APs", "covered": False, "evidence": ""},
            {"requirement": "Testing quarterly", "covered": True, "evidence": "every three months"},
        ]

        # Chunk 2 covers sub-req B only
        r2 = MappingRationale(
            is_compliant=True,
            compliance_level=ComplianceLevel.PARTIALLY_COMPLIANT,
            confidence_score=0.85,
            explanation="Covers WIDS for unauthorized detection.",
        )
        sub2 = [
            {"requirement": "Test for wireless APs", "covered": False, "evidence": ""},
            {"requirement": "Detect unauthorized APs", "covered": True, "evidence": "WIDS deployed"},
            {"requirement": "Testing quarterly", "covered": False, "evidence": ""},
        ]

        result = aggregate_rationales(
            rationales=[r1, r2],
            sub_requirements=[sub1, sub2],
        )

        assert result is not None
        assert result.compliance_level == ComplianceLevel.FULLY_COMPLIANT
        assert result.is_compliant is True

    def test_single_rationale_passes_through(self) -> None:
        """Single rationale with no aggregation needed returns as-is."""
        from ctrlmap.llm.structured_output import aggregate_rationales

        r1 = MappingRationale(
            is_compliant=True,
            compliance_level=ComplianceLevel.PARTIALLY_COMPLIANT,
            confidence_score=0.8,
            explanation="Partial coverage.",
        )
        sub1 = [
            {"requirement": "A", "covered": True, "evidence": "text"},
            {"requirement": "B", "covered": False, "evidence": ""},
        ]

        result = aggregate_rationales(rationales=[r1], sub_requirements=[sub1])
        assert result is not None
        assert result.compliance_level == ComplianceLevel.PARTIALLY_COMPLIANT

    def test_no_sub_requirements_falls_back_to_select_best(self) -> None:
        """When no sub_requirements data, falls back to select_best_rationale."""
        from ctrlmap.llm.structured_output import aggregate_rationales

        r1 = MappingRationale(
            is_compliant=True,
            compliance_level=ComplianceLevel.FULLY_COMPLIANT,
            confidence_score=0.9,
            explanation="Full coverage.",
        )

        result = aggregate_rationales(rationales=[r1], sub_requirements=[])
        assert result is not None
        assert result.compliance_level == ComplianceLevel.FULLY_COMPLIANT

    def test_empty_rationales_returns_none(self) -> None:
        """Empty input returns None."""
        from ctrlmap.llm.structured_output import aggregate_rationales

        result = aggregate_rationales(rationales=[], sub_requirements=[])
        assert result is None

    def test_all_non_compliant_stays_non_compliant(self) -> None:
        """If no sub-reqs covered across all chunks, stays non_compliant."""
        from ctrlmap.llm.structured_output import aggregate_rationales

        r1 = MappingRationale(
            is_compliant=False,
            compliance_level=ComplianceLevel.NON_COMPLIANT,
            confidence_score=0.5,
            explanation="No coverage.",
        )
        sub1 = [
            {"requirement": "A", "covered": False, "evidence": ""},
            {"requirement": "B", "covered": False, "evidence": ""},
        ]

        result = aggregate_rationales(rationales=[r1], sub_requirements=[sub1])
        assert result is not None
        assert result.compliance_level == ComplianceLevel.NON_COMPLIANT
