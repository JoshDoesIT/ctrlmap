"""Integration test: Control harmonization integrity (Test Spec 2 from SDD).

Verbatim from the SDD blueprint:
    Goal: Ensure identical or highly similar controls from different
    frameworks are merged.

    Given: Three framework documents containing an "Encryption at Rest"
    requirement.

    When: Processed by the harmonize pipeline.

    Then: The engine must cluster the three requirements into a single
    CommonControl object. The source_references array must contain
    exactly three IDs mapping back to the distinct origin documents.

Ref: GitHub Issue #21.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def three_enc_frameworks(tmp_path: Path) -> Path:
    """Create three OSCAL framework files with 'Encryption at Rest' controls."""
    inputs_dir = tmp_path / "frameworks"
    inputs_dir.mkdir()

    frameworks = [
        {
            "name": "nist_enc.json",
            "catalog": {
                "uuid": "nist-test",
                "metadata": {"title": "NIST Test", "version": "1.0"},
                "groups": [
                    {
                        "id": "sc",
                        "title": "System Protection",
                        "controls": [
                            {
                                "id": "sc-28",
                                "title": "Protection of Information at Rest",
                                "props": [{"name": "label", "value": "NIST-SC-28"}],
                                "parts": [
                                    {
                                        "id": "sc-28_smt",
                                        "name": "statement",
                                        "prose": (
                                            "Protect the confidentiality and integrity "
                                            "of information at rest using encryption."
                                        ),
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        },
        {
            "name": "soc2_enc.json",
            "catalog": {
                "uuid": "soc2-test",
                "metadata": {"title": "SOC2 Test", "version": "1.0"},
                "groups": [
                    {
                        "id": "cc6",
                        "title": "Logical Access",
                        "controls": [
                            {
                                "id": "cc6-1",
                                "title": "Data Encryption at Rest",
                                "props": [{"name": "label", "value": "SOC2-CC6.1"}],
                                "parts": [
                                    {
                                        "id": "cc6-1_smt",
                                        "name": "statement",
                                        "prose": (
                                            "Encrypt all sensitive data at rest using "
                                            "approved cryptographic algorithms."
                                        ),
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        },
        {
            "name": "iso_enc.json",
            "catalog": {
                "uuid": "iso-test",
                "metadata": {"title": "ISO Test", "version": "1.0"},
                "groups": [
                    {
                        "id": "a10",
                        "title": "Cryptography",
                        "controls": [
                            {
                                "id": "a-10-1-1",
                                "title": "Cryptographic Controls for Data at Rest",
                                "props": [{"name": "label", "value": "ISO-A.10.1.1"}],
                                "parts": [
                                    {
                                        "id": "a-10-1-1_smt",
                                        "name": "statement",
                                        "prose": (
                                            "Implement cryptographic controls to protect "
                                            "data confidentiality and integrity at rest."
                                        ),
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        },
    ]

    for fw in frameworks:
        fpath = inputs_dir / fw["name"]
        fpath.write_text(json.dumps({"catalog": fw["catalog"]}))

    return inputs_dir


class TestHarmonizationIntegrity:
    """Test Spec 2 from the SDD blueprint."""

    def test_three_encryption_controls_merge_into_one_common_control(
        self,
        three_enc_frameworks: Path,
    ) -> None:
        """Three 'Encryption at Rest' controls cluster into a single CommonControl."""
        from ctrlmap.map.cluster import cluster_controls
        from ctrlmap.models.oscal import parse_oscal_catalog
        from ctrlmap.models.schemas import SecurityControl

        # Load controls from all three frameworks
        all_controls: list[SecurityControl] = []
        for fpath in sorted(three_enc_frameworks.glob("*.json")):
            controls = parse_oscal_catalog(fpath)
            all_controls.extend(controls)

        assert len(all_controls) == 3

        # Harmonize with a threshold that captures encryption overlap
        common_controls = cluster_controls(
            controls=all_controls,
            similarity_threshold=0.55,
        )

        # THEN: The engine must cluster the three requirements into a single
        # CommonControl object.
        assert len(common_controls) == 1

        cc = common_controls[0]

        # The source_references array must contain exactly three IDs
        # mapping back to the distinct origin documents.
        assert len(cc.source_references) == 3
        assert "NIST-SC-28" in cc.source_references
        assert "SOC2-CC6.1" in cc.source_references
        assert "ISO-A.10.1.1" in cc.source_references

        # Verify the unified description contains content from all sources
        assert len(cc.unified_description) > 0
