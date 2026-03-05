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
MappingRationale
    LLM-generated compliance justification.
InsufficientEvidence
    Explicit uncertainty marker when context is insufficient.
MappedResult
    Control + supporting chunks + union-type rationale.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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


class CommonControl(BaseModel):
    """A deduplicated control synthesized from multiple overlapping requirements."""

    model_config = ConfigDict(extra="forbid", strict=True)

    common_id: str
    theme: str
    unified_description: str
    source_references: list[str]


class MappingRationale(BaseModel):
    """LLM-generated rationale when sufficient evidence supports a mapping."""

    model_config = ConfigDict(extra="forbid", strict=True)

    is_compliant: bool
    confidence_score: float = Field(ge=0.0, le=1.0)
    explanation: str


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
