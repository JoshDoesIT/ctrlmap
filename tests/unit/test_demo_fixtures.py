"""Tests for demo fixture files.

Verifies that the demo data kit (PCI DSS OSCAL framework and synthetic
policy PDFs) is valid and usable by the ctrlmap pipeline.
"""

from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent.parent / "demo"

_POLICIES_DIR = DEMO_DIR / "policies"
_DEMO_PDFS_EXIST = (
    (_POLICIES_DIR / "access_control_policy.pdf").exists()
    and (_POLICIES_DIR / "data_protection_policy.pdf").exists()
    and (_POLICIES_DIR / "network_security_policy.pdf").exists()
)


class TestPciDssOscalFixture:
    """Tests for the PCI DSS OSCAL framework file."""

    def test_pci_dss_oscal_is_parseable(self) -> None:
        """PCI DSS OSCAL JSON file parses without error."""
        from ctrlmap.models.oscal import parse_oscal_catalog

        controls = parse_oscal_catalog(DEMO_DIR / "frameworks" / "pci_dss_v4_oscal.json")
        assert len(controls) >= 25

    def test_pci_dss_controls_have_framework_set(self) -> None:
        """All PCI DSS controls should have framework='PCI-DSS'."""
        from ctrlmap.models.oscal import parse_oscal_catalog

        controls = parse_oscal_catalog(DEMO_DIR / "frameworks" / "pci_dss_v4_oscal.json")
        for c in controls:
            assert c.framework == "PCI-DSS"

    def test_pci_dss_covers_multiple_requirement_groups(self) -> None:
        """PCI DSS fixture should span at least 3 requirement groups."""
        from ctrlmap.models.oscal import parse_oscal_catalog

        controls = parse_oscal_catalog(DEMO_DIR / "frameworks" / "pci_dss_v4_oscal.json")
        # Control IDs like "1.1.1", "3.2.1", etc. — first digit = requirement group
        groups = {c.control_id.split(".")[0] for c in controls}
        assert len(groups) >= 3


@pytest.mark.skipif(
    not _DEMO_PDFS_EXIST,
    reason="Demo PDFs not generated",
)
class TestDemoPolicyPdfs:
    """Tests for the synthetic demo policy PDFs."""

    def test_access_control_policy_is_extractable(self) -> None:
        """Access control PDF should yield text blocks via PyMuPDF."""
        from ctrlmap.parse.extractor import extract_text_blocks

        blocks = extract_text_blocks(DEMO_DIR / "policies" / "access_control_policy.pdf")
        assert len(blocks) > 10

    def test_data_protection_policy_is_extractable(self) -> None:
        """Data protection PDF should yield text blocks via PyMuPDF."""
        from ctrlmap.parse.extractor import extract_text_blocks

        blocks = extract_text_blocks(DEMO_DIR / "policies" / "data_protection_policy.pdf")
        assert len(blocks) > 10

    def test_network_security_policy_is_extractable(self) -> None:
        """Network security PDF should yield text blocks via PyMuPDF."""
        from ctrlmap.parse.extractor import extract_text_blocks

        blocks = extract_text_blocks(DEMO_DIR / "policies" / "network_security_policy.pdf")
        assert len(blocks) > 10

    def test_policy_pdfs_contain_security_language(self) -> None:
        """Demo PDFs should contain recognizable security policy language."""
        from ctrlmap.parse.extractor import extract_text_blocks

        blocks = extract_text_blocks(DEMO_DIR / "policies" / "access_control_policy.pdf")
        all_text = " ".join(b.text.lower() for b in blocks)
        assert "multi-factor authentication" in all_text or "mfa" in all_text
        assert "access" in all_text
