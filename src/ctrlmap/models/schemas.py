"""ctrlmap core data models.

Pydantic v2 schemas for the SDD pipeline. All models use:
- ``model_config = ConfigDict(extra='forbid', strict=True)``
  to prevent silent data corruption from unexpected fields or type coercion.

Models
------
ParsedChunk
    Semantic text payload with document/page metadata.
SecurityControl
    Standardized control definition (e.g., NIST AC-2).
CommonControl
    Unified deduplicated control with source references.
ComplianceLevel
    Three-tier compliance classification.
MappingRationale
    LLM-generated compliance justification.
InsufficientEvidence
    Explicit uncertainty marker when context is insufficient.
MappedResult
    Control + supporting chunks + union-type rationale.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ParsedChunk(BaseModel):
    """A semantically cohesive text segment extracted from a policy document."""

    model_config = ConfigDict(extra="forbid", strict=True)

    chunk_id: str
    document_name: str
    page_number: int = Field(ge=1)
    raw_text: str = Field(min_length=50)
    section_header: str | None = None
    embedding: list[float] | None = None


class SecurityControl(BaseModel):
    """A standardized security control from a compliance framework."""

    model_config = ConfigDict(extra="forbid", strict=True)

    control_id: str
    framework: str
    title: str
    description: str
    requirement_family: str = ""

    def as_prompt_text(self) -> str:
        """Format the control as a single prompt string for LLM consumption.

        Returns:
            A string like ``"AC-2: Account Management. <description>"``.
        """
        return f"{self.control_id}: {self.title}. {self.description}"


class CommonControl(BaseModel):
    """A deduplicated control synthesized from multiple overlapping requirements."""

    model_config = ConfigDict(extra="forbid", strict=True)

    common_id: str
    theme: str
    unified_description: str
    source_references: list[str]


class ComplianceLevel(StrEnum):
    """Three-tier compliance classification for control mappings."""

    FULLY_COMPLIANT = "fully_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"


class MappingRationale(BaseModel):
    """LLM-generated rationale when sufficient evidence supports a mapping."""

    model_config = ConfigDict(extra="forbid", strict=True)

    is_compliant: bool
    compliance_level: ComplianceLevel = ComplianceLevel.NON_COMPLIANT
    confidence_score: float = Field(ge=0.0, le=1.0)
    explanation: str

    @model_validator(mode="after")
    def _default_compliance_level(self) -> MappingRationale:
        """Derive compliance_level from is_compliant when not explicitly set.

        If the caller only provides ``is_compliant`` (backward-compat path),
        this validator sets compliance_level to the appropriate binary value.
        When compliance_level is explicitly provided, it takes precedence.
        """
        # Detect whether compliance_level was explicitly provided.
        # If the field still has its schema default AND it contradicts
        # is_compliant, override it with the inferred value.
        if self.is_compliant and self.compliance_level == ComplianceLevel.NON_COMPLIANT:
            self.compliance_level = ComplianceLevel.FULLY_COMPLIANT
        elif not self.is_compliant and self.compliance_level == ComplianceLevel.FULLY_COMPLIANT:
            self.compliance_level = ComplianceLevel.NON_COMPLIANT
        return self


class InsufficientEvidence(BaseModel):
    """Explicit marker when LLM cannot produce a grounded rationale."""

    model_config = ConfigDict(extra="forbid", strict=True)

    reason: str
    required_context: str


class MappedResult(BaseModel):
    """A single control mapping with supporting evidence and rationale."""

    model_config = ConfigDict(extra="forbid", strict=True)

    control: SecurityControl
    supporting_chunks: list[ParsedChunk]
    rationale: MappingRationale | InsufficientEvidence | None = None
