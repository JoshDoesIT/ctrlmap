#!/usr/bin/env python3
"""Merge multiple framework mapping JSON files into a unified HTML report.

Reads JSON mapping outputs from separate ctrlmap ``map`` runs (one per
framework) and produces a single interactive HTML report combining all
frameworks with search, document reader, and optional embedded PDF views.

Usage::

    python scripts/merge_reports.py \\
        --inputs nist_mapping.json,pci_mapping.json \\
        --chunks all_chunks.jsonl \\
        --pdf-dir demo/policies \\
        --output report.html
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ctrlmap.export.html_formatter import export_html  # noqa: E402
from ctrlmap.models.schemas import MappedResult, ParsedChunk  # noqa: E402


def _load_results(path: Path) -> list[MappedResult]:
    """Deserialize a JSON file of serialized MappedResult dicts.

    For dot-hierarchical frameworks (e.g. PCI DSS), filters out
    non-testable parent-level controls (e.g. ``1.1``, ``1.2``) that are
    section headers, keeping only leaf-level sub-requirements
    (e.g. ``1.1.1``, ``1.2.1``).

    Frameworks with non-dot ID formats (e.g. NIST ``AC-1``, ``SC-28``)
    are returned unfiltered.
    """
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    results = [MappedResult.model_validate(item, strict=False) for item in raw]

    # Only apply the dot-level parent filter to frameworks that use
    # dot-hierarchical numbering (e.g. PCI DSS "1.2.4").  Detect this
    # by checking if the first control's ID contains a dot.
    if results and "." in results[0].control.control_id:
        filtered = [
            r for r in results
            if len(r.control.control_id.split(".")) >= 3
        ]
        if len(filtered) < len(results):
            print(f"  Filtered {len(results) - len(filtered)} parent-level section headers")
        return filtered

    return results


def _load_chunks(path: Path) -> list[ParsedChunk]:
    """Load chunks from a JSONL file."""
    chunks: list[ParsedChunk] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(ParsedChunk.model_validate_json(line))
    return chunks


def _render_pdfs(
    pdf_dir: Path,
    all_chunks: list[ParsedChunk],
    all_results: list[MappedResult],
) -> list[Any]:
    """Render PDF pages and compute chunk overlay positions.

    Returns a list of ``RenderedDocument`` objects.
    """
    from ctrlmap.export.pdf_renderer import render_document

    # Group chunks by document name
    doc_chunks: dict[str, list[ParsedChunk]] = defaultdict(list)
    for chunk in all_chunks:
        doc_chunks[chunk.document_name].append(chunk)

    # Build chunk→control info index
    chunk_controls: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in all_results:
        ctrl = result.control
        label = f"{ctrl.framework} {ctrl.control_id}"
        for chunk in result.supporting_chunks:
            chunk_controls[chunk.chunk_id].append(label)

    rendered = []
    for doc_name in sorted(doc_chunks):
        pdf_path = pdf_dir / doc_name
        if not pdf_path.exists():
            print(f"[!] PDF not found: {pdf_path}, skipping PDF render", file=sys.stderr)
            continue

        print(f"[+] Rendering {doc_name}...")
        doc = render_document(
            pdf_path,
            doc_chunks[doc_name],
            chunk_controls,
        )
        n_overlays = sum(len(p.overlays) for p in doc.pages)
        print(f"    {len(doc.pages)} pages, {n_overlays} chunk overlays")
        rendered.append(doc)

    return rendered


def main() -> None:
    """Parse arguments and produce the merged report."""
    parser = argparse.ArgumentParser(description="Merge framework mappings into unified HTML.")
    parser.add_argument(
        "--inputs",
        required=True,
        help="Comma-separated paths to JSON mapping files.",
    )
    parser.add_argument(
        "--chunks",
        required=True,
        help="Path to the merged all_chunks.jsonl file.",
    )
    parser.add_argument(
        "--pdf-dir",
        default=None,
        help="Path to directory containing source PDF files. "
        "When provided, the Document Reader shows actual PDF pages.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for the unified HTML report.",
    )
    args = parser.parse_args()

    input_paths = [Path(p.strip()) for p in args.inputs.split(",")]
    chunks_path = Path(args.chunks)
    output_path = Path(args.output)

    # Load all framework results
    results_by_framework: dict[str, list[MappedResult]] = {}
    for path in input_paths:
        if not path.exists():
            print(f"[!] Skipping missing file: {path}", file=sys.stderr)
            continue
        results = _load_results(path)
        if results:
            framework = results[0].control.framework
            results_by_framework[framework] = results
            print(f"[+] Loaded {len(results)} controls from {path} ({framework})")

    if not results_by_framework:
        print("[!] No results loaded. Aborting.", file=sys.stderr)
        sys.exit(1)

    # Load chunks
    all_chunks = _load_chunks(chunks_path)
    print(f"[+] Loaded {len(all_chunks)} chunks from {chunks_path}")

    # Merge all results into a flat list
    all_results = [r for rs in results_by_framework.values() for r in rs]

    # Optionally render PDFs
    pdf_documents = None
    if args.pdf_dir:
        pdf_dir = Path(args.pdf_dir)
        if pdf_dir.is_dir():
            pdf_documents = _render_pdfs(pdf_dir, all_chunks, all_results)
            print(f"[+] Rendered {len(pdf_documents)} PDF documents")
        else:
            print(f"[!] PDF directory not found: {pdf_dir}", file=sys.stderr)

    # Generate unified report
    export_html(
        all_results,
        output_path,
        all_chunks=all_chunks,
        results_by_framework=results_by_framework,
        pdf_documents=pdf_documents,
    )
    total = sum(len(rs) for rs in results_by_framework.values())
    fws = ", ".join(results_by_framework.keys())
    print(f"[+] Generated unified report: {output_path} ({total} controls across {fws})")


if __name__ == "__main__":
    main()
