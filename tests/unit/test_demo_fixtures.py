"""Tests for demo fixture files.

Verifies that the demo data kit (PCI DSS OSCAL framework and synthetic
policy PDFs) is valid and usable by the ctrlmap pipeline.
"""

from pathlib import Path

import pytest

DEMO_DIR = Path(__file__).parent.parent.parent / "demo"

_POLICIES_DIR = DEMO_DIR / "policies"
_ALL_POLICY_PDFS = [
    "access_control_policy.pdf",
    "data_protection_policy.pdf",
    "network_security_policy.pdf",
    "incident_response_policy.pdf",
    "security_awareness_policy.pdf",
    "change_management_policy.pdf",
    "physical_security_policy.pdf",
]
_DEMO_PDFS_EXIST = all((_POLICIES_DIR / pdf).exists() for pdf in _ALL_POLICY_PDFS)


class TestPciDssOscalFixture:
    """Tests for the PCI DSS OSCAL framework file."""

    def test_pci_dss_oscal_is_parseable(self) -> None:
        """PCI DSS OSCAL JSON file parses without error and contains expected controls."""
        from ctrlmap.models.oscal import parse_oscal_catalog

        controls = parse_oscal_catalog(DEMO_DIR / "frameworks" / "pci_dss_v4_oscal.json")
        assert len(controls) >= 60

    def test_pci_dss_controls_have_framework_set(self) -> None:
        """All PCI DSS controls should have framework='PCI-DSS'."""
        from ctrlmap.models.oscal import parse_oscal_catalog

        controls = parse_oscal_catalog(DEMO_DIR / "frameworks" / "pci_dss_v4_oscal.json")
        for c in controls:
            assert c.framework == "PCI-DSS"

    def test_pci_dss_covers_all_twelve_requirement_groups(self) -> None:
        """PCI DSS fixture should span all 12 requirement groups."""
        from ctrlmap.models.oscal import parse_oscal_catalog

        controls = parse_oscal_catalog(DEMO_DIR / "frameworks" / "pci_dss_v4_oscal.json")
        # Control IDs like "1.1.1", "3.2.1", etc. — first digit(s) = requirement group
        groups = {c.control_id.split(".")[0] for c in controls}
        assert len(groups) >= 12


@pytest.mark.skipif(
    not _DEMO_PDFS_EXIST,
    reason="Demo PDFs not generated",
)
class TestDemoPolicyPdfs:
    """Tests for the synthetic demo policy PDFs."""

    @pytest.mark.parametrize("pdf_name", _ALL_POLICY_PDFS)
    def test_policy_pdf_is_extractable(self, pdf_name: str) -> None:
        """Each policy PDF should yield text blocks via PyMuPDF."""
        from ctrlmap.parse.extractor import extract_text_blocks

        blocks = extract_text_blocks(DEMO_DIR / "policies" / pdf_name)
        assert len(blocks) > 10

    def test_access_control_policy_contains_security_language(self) -> None:
        """Access control PDF should contain recognizable security policy language."""
        from ctrlmap.parse.extractor import extract_text_blocks

        blocks = extract_text_blocks(DEMO_DIR / "policies" / "access_control_policy.pdf")
        all_text = " ".join(b.text.lower() for b in blocks)
        assert "multi-factor authentication" in all_text or "mfa" in all_text
        assert "access" in all_text

    def test_physical_security_policy_contains_facility_language(self) -> None:
        """Physical security PDF should contain physical access language."""
        from ctrlmap.parse.extractor import extract_text_blocks

        blocks = extract_text_blocks(DEMO_DIR / "policies" / "physical_security_policy.pdf")
        all_text = " ".join(b.text.lower() for b in blocks)
        assert "facility" in all_text or "physical access" in all_text
        assert "visitor" in all_text
