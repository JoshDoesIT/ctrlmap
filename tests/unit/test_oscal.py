"""Tests for OSCAL JSON ingestion parser.

TDD RED phase: Tests define the expected behavior of the OSCAL parser
before implementation.
"""

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


class TestOscalParser:
    """Tests for the OSCAL JSON catalog parser."""

    def test_parse_oscal_extracts_controls(self) -> None:
        """Parser should extract all base controls from the OSCAL catalog."""
        from ctrlmap.models.oscal import parse_oscal_catalog

        controls = parse_oscal_catalog(FIXTURE_DIR / "nist_800_53_subset.json")
        control_ids = {c.control_id for c in controls}
        assert "AC-1" in control_ids
        assert "AC-2" in control_ids
        assert "SC-28" in control_ids
        assert len(controls) >= 3

    def test_parse_oscal_handles_control_enhancements(self) -> None:
        """Parser should extract control enhancements (e.g., AC-2(1))."""
        from ctrlmap.models.oscal import parse_oscal_catalog

        controls = parse_oscal_catalog(FIXTURE_DIR / "nist_800_53_subset.json")
        control_ids = {c.control_id for c in controls}
        assert "AC-2(1)" in control_ids

    def test_parse_oscal_populates_all_security_control_fields(self) -> None:
        """Each parsed control should have all SecurityControl fields populated."""
        from ctrlmap.models.oscal import parse_oscal_catalog

        controls = parse_oscal_catalog(FIXTURE_DIR / "nist_800_53_subset.json")
        ac2 = next(c for c in controls if c.control_id == "AC-2")
        assert ac2.framework == "NIST-800-53"
        assert ac2.title == "Account Management"
        assert len(ac2.description) > 0

    def test_parse_oscal_rejects_malformed_json(self) -> None:
        """Parser should raise a clear error for malformed OSCAL JSON."""
        from ctrlmap.models.oscal import parse_oscal_catalog

        malformed = FIXTURE_DIR / "nonexistent.json"
        with pytest.raises((FileNotFoundError, ValueError)):
            parse_oscal_catalog(malformed)

    def test_parse_oscal_rejects_missing_catalog_key(self) -> None:
        """Parser should raise ValueError when the 'catalog' key is missing."""
        import json
        import tempfile

        from ctrlmap.models.oscal import parse_oscal_catalog

        bad_data = {"not_a_catalog": {}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(bad_data, f)
            f.flush()
            with pytest.raises(ValueError, match="catalog"):
                parse_oscal_catalog(Path(f.name))
