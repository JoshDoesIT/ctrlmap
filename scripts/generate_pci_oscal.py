#!/usr/bin/env python3
"""Generate the PCI DSS v4.0.1 OSCAL catalog from the Prioritized Approach XLSX.

Reads every control from the XLSX spreadsheet and produces an OSCAL-lite
JSON catalog in ``demo/frameworks/pci_dss_v4_oscal.json``.

Usage::

    uv run --with openpyxl python scripts/generate_pci_oscal.py
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

import openpyxl  # type: ignore[import-untyped]

XLSX_PATH = Path(__file__).resolve().parent.parent / "Prioritized-Approach-Tool-For-PCI-DSS-v4_0_1.xlsx"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "demo" / "frameworks" / "pci_dss_v4_oscal.json"

# Requirement family titles from the PCI DSS v4.0.1 standard
FAMILY_TITLES: dict[str, str] = {
    "1": "Requirement 1: Install and Maintain Network Security Controls",
    "2": "Requirement 2: Apply Secure Configurations to All System Components",
    "3": "Requirement 3: Protect Stored Account Data",
    "4": "Requirement 4: Protect Cardholder Data with Strong Cryptography During Transmission Over Open, Public Networks",
    "5": "Requirement 5: Protect All Systems and Networks from Malicious Software",
    "6": "Requirement 6: Develop and Maintain Secure Systems and Software",
    "7": "Requirement 7: Restrict Access to System Components and Cardholder Data by Business Need to Know",
    "8": "Requirement 8: Identify Users and Authenticate Access to System Components",
    "9": "Requirement 9: Restrict Physical Access to Cardholder Data",
    "10": "Requirement 10: Log and Monitor All Access to System Components and Cardholder Data",
    "11": "Requirement 11: Test Security of Systems and Networks Regularly",
    "12": "Requirement 12: Support Information Security with Organizational Policies and Programs",
}


def _extract_controls(xlsx_path: Path) -> dict[str, list[tuple[str, str]]]:
    """Extract controls from XLSX, grouped by requirement family.

    Returns:
        Dict mapping family number (e.g. "1") to list of (control_id, prose) tuples.
    """
    wb = openpyxl.load_workbook(str(xlsx_path), data_only=True)
    ws = wb["Prioritized Approach Milestones"]

    families: dict[str, list[tuple[str, str]]] = {}
    seen: dict[str, str] = {}  # control_id -> prose (for dedup)

    for row in ws.iter_rows(min_row=1, values_only=True):
        cell = row[0]
        if not cell or not isinstance(cell, str) or not cell[0].isdigit():
            continue

        text = cell.strip()

        # Primary pattern: "1.2.3 Some text..." with dot-separated ID
        match = re.match(r"^(\d+(?:\.\d+)+)\s+(.*)", text, re.DOTALL)
        if match:
            control_id = match.group(1)
            prose = match.group(2).strip()

            # Check for space-separated continuation like "11.2 2 Some text"
            # where the actual ID is "11.2.2"
            continuation = re.match(r"^(\d+)\s+(.*)", prose, re.DOTALL)
            if continuation:
                extended_id = f"{control_id}.{continuation.group(1)}"
                # Only treat as continuation if the extended ID looks valid
                # (i.e., it's a plausible PCI control ID)
                extended_prose = continuation.group(2).strip()
                if extended_prose and not extended_prose[0].isdigit():
                    control_id = extended_id
                    prose = extended_prose
        else:
            # Fallback: no space between ID and text
            match = re.match(r"^(\d+(?:\.\d+)+)(.*)", text, re.DOTALL)
            if not match:
                continue
            control_id = match.group(1)
            prose = match.group(2).strip()

        # Deduplicate: keep the entry with the longer prose
        if control_id in seen:
            if len(prose) <= len(seen[control_id]):
                continue
            # Replace existing entry in its family
            family = control_id.split(".")[0]
            if family in families:
                families[family] = [
                    (cid, p) if cid != control_id else (cid, prose)
                    for cid, p in families[family]
                ]
            seen[control_id] = prose
            continue

        seen[control_id] = prose
        family = control_id.split(".")[0]
        if family not in families:
            families[family] = []
        families[family].append((control_id, prose))

    wb.close()
    return families


def _build_oscal_control(control_id: str, prose: str) -> dict:
    """Build a single OSCAL control entry."""
    safe_id = control_id.replace(".", "-")
    return {
        "id": f"pci-{safe_id}",
        "title": f"PCI DSS {control_id}",
        "props": [{"name": "label", "value": control_id}],
        "parts": [
            {
                "id": f"pci-{safe_id}_smt",
                "name": "statement",
                "prose": prose,
            }
        ],
    }


def _build_oscal_catalog(families: dict[str, list[tuple[str, str]]]) -> dict:
    """Build the full OSCAL catalog structure."""
    groups = []

    for fam_num in sorted(families, key=int):
        controls_data = families[fam_num]
        title = FAMILY_TITLES.get(fam_num, f"Requirement {fam_num}")

        # Separate parent controls (e.g. 1.2) from leaf controls (e.g. 1.2.1)
        # Parent controls with depth <= 2 become group-level controls
        # Their children become nested sub-controls
        parent_map: dict[str, dict] = {}
        leaf_controls: list[dict] = []

        for cid, prose in sorted(controls_data, key=lambda x: [int(p) for p in x[0].split(".")]):
            parts = cid.split(".")
            oscal_ctrl = _build_oscal_control(cid, prose)

            if len(parts) == 2:
                # Section header like 1.2 — NOT testable, just store for nesting
                parent_map[cid] = oscal_ctrl
            elif len(parts) >= 3:
                # Testable sub-control like 1.2.1 or 1.2.1.1
                leaf_controls.append(oscal_ctrl)
            else:
                # Single-digit like just "1" - skip, these are section headers
                continue

        groups.append(
            {
                "id": f"req-{fam_num}",
                "title": title,
                "controls": leaf_controls,
            }
        )

    return {
        "catalog": {
            "uuid": str(uuid.uuid4()),
            "metadata": {
                "title": "PCI DSS v4.0.1",
                "version": "4.0.1",
                "oscal-version": "1.1.2",
            },
            "groups": groups,
        }
    }


def main() -> None:
    """Extract PCI controls from XLSX and write OSCAL JSON."""
    print(f"Reading controls from: {XLSX_PATH.name}")
    families = _extract_controls(XLSX_PATH)

    total = sum(len(v) for v in families.values())
    print(f"  Extracted {total} controls across {len(families)} requirement families")

    catalog = _build_oscal_catalog(families)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")

    # Count controls in output
    out_count = 0
    for g in catalog["catalog"]["groups"]:
        for c in g["controls"]:
            out_count += 1
            out_count += len(c.get("controls", []))

    print(f"  Wrote {out_count} controls to: {OUTPUT_PATH.relative_to(XLSX_PATH.parent)}")
    print("Done!")


if __name__ == "__main__":
    main()
