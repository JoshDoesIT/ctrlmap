"""OSCAL JSON catalog parser.

Parses NIST OSCAL-formatted JSON catalogs into ``SecurityControl``
Pydantic model instances. Handles the nested structure of groups →
controls → enhancements.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ctrlmap.models.schemas import SecurityControl


def parse_oscal_catalog(path: Path) -> list[SecurityControl]:
    """Parse an OSCAL JSON catalog file into SecurityControl instances.

    Args:
        path: Path to an OSCAL JSON catalog file.

    Returns:
        A list of SecurityControl instances extracted from the catalog.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the JSON is missing the 'catalog' key.
    """
    with path.open() as f:
        data = json.load(f)

    if "catalog" not in data:
        msg = "Invalid OSCAL file: missing 'catalog' key."
        raise ValueError(msg)

    catalog = data["catalog"]
    controls: list[SecurityControl] = []

    for group in catalog.get("groups", []):
        _extract_controls(group.get("controls", []), controls)

    return controls


def _extract_controls(
    raw_controls: list[dict[str, Any]],
    output: list[SecurityControl],
) -> None:
    """Recursively extract controls and their enhancements."""
    for ctrl in raw_controls:
        label = _get_label(ctrl)
        title = ctrl.get("title", "")
        description = _get_statement_prose(ctrl)

        output.append(
            SecurityControl(
                control_id=label,
                framework="NIST-800-53",
                title=title,
                description=description,
            )
        )

        # Recurse into control enhancements (nested controls)
        for enhancement in ctrl.get("controls", []):
            _extract_controls([enhancement], output)


def _get_label(ctrl: dict[str, Any]) -> str:
    """Extract the human-readable label (e.g., 'AC-2' or 'AC-2(1)') from props."""
    for prop in ctrl.get("props", []):
        if prop.get("name") == "label":
            return str(prop["value"])
    # Fallback to the raw ID
    return str(ctrl.get("id", "UNKNOWN"))


def _get_statement_prose(ctrl: dict[str, Any]) -> str:
    """Extract the statement prose from control parts."""
    for part in ctrl.get("parts", []):
        if part.get("name") == "statement":
            return str(part.get("prose", ""))
    return ""
