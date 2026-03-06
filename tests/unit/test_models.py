"""Tests for ctrlmap Pydantic v2 data models.

TDD RED phase: These tests define the expected behavior of all core models
from the SDD blueprint before implementation.
"""

import pytest
from pydantic import ValidationError


class TestParsedChunk:
    """Tests for the ParsedChunk model."""

    def test_valid_parsed_chunk(self) -> None:
        """A ParsedChunk with all required fields should validate successfully."""
        from ctrlmap.models.schemas import ParsedChunk

        chunk = ParsedChunk(
            chunk_id="abc123",
            document_name="policy.pdf",
            page_number=1,
            raw_text="This is a valid chunk of text for testing purposes.",
        )
        assert chunk.chunk_id == "abc123"
        assert chunk.document_name == "policy.pdf"
        assert chunk.page_number == 1

    def test_parsed_chunk_rejects_extra_fields(self) -> None:
        """ParsedChunk with extra='forbid' must raise ValidationError on unknown fields."""
        from ctrlmap.models.schemas import ParsedChunk

        with pytest.raises(ValidationError, match="extra_forbidden"):
            ParsedChunk(
                chunk_id="abc123",
                document_name="policy.pdf",
                page_number=1,
                raw_text="This is a valid chunk of text for testing purposes.",
                unknown_field="should fail",
            )

    def test_parsed_chunk_rejects_short_raw_text(self) -> None:
        """raw_text with fewer than 50 characters must be rejected."""
        from ctrlmap.models.schemas import ParsedChunk

        with pytest.raises(ValidationError, match="String should have at least 50 characters"):
            ParsedChunk(
                chunk_id="abc123",
                document_name="policy.pdf",
                page_number=1,
                raw_text="short",
            )

    def test_parsed_chunk_rejects_zero_page_number(self) -> None:
        """page_number=0 must be rejected (ge=1)."""
        from ctrlmap.models.schemas import ParsedChunk

        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            ParsedChunk(
                chunk_id="abc123",
                document_name="policy.pdf",
                page_number=0,
                raw_text="This is a valid chunk of text for testing purposes.",
            )

    def test_parsed_chunk_optional_fields_default_none(self) -> None:
        """Optional fields (section_header, embedding) should default to None."""
        from ctrlmap.models.schemas import ParsedChunk

        chunk = ParsedChunk(
            chunk_id="abc123",
            document_name="policy.pdf",
            page_number=1,
            raw_text="This is a valid chunk of text for testing purposes.",
        )
        assert chunk.section_header is None
        assert chunk.embedding is None

    def test_strict_mode_prevents_type_coercion(self) -> None:
        """Passing a string where int is expected must raise ValidationError in strict mode."""
        from ctrlmap.models.schemas import ParsedChunk

        with pytest.raises(ValidationError):
            ParsedChunk(
                chunk_id="abc123",
                document_name="policy.pdf",
                page_number="not_a_number",  # type: ignore[arg-type]
                raw_text="This is a valid chunk of text for testing purposes.",
            )


class TestSecurityControl:
    """Tests for the SecurityControl model."""

    def test_valid_security_control(self) -> None:
        """A SecurityControl with all required fields should validate."""
        from ctrlmap.models.schemas import SecurityControl

        control = SecurityControl(
            control_id="AC-2",
            framework="NIST-800-53-r5",
            title="Account Management",
            description="Manage system accounts, group memberships, and authorizations.",
        )
        assert control.control_id == "AC-2"
        assert control.framework == "NIST-800-53-r5"

    def test_security_control_requires_all_fields(self) -> None:
        """Missing required fields must raise ValidationError."""
        from ctrlmap.models.schemas import SecurityControl

        with pytest.raises(ValidationError):
            SecurityControl(
                control_id="AC-2",
                # missing framework, title, description
            )  # type: ignore[call-arg]


class TestCommonControl:
    """Tests for the CommonControl model."""

    def test_valid_common_control(self) -> None:
        """A CommonControl with all required fields should validate."""
        from ctrlmap.models.schemas import CommonControl

        cc = CommonControl(
            common_id="CC-1",
            theme="Access Control",
            unified_description="Comprehensive access control requirements from all sources.",
            source_references=["chunk_1", "ctrl_ac2", "ctrl_ia5"],
        )
        assert cc.common_id == "CC-1"
        assert len(cc.source_references) == 3

    def test_common_control_requires_source_references(self) -> None:
        """source_references is required and cannot be omitted."""
        from ctrlmap.models.schemas import CommonControl

        with pytest.raises(ValidationError):
            CommonControl(
                common_id="CC-1",
                theme="Access Control",
                unified_description="Description text.",
                # missing source_references
            )  # type: ignore[call-arg]


class TestMappingRationale:
    """Tests for the MappingRationale model."""

    def test_valid_mapping_rationale(self) -> None:
        """A MappingRationale with valid fields should validate."""
        from ctrlmap.models.schemas import MappingRationale

        rationale = MappingRationale(
            is_compliant=True,
            confidence_score=0.95,
            explanation="Policy chunk fully satisfies the access control requirements.",
        )
        assert rationale.is_compliant is True
        assert rationale.confidence_score == 0.95

    def test_mapping_rationale_confidence_below_zero(self) -> None:
        """confidence_score below 0.0 must be rejected."""
        from ctrlmap.models.schemas import MappingRationale

        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            MappingRationale(
                is_compliant=True,
                confidence_score=-0.1,
                explanation="Some explanation.",
            )

    def test_mapping_rationale_confidence_above_one(self) -> None:
        """confidence_score above 1.0 must be rejected."""
        from ctrlmap.models.schemas import MappingRationale

        with pytest.raises(ValidationError, match="less than or equal to 1"):
            MappingRationale(
                is_compliant=True,
                confidence_score=1.5,
                explanation="Some explanation.",
            )

    def test_compliance_level_fully_compliant(self) -> None:
        """MappingRationale accepts compliance_level='fully_compliant'."""
        from ctrlmap.models.schemas import ComplianceLevel, MappingRationale

        rationale = MappingRationale(
            is_compliant=True,
            compliance_level=ComplianceLevel.FULLY_COMPLIANT,
            confidence_score=0.95,
            explanation="All requirements addressed.",
        )
        assert rationale.compliance_level == ComplianceLevel.FULLY_COMPLIANT

    def test_compliance_level_partially_compliant(self) -> None:
        """MappingRationale accepts compliance_level='partially_compliant'."""
        from ctrlmap.models.schemas import ComplianceLevel, MappingRationale

        rationale = MappingRationale(
            is_compliant=True,
            compliance_level=ComplianceLevel.PARTIALLY_COMPLIANT,
            confidence_score=0.65,
            explanation="Core requirement addressed but details missing.",
        )
        assert rationale.compliance_level == ComplianceLevel.PARTIALLY_COMPLIANT

    def test_compliance_level_non_compliant(self) -> None:
        """MappingRationale accepts compliance_level='non_compliant'."""
        from ctrlmap.models.schemas import ComplianceLevel, MappingRationale

        rationale = MappingRationale(
            is_compliant=False,
            compliance_level=ComplianceLevel.NON_COMPLIANT,
            confidence_score=0.90,
            explanation="No policy coverage.",
        )
        assert rationale.compliance_level == ComplianceLevel.NON_COMPLIANT

    def test_compliance_level_defaults_from_is_compliant(self) -> None:
        """When compliance_level is omitted, it should default based on is_compliant."""
        from ctrlmap.models.schemas import ComplianceLevel, MappingRationale

        compliant = MappingRationale(
            is_compliant=True,
            confidence_score=0.90,
            explanation="Policy covers the requirement.",
        )
        assert compliant.compliance_level == ComplianceLevel.FULLY_COMPLIANT

        non_compliant = MappingRationale(
            is_compliant=False,
            confidence_score=0.85,
            explanation="No coverage found.",
        )
        assert non_compliant.compliance_level == ComplianceLevel.NON_COMPLIANT

    def test_compliance_level_enum_has_three_values(self) -> None:
        """ComplianceLevel enum should have exactly 3 values."""
        from ctrlmap.models.schemas import ComplianceLevel

        values = list(ComplianceLevel)
        assert len(values) == 3
        assert ComplianceLevel.FULLY_COMPLIANT in values
        assert ComplianceLevel.PARTIALLY_COMPLIANT in values
        assert ComplianceLevel.NON_COMPLIANT in values


class TestInsufficientEvidence:
    """Tests for the InsufficientEvidence model."""

    def test_valid_insufficient_evidence(self) -> None:
        """An InsufficientEvidence with valid fields should validate."""
        from ctrlmap.models.schemas import InsufficientEvidence

        ie = InsufficientEvidence(
            reason="No policy chunks reference encryption at rest.",
            required_context="Policy language addressing data encryption requirements.",
        )
        assert "encryption" in ie.reason

    def test_insufficient_evidence_requires_both_fields(self) -> None:
        """Both reason and required_context are required."""
        from ctrlmap.models.schemas import InsufficientEvidence

        with pytest.raises(ValidationError):
            InsufficientEvidence(
                reason="Missing context.",
                # missing required_context
            )  # type: ignore[call-arg]


class TestMappedResult:
    """Tests for the MappedResult model with union-type rationale."""

    def test_mapped_result_accepts_mapping_rationale(self) -> None:
        """MappedResult should accept MappingRationale as rationale."""
        from ctrlmap.models.schemas import (
            MappedResult,
            MappingRationale,
            ParsedChunk,
            SecurityControl,
        )

        result = MappedResult(
            control=SecurityControl(
                control_id="AC-2",
                framework="NIST-800-53-r5",
                title="Account Management",
                description="Manage system accounts.",
            ),
            supporting_chunks=[
                ParsedChunk(
                    chunk_id="chunk_1",
                    document_name="policy.pdf",
                    page_number=5,
                    raw_text="All user accounts must be reviewed quarterly by management.",
                )
            ],
            rationale=MappingRationale(
                is_compliant=True,
                confidence_score=0.92,
                explanation="Policy requires quarterly account reviews.",
            ),
        )
        assert isinstance(result.rationale, MappingRationale)

    def test_mapped_result_accepts_insufficient_evidence(self) -> None:
        """MappedResult should accept InsufficientEvidence as rationale."""
        from ctrlmap.models.schemas import (
            InsufficientEvidence,
            MappedResult,
            ParsedChunk,
            SecurityControl,
        )

        result = MappedResult(
            control=SecurityControl(
                control_id="SC-28",
                framework="NIST-800-53-r5",
                title="Protection of Information at Rest",
                description="Protect the confidentiality of information at rest.",
            ),
            supporting_chunks=[
                ParsedChunk(
                    chunk_id="chunk_2",
                    document_name="policy.pdf",
                    page_number=10,
                    raw_text=(
                        "The company follows standard operational procedures for data handling."
                    ),
                )
            ],
            rationale=InsufficientEvidence(
                reason="Policy chunk does not address encryption at rest.",
                required_context="Policy language about data encryption requirements.",
            ),
        )
        assert isinstance(result.rationale, InsufficientEvidence)
