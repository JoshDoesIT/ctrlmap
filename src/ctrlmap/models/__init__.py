"""ctrlmap.models: Pydantic schema definitions and OSCAL serialization.

Public API:
    ComplianceLevel: Three-tier compliance enum.
    CommonControl: Deduplicated control from harmonization.
    InsufficientEvidence: Returned when LLM cannot produce a rationale.
    MappedResult: A control paired with its supporting chunks and rationale.
    MappingRationale: Structured LLM compliance rationale.
    ParsedChunk: A semantically cohesive text segment from a document.
    SecurityControl: A standardized control from a compliance framework.
    parse_oscal_catalog: Parse an OSCAL JSON catalog into SecurityControl list.
"""

from ctrlmap.models.oscal import parse_oscal_catalog
from ctrlmap.models.schemas import (
    CommonControl,
    ComplianceLevel,
    InsufficientEvidence,
    MappedResult,
    MappingRationale,
    ParsedChunk,
    SecurityControl,
)

__all__ = [
    "CommonControl",
    "ComplianceLevel",
    "InsufficientEvidence",
    "MappedResult",
    "MappingRationale",
    "ParsedChunk",
    "SecurityControl",
    "parse_oscal_catalog",
]
