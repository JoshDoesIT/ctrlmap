"""Tests for meta-requirement detection and sibling aggregation.

TDD RED phase: meta-requirements like PCI DSS X.1.1 / X.1.2 should be
detected via LLM classification and resolved by aggregating compliance
status from sibling controls in the same requirement family.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ctrlmap.models.schemas import (
    MappedResult,
    MappingRationale,
    ParsedChunk,
    SecurityControl,
)

# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def pci_meta_policy_doc_control() -> SecurityControl:
    """PCI DSS X.1.1: 'All security policies...documented, in use...'"""
    return SecurityControl(
        control_id="1.1.1",
        framework="PCI-DSS",
        title="PCI DSS 1.1.1",
        description=(
            "All security policies and operational procedures that are "
            "identified in Requirement 1 are: \n"
            "• Documented.\n• Kept up to date.\n• In use.\n"
            "• Known to all affected parties."
        ),
    )


@pytest.fixture()
def pci_meta_roles_control() -> SecurityControl:
    """PCI DSS X.1.2: 'Roles and responsibilities...documented, assigned...'"""
    return SecurityControl(
        control_id="1.1.2",
        framework="PCI-DSS",
        title="PCI DSS 1.1.2",
        description=(
            "Roles and responsibilities for performing activities "
            "in Requirement 1 are documented, assigned, and understood."
        ),
    )


@pytest.fixture()
def pci_substantive_control() -> SecurityControl:
    """A normal substantive PCI DSS control."""
    return SecurityControl(
        control_id="1.2.1",
        framework="PCI-DSS",
        title="PCI DSS 1.2.1",
        description=(
            "Configuration standards for NSC rulesets are:\n"
            "• Defined.\n• Implemented.\n• Maintained."
        ),
    )


@pytest.fixture()
def compliant_sibling_results() -> list[MappedResult]:
    """A set of mapping results where all Requirement 1 siblings are compliant."""
    chunk = ParsedChunk(
        chunk_id="chunk-001",
        document_name="network_policy.pdf",
        page_number=2,
        raw_text=(
            "Configuration files for NSCs must be secured"
            " from unauthorized access and kept consistent."
        ),
        section_header="Firewall Config",
    )
    controls = [
        (
            "1.1.1",
            "PCI DSS 1.1.1",
            (
                "All security policies and operational"
                " procedures that are identified in"
                " Requirement 1 are: \n• Documented."
                "\n• Kept up to date.\n• In use."
                "\n• Known to all affected parties."
            ),
        ),
        (
            "1.1.2",
            "PCI DSS 1.1.2",
            (
                "Roles and responsibilities for performing"
                " activities in Requirement 1 are"
                " documented, assigned, and understood."
            ),
        ),
        (
            "1.2.1",
            "PCI DSS 1.2.1",
            (
                "Configuration standards for NSC rulesets"
                " are:\n• Defined.\n• Implemented."
                "\n• Maintained."
            ),
        ),
        (
            "1.2.2",
            "PCI DSS 1.2.2",
            "All changes to network connections approved via change control.",
        ),
        (
            "1.2.3",
            "PCI DSS 1.2.3",
            "Accurate network diagram maintained.",
        ),
    ]
    results = []
    for cid, title, desc in controls:
        is_meta = cid in ("1.1.1", "1.1.2")
        results.append(
            MappedResult(
                control=SecurityControl(
                    control_id=cid,
                    framework="PCI-DSS",
                    title=title,
                    description=desc,
                ),
                supporting_chunks=[] if is_meta else [chunk],
                rationale=(
                    None
                    if is_meta
                    else MappingRationale(
                        is_compliant=True,
                        confidence_score=0.90,
                        explanation=f"Policy addresses {cid}.",
                    )
                ),
            )
        )
    return results


@pytest.fixture()
def mixed_sibling_results() -> list[MappedResult]:
    """Results where some Requirement 1 siblings are non-compliant."""
    chunk = ParsedChunk(
        chunk_id="chunk-001",
        document_name="network_policy.pdf",
        page_number=2,
        raw_text=(
            "Configuration files for NSCs must be secured"
            " from unauthorized access and kept consistent."
        ),
        section_header="Firewall Config",
    )
    return [
        MappedResult(
            control=SecurityControl(
                control_id="1.1.1",
                framework="PCI-DSS",
                title="PCI DSS 1.1.1",
                description="All security policies...documented...",
            ),
            supporting_chunks=[],
            rationale=None,
        ),
        MappedResult(
            control=SecurityControl(
                control_id="1.2.1",
                framework="PCI-DSS",
                title="PCI DSS 1.2.1",
                description="Config standards defined.",
            ),
            supporting_chunks=[chunk],
            rationale=MappingRationale(
                is_compliant=True,
                confidence_score=0.90,
                explanation="Policy addresses config.",
            ),
        ),
        MappedResult(
            control=SecurityControl(
                control_id="1.2.2",
                framework="PCI-DSS",
                title="PCI DSS 1.2.2",
                description="Change control process.",
            ),
            supporting_chunks=[],
            rationale=MappingRationale(
                is_compliant=False,
                confidence_score=0.30,
                explanation="No change control process documented.",
            ),
        ),
    ]


# ---------------------------------------------------------------------------
#  Tests: LLM-based classification
# ---------------------------------------------------------------------------


class TestClassifyMetaRequirement:
    """classify_meta_requirement uses LLM to detect governance requirements."""

    def test_classifies_policy_documentation_requirement_as_meta(
        self,
        pci_meta_policy_doc_control: SecurityControl,
    ) -> None:
        """LLM should classify 'All security policies...documented' as meta."""
        from ctrlmap.map.meta_requirements import classify_meta_requirement

        # Mock the LLM to return True (it IS a meta-requirement)
        with patch("ctrlmap.map.meta_requirements.OllamaClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.classify_control_type.return_value = True

            result = classify_meta_requirement(
                control=pci_meta_policy_doc_control,
                client=mock_instance,
            )
            assert result is True
            mock_instance.classify_control_type.assert_called_once()

    def test_classifies_roles_responsibilities_as_meta(
        self,
        pci_meta_roles_control: SecurityControl,
    ) -> None:
        """LLM should classify 'roles and responsibilities' as meta."""
        from ctrlmap.map.meta_requirements import classify_meta_requirement

        with patch("ctrlmap.map.meta_requirements.OllamaClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.classify_control_type.return_value = True

            result = classify_meta_requirement(
                control=pci_meta_roles_control,
                client=mock_instance,
            )
            assert result is True

    def test_classifies_substantive_control_as_not_meta(
        self,
        pci_substantive_control: SecurityControl,
    ) -> None:
        """LLM should classify normal technical controls as NOT meta."""
        from ctrlmap.map.meta_requirements import classify_meta_requirement

        with patch("ctrlmap.map.meta_requirements.OllamaClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.classify_control_type.return_value = False

            result = classify_meta_requirement(
                control=pci_substantive_control,
                client=mock_instance,
            )
            assert result is False


# ---------------------------------------------------------------------------
#  Tests: Sibling aggregation
# ---------------------------------------------------------------------------


class TestResolveMetaRequirements:
    """resolve_meta_requirements aggregates sibling compliance."""

    def test_resolve_marks_meta_compliant_when_all_siblings_pass(
        self,
        compliant_sibling_results: list[MappedResult],
    ) -> None:
        """Meta-requirements become compliant when all siblings are compliant."""
        from ctrlmap.map.meta_requirements import resolve_meta_requirements

        meta_ids = {"1.1.1", "1.1.2"}
        resolved = resolve_meta_requirements(
            results=compliant_sibling_results,
            meta_control_ids=meta_ids,
        )

        # 1.1.1 should now be compliant via aggregation
        meta_111 = next(r for r in resolved if r.control.control_id == "1.1.1")
        assert isinstance(meta_111.rationale, MappingRationale)
        assert meta_111.rationale.is_compliant is True
        explanation = meta_111.rationale.explanation.lower()
        assert "sibling" in explanation or "aggregat" in explanation

        # 1.1.2 should similarly be compliant
        meta_112 = next(r for r in resolved if r.control.control_id == "1.1.2")
        assert isinstance(meta_112.rationale, MappingRationale)
        assert meta_112.rationale.is_compliant is True

    def test_resolve_marks_meta_noncompliant_when_siblings_have_gaps(
        self,
        mixed_sibling_results: list[MappedResult],
    ) -> None:
        """Meta-requirements are non-compliant when some siblings fail."""
        from ctrlmap.map.meta_requirements import resolve_meta_requirements

        meta_ids = {"1.1.1"}
        resolved = resolve_meta_requirements(
            results=mixed_sibling_results,
            meta_control_ids=meta_ids,
        )

        meta_111 = next(r for r in resolved if r.control.control_id == "1.1.1")
        assert isinstance(meta_111.rationale, MappingRationale)
        assert meta_111.rationale.is_compliant is False
        # Should mention the non-compliant sibling
        assert "1.2.2" in meta_111.rationale.explanation

    def test_resolve_leaves_non_meta_controls_untouched(
        self,
        compliant_sibling_results: list[MappedResult],
    ) -> None:
        """Substantive controls should not be modified."""
        from ctrlmap.map.meta_requirements import resolve_meta_requirements

        meta_ids = {"1.1.1", "1.1.2"}
        resolved = resolve_meta_requirements(
            results=compliant_sibling_results,
            meta_control_ids=meta_ids,
        )

        # Substantive controls should retain their original rationale
        ctrl_121 = next(r for r in resolved if r.control.control_id == "1.2.1")
        assert isinstance(ctrl_121.rationale, MappingRationale)
        assert ctrl_121.rationale.confidence_score == 0.90
        assert ctrl_121.rationale.explanation == "Policy addresses 1.2.1."

    def test_resolve_handles_empty_results(self) -> None:
        """Empty input returns empty output."""
        from ctrlmap.map.meta_requirements import resolve_meta_requirements

        resolved = resolve_meta_requirements(results=[], meta_control_ids=set())
        assert resolved == []

    def test_sibling_counts_are_consistent_across_family(
        self,
        compliant_sibling_results: list[MappedResult],
    ) -> None:
        """All meta-requirements in the same family should report the same sibling count."""
        from ctrlmap.map.meta_requirements import resolve_meta_requirements

        import re

        meta_ids = {"1.1.1", "1.1.2"}
        resolved = resolve_meta_requirements(
            results=compliant_sibling_results,
            meta_control_ids=meta_ids,
        )

        meta_111 = next(r for r in resolved if r.control.control_id == "1.1.1")
        meta_112 = next(r for r in resolved if r.control.control_id == "1.1.2")

        assert isinstance(meta_111.rationale, MappingRationale)
        assert isinstance(meta_112.rationale, MappingRationale)

        # Both should reference the same number of siblings (3 substantive in family 1)
        count_111 = re.search(r"all (\d+) evaluated", meta_111.rationale.explanation)
        count_112 = re.search(r"all (\d+) evaluated", meta_112.rationale.explanation)

        assert count_111 is not None, f"Missing count in: {meta_111.rationale.explanation}"
        assert count_112 is not None, f"Missing count in: {meta_112.rationale.explanation}"
        assert count_111.group(1) == count_112.group(1), (
            f"Sibling counts differ: 1.1.1 says {count_111.group(1)}, "
            f"1.1.2 says {count_112.group(1)}"
        )


class TestGovernanceControlOverride:
    """Governance controls (x.1.x) should always check sibling compliance."""

    def test_governance_control_overridden_when_siblings_non_compliant(self) -> None:
        """A governance control without direct evidence should be overridden
        to non-compliant when sibling controls are non-compliant.

        Reproduces the case where a governance control has no matching
        policy text but siblings in the same requirement family have gaps.
        """
        from ctrlmap.map.meta_requirements import resolve_meta_requirements
        from ctrlmap.models.schemas import ComplianceLevel

        # 6.1.2 — governance control, no direct evidence
        ctrl_612 = SecurityControl(
            control_id="6.1.2",
            framework="PCI-DSS",
            title="PCI DSS 6.1.2",
            description="Roles and responsibilities for Requirement 6.",
        )
        result_612 = MappedResult(
            control=ctrl_612,
            supporting_chunks=[],
            rationale=None,
        )

        # 6.2.1 — non-compliant sibling
        result_621 = MappedResult(
            control=SecurityControl(
                control_id="6.2.1",
                framework="PCI-DSS",
                title="PCI DSS 6.2.1",
                description="Secure development practices.",
            ),
            supporting_chunks=[],
            rationale=MappingRationale(
                is_compliant=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                confidence_score=0.80,
                explanation="No secure dev policy.",
            ),
        )

        # 6.2.2 — non-compliant sibling
        result_622 = MappedResult(
            control=SecurityControl(
                control_id="6.2.2",
                framework="PCI-DSS",
                title="PCI DSS 6.2.2",
                description="Training for dev personnel.",
            ),
            supporting_chunks=[],
            rationale=MappingRationale(
                is_compliant=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                confidence_score=0.80,
                explanation="No training policy.",
            ),
        )

        results = [result_612, result_621, result_622]

        # 6.1.2 is classified by the LLM as a meta-requirement (governance),
        # so it appears in meta_control_ids and should be overridden.
        resolved = resolve_meta_requirements(
            results=results,
            meta_control_ids={"6.1.2"},
        )

        r612 = next(r for r in resolved if r.control.control_id == "6.1.2")
        assert isinstance(r612.rationale, MappingRationale)
        assert r612.rationale.compliance_level == ComplianceLevel.NON_COMPLIANT, (
            f"Expected 6.1.2 to be NON_COMPLIANT due to siblings, "
            f"got {r612.rationale.compliance_level}"
        )

    def test_meta_with_direct_evidence_preserved_when_correct(self) -> None:
        """A meta-control with direct chunk evidence and a compliant LLM
        rationale should NOT be overridden to non-compliant just because
        an unrelated sibling in the same requirement family has a gap.

        Reproduces the 12.1.4 bug: 'CISO formally assigned' has direct
        evidence from the policy header, but gets overridden because
        12.2.1 (end-user acceptable use) is a gap.
        """
        from ctrlmap.map.meta_requirements import resolve_meta_requirements
        from ctrlmap.models.schemas import ComplianceLevel

        # 12.1.4 — meta with direct evidence (CISO assignment, compliant)
        result_1214 = MappedResult(
            control=SecurityControl(
                control_id="12.1.4",
                framework="PCI-DSS",
                title="CISO responsibility formally assigned",
                description="Responsibility for information security is formally assigned to a CISO.",
            ),
            supporting_chunks=[
                ParsedChunk(
                    chunk_id="c-ciso",
                    document_name="policy.pdf",
                    page_number=1,
                    raw_text="This policy has been approved by the Chief Information Security Officer Acme Corp Network Security Policy.",
                ),
            ],
            rationale=MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.FULLY_COMPLIANT,
                confidence_score=0.95,
                explanation="CISO role is explicitly referenced in the policy header.",
            ),
        )

        # 12.2.1 — non-compliant gap (acceptable use policy)
        result_1221 = MappedResult(
            control=SecurityControl(
                control_id="12.2.1",
                framework="PCI-DSS",
                title="Acceptable use policies",
                description="Acceptable use policies for end-user technologies are documented.",
            ),
            supporting_chunks=[],
            rationale=MappingRationale(
                is_compliant=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                confidence_score=0.90,
                explanation="No acceptable use policy exists.",
            ),
        )

        results = [result_1214, result_1221]
        resolved = resolve_meta_requirements(
            results=results,
            meta_control_ids={"12.1.4"},
        )

        r1214 = next(r for r in resolved if r.control.control_id == "12.1.4")
        assert isinstance(r1214.rationale, MappingRationale)
        # Should KEEP its compliant verdict — has direct evidence
        assert r1214.rationale.compliance_level == ComplianceLevel.FULLY_COMPLIANT, (
            f"Expected 12.1.4 to KEEP FULLY_COMPLIANT (has direct evidence), "
            f"got {r1214.rationale.compliance_level}"
        )

    def test_meta_overridden_noncompliant_when_siblings_have_gaps(self) -> None:
        """A meta-control should be overridden to non-compliant when
        sibling controls have gaps, regardless of any existing rationale.

        Reproduces the case where a meta-control (8.2.4) has a gap
        rationale from Step 4, and siblings also have gaps. The
        sibling-level non-compliance should override.
        """
        from ctrlmap.map.meta_requirements import resolve_meta_requirements
        from ctrlmap.models.schemas import ComplianceLevel

        # 8.2.4 — meta with gap rationale (from Step 4), no chunks
        result_824 = MappedResult(
            control=SecurityControl(
                control_id="8.2.4",
                framework="PCI-DSS",
                title="User ID lifecycle management",
                description="Addition, deletion, and modification of user IDs are managed.",
            ),
            supporting_chunks=[],
            rationale=MappingRationale(
                is_compliant=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                confidence_score=0.80,
                explanation="No policy covers user ID lifecycle management.",
            ),
        )

        # 8.2.1 — compliant sibling
        result_821 = MappedResult(
            control=SecurityControl(
                control_id="8.2.1",
                framework="PCI-DSS",
                title="Unique user IDs",
                description="All users are assigned a unique ID.",
            ),
            supporting_chunks=[
                ParsedChunk(
                    chunk_id="c-uid",
                    document_name="access.pdf",
                    page_number=2,
                    raw_text="All users must be assigned a unique user ID before they are allowed access to any system component.",
                ),
            ],
            rationale=MappingRationale(
                is_compliant=True,
                compliance_level=ComplianceLevel.FULLY_COMPLIANT,
                confidence_score=1.00,
                explanation="Unique ID assignment policy exists.",
            ),
        )

        # 8.2.5 — non-compliant sibling (gap)
        result_825 = MappedResult(
            control=SecurityControl(
                control_id="8.2.5",
                framework="PCI-DSS",
                title="Access revocation",
                description="Access for terminated users is immediately revoked.",
            ),
            supporting_chunks=[],
            rationale=MappingRationale(
                is_compliant=False,
                compliance_level=ComplianceLevel.NON_COMPLIANT,
                confidence_score=0.80,
                explanation="No termination revocation policy.",
            ),
        )

        results = [result_824, result_821, result_825]
        resolved = resolve_meta_requirements(
            results=results,
            meta_control_ids={"8.2.4"},
        )

        r824 = next(r for r in resolved if r.control.control_id == "8.2.4")
        # Should be non-compliant — sibling 8.2.5 has a gap
        assert isinstance(r824.rationale, MappingRationale)
        assert not r824.rationale.is_compliant, (
            f"Expected 8.2.4 to be non-compliant (sibling gap), "
            f"but got {r824.rationale}"
        )


class TestPerChunkSelection:
    """Per-chunk rationale selection should pick the best rationale."""

    def test_select_best_rationale_picks_compliant_over_non_compliant(self) -> None:
        """When one chunk produces compliant and another non-compliant,
        the compliant rationale should be selected."""
        from ctrlmap.llm.structured_output import select_best_rationale
        from ctrlmap.models.schemas import ComplianceLevel

        compliant = MappingRationale(
            is_compliant=True,
            compliance_level=ComplianceLevel.FULLY_COMPLIANT,
            confidence_score=0.90,
            explanation="Chunk directly addresses the control.",
        )
        non_compliant = MappingRationale(
            is_compliant=False,
            compliance_level=ComplianceLevel.NON_COMPLIANT,
            confidence_score=0.80,
            explanation="Chunk does not address the control.",
        )

        best = select_best_rationale([non_compliant, compliant])
        assert best.compliance_level == ComplianceLevel.FULLY_COMPLIANT

    def test_select_best_rationale_picks_higher_confidence(self) -> None:
        """When multiple chunks produce the same compliance level,
        the one with higher confidence should win."""
        from ctrlmap.llm.structured_output import select_best_rationale
        from ctrlmap.models.schemas import ComplianceLevel

        low = MappingRationale(
            is_compliant=True,
            compliance_level=ComplianceLevel.FULLY_COMPLIANT,
            confidence_score=0.70,
            explanation="Weak evidence.",
        )
        high = MappingRationale(
            is_compliant=True,
            compliance_level=ComplianceLevel.FULLY_COMPLIANT,
            confidence_score=0.95,
            explanation="Strong evidence.",
        )

        best = select_best_rationale([low, high])
        assert best.confidence_score == 0.95

    def test_select_best_rationale_empty_list_returns_none(self) -> None:
        """An empty list should return None."""
        from ctrlmap.llm.structured_output import select_best_rationale

        assert select_best_rationale([]) is None


