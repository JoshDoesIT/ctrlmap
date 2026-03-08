"""Shared pytest fixtures for ctrlmap test suite.

Provides reusable model instances (SecurityControl, ParsedChunk,
MappedResult, MappingRationale) to reduce boilerplate across
test modules.
"""

from __future__ import annotations

import pytest

from ctrlmap.models.schemas import (
    ComplianceLevel,
    MappedResult,
    MappingRationale,
    ParsedChunk,
    SecurityControl,
)


@pytest.fixture()
def sample_control() -> SecurityControl:
    """A minimal PCI DSS security control."""
    return SecurityControl(
        control_id="8.2.2",
        framework="PCI DSS v4.0",
        title="Unique User Identification",
        description="Assign a unique ID to each person with computer access.",
        requirement_family="Identify Users and Authenticate Access",
    )


@pytest.fixture()
def sample_chunk() -> ParsedChunk:
    """A minimal parsed chunk from an access control policy."""
    return ParsedChunk(
        chunk_id="chunk-001",
        document_name="access_control_policy.pdf",
        page_number=3,
        raw_text=(
            "All employees must be assigned a unique user identifier. "
            "Generic, shared, or group IDs are strictly prohibited."
        ),
        section_header="8  User Identification",
    )


@pytest.fixture()
def sample_rationale() -> MappingRationale:
    """A minimal fully-compliant rationale."""
    return MappingRationale(
        is_compliant=True,
        compliance_level=ComplianceLevel.FULLY_COMPLIANT,
        confidence_score=0.92,
        explanation="The policy explicitly requires unique user IDs.",
    )


@pytest.fixture()
def sample_mapped_result(
    sample_control: SecurityControl,
    sample_chunk: ParsedChunk,
    sample_rationale: MappingRationale,
) -> MappedResult:
    """A minimal mapped result with one supporting chunk and rationale."""
    return MappedResult(
        control=sample_control,
        supporting_chunks=[sample_chunk],
        similarity_score=0.87,
        rationale=sample_rationale,
    )
