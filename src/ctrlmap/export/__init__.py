"""ctrlmap.export: Output formatters for compliance mapping results.

Public API:
    export_csv / format_csv: CSV output (one row per control-chunk pair).
    export_markdown / format_markdown: Markdown report with evidence tables.
    export_oscal / format_oscal: OSCAL-aligned assessment results JSON.
    export_html / format_html: Interactive single-file HTML dashboard.
    atomic_write: Shared atomic file-write utility.
"""

from ctrlmap.export._io import atomic_write
from ctrlmap.export.csv_formatter import export_csv, format_csv
from ctrlmap.export.html_formatter import export_html, format_html
from ctrlmap.export.markdown_formatter import export_markdown, format_markdown
from ctrlmap.export.oscal_formatter import export_oscal, format_oscal

__all__ = [
    "atomic_write",
    "export_csv",
    "export_html",
    "export_markdown",
    "export_oscal",
    "format_csv",
    "format_html",
    "format_markdown",
    "format_oscal",
]
