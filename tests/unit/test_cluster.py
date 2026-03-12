"""Tests for vector-based clustering of overlapping controls.

TDD RED phase: Story #17, group semantically overlapping controls.
Ref: GitHub Issue #17.
"""

from __future__ import annotations

from ctrlmap.models.schemas import SecurityControl


def _make_controls() -> list[SecurityControl]:
    """Create test controls with known semantic relationships."""
    return [
        # Three controls about encryption at rest, should cluster
        SecurityControl(
            control_id="NIST-SC-28",
            framework="NIST-800-53",
            title="Protection of Information at Rest",
            description="Protect the confidentiality and integrity of information at rest.",
        ),
        SecurityControl(
            control_id="SOC2-CC6.1",
            framework="SOC2",
            title="Data Encryption at Rest",
            description="Encrypt all sensitive data at rest using approved encryption algorithms.",
        ),
        SecurityControl(
            control_id="ISO-A.10.1.1",
            framework="ISO-27001",
            title="Cryptographic Controls for Data at Rest",
            description="Implement cryptographic controls to protect data confidentiality at rest.",
        ),
        # One unrelated control about physical security, should NOT cluster
        SecurityControl(
            control_id="NIST-PE-3",
            framework="NIST-800-53",
            title="Physical Access Control",
            description="Control physical access to facility and information systems.",
        ),
    ]


class TestVectorClustering:
    """Story #17: Vector-based clustering for overlapping requirements."""

    def test_cluster_identical_controls(self) -> None:
        """Semantically identical controls from different frameworks are grouped together."""
        from ctrlmap.map.cluster import cluster_controls

        controls = _make_controls()
        clusters = cluster_controls(controls=controls, similarity_threshold=0.65)

        # Find the cluster containing the encryption controls
        enc_cluster = None
        for cc in clusters:
            if any("SC-28" in ref for ref in cc.source_references):
                enc_cluster = cc
                break

        assert enc_cluster is not None
        assert len(enc_cluster.source_references) >= 3

    def test_cluster_preserves_source_references(self) -> None:
        """Each CommonControl's source_references links back to original control IDs."""
        from ctrlmap.map.cluster import cluster_controls

        controls = _make_controls()
        clusters = cluster_controls(controls=controls, similarity_threshold=0.55)

        all_refs: list[str] = []
        for cc in clusters:
            all_refs.extend(cc.source_references)

        # Every input control must appear in exactly one cluster
        for ctrl in controls:
            assert ctrl.control_id in all_refs

    def test_cluster_separates_unrelated_controls(self) -> None:
        """Controls with different themes are placed in separate clusters."""
        from ctrlmap.map.cluster import cluster_controls

        controls = _make_controls()
        clusters = cluster_controls(controls=controls, similarity_threshold=0.75)

        # The physical access control should NOT be in the same cluster as encryption
        pe3_cluster = next(cc for cc in clusters if "NIST-PE-3" in cc.source_references)
        assert "NIST-SC-28" not in pe3_cluster.source_references

    def test_configurable_similarity_threshold(self) -> None:
        """A very high threshold should produce more clusters (fewer merges)."""
        from ctrlmap.map.cluster import cluster_controls

        controls = _make_controls()

        # With a low threshold, more controls get merged
        loose_clusters = cluster_controls(controls=controls, similarity_threshold=0.50)

        # With a very high threshold, fewer controls get merged
        strict_clusters = cluster_controls(controls=controls, similarity_threshold=0.99)

        assert len(strict_clusters) >= len(loose_clusters)
