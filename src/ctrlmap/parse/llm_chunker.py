"""LLM-based control extraction from raw PDF text.

Uses a local Ollama model to extract individual security controls
from raw PDF page text.  This replaces heuristic regex-based
chunking with a single LLM call per page that understands context
and produces clean, sentence-aligned control statements.

Each extracted control becomes a ``ParsedChunk`` with accurate
section headers and page numbers — no paragraph-joining, sentence
healing, or boilerplate filtering needed.
"""

from __future__ import annotations

import re
import uuid

from ctrlmap._console import err_console
from ctrlmap._defaults import DEFAULT_LLM_MODEL
from ctrlmap.llm._json_utils import extract_json_array
from ctrlmap.llm.client import OllamaClient
from ctrlmap.llm.prompts import load_prompt
from ctrlmap.models.schemas import ParsedChunk

_MAX_RETRIES = 2


_SECTION_HEADER_RE = re.compile(r"^\d+(?:\.\d+)*\s{2,}\S", re.MULTILINE)

# Max chars per LLM call — pages larger than this get split into sections
_PAGE_SPLIT_THRESHOLD = 1500


def _split_page_into_sections(page_text: str) -> list[str]:
    """Split a dense page into smaller sections at header boundaries.

    If the page text is short enough, it's returned as a single segment.
    For dense pages, it's split at numbered section headers (e.g.,
    ``2.1  Unique User Identification``).

    Args:
        page_text: Raw page text.

    Returns:
        A list of text segments, each small enough for one LLM call.
    """
    if len(page_text) <= _PAGE_SPLIT_THRESHOLD:
        return [page_text]

    # Find all section header positions
    matches = list(_SECTION_HEADER_RE.finditer(page_text))
    if not matches:
        return [page_text]

    segments: list[str] = []

    # Text before the first header (preamble)
    preamble = page_text[: matches[0].start()].strip()
    if preamble:
        segments.append(preamble)

    # Each header → next header (or end)
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(page_text)
        segment = page_text[start:end].strip()
        if segment:
            segments.append(segment)

    return segments


def _extract_section(
    *,
    section_text: str,
    page_number: int,
    document_name: str,
    client: OllamaClient,
) -> list[dict[str, str]]:
    """Send one text section to the LLM and parse the response.

    Retries up to ``_MAX_RETRIES`` times on parse failure.

    Returns:
        A list of dicts with ``section`` and ``text`` keys.
    """
    template = load_prompt("control_extraction.txt")
    prompt = template.format(
        page_number=page_number,
        document_name=document_name,
        page_text=section_text,
    )

    for attempt in range(_MAX_RETRIES + 1):
        raw_response = client._call_llm(prompt, "control_extraction").strip()
        controls = extract_json_array(raw_response)

        if controls:
            return controls

        if attempt < _MAX_RETRIES:
            err_console.print(
                f"[yellow]  Page {page_number}: JSON parse failed, "
                f"retrying ({attempt + 1}/{_MAX_RETRIES})…[/]"
            )
        else:
            err_console.print(
                f"[red]  Page {page_number}: extraction failed "
                f"after {_MAX_RETRIES + 1} attempts "
                f"({len(section_text)} chars).[/]"
            )
            err_console.print(
                f"[dim]DEBUG page {page_number} raw LLM response:\n{raw_response[:500]}[/]",
            )

    return []


def extract_controls_with_llm(
    pages: list[dict[str, str | int]],
    *,
    document_name: str,
    model: str = DEFAULT_LLM_MODEL,
) -> list[ParsedChunk]:
    """Extract individual controls from raw page text using a local LLM.

    Dense pages (> 1500 chars) are split into per-section segments
    so the LLM processes a focused block of text and doesn't truncate
    or drop controls.

    Args:
        pages: List of dicts with ``page_number`` (int) and ``text`` (str).
        document_name: Source document filename.
        model: Ollama model name (default: ``qwen2.5:14b``).

    Returns:
        A list of ``ParsedChunk`` instances, one per extracted control.
    """
    client = OllamaClient(model=model)
    chunks: list[ParsedChunk] = []

    for page in pages:
        page_number = int(page["page_number"])
        page_text = str(page["text"]).strip()

        if len(page_text) < 50:
            continue

        segments = _split_page_into_sections(page_text)

        for segment in segments:
            if len(segment) < 50:
                continue

            controls = _extract_section(
                section_text=segment,
                page_number=page_number,
                document_name=document_name,
                client=client,
            )

            # Re-sort by text position in the original segment
            # to guarantee document order regardless of LLM output order.
            # Normalize whitespace: PDF text has embedded line breaks that
            # the LLM strips out, causing str.find() to miss matches.
            _norm_seg = " ".join(segment.split())

            def _text_position(ctrl: dict[str, str], _seg: str = _norm_seg) -> int:
                text = ctrl.get("text", "").strip()
                needle = " ".join(text[:60].split())
                pos = _seg.find(needle)
                return pos if pos >= 0 else len(_seg)

            controls.sort(key=_text_position)

            for ctrl in controls:
                text = ctrl.get("text", "").strip()
                section = ctrl.get("section", "").strip() or None
                if len(text) < 50:
                    continue

                # Verify the control text exists in the source segment
                # to catch LLM hallucinations. Use first 30 chars normalized.
                verify_needle = " ".join(text[:30].split())
                if _norm_seg.find(verify_needle) < 0:
                    err_console.print(
                        f"[yellow]  Page {page_number}: dropped "
                        f"hallucinated control "
                        f'"{text[:60]}…"[/]'
                    )
                    continue

                chunks.append(
                    ParsedChunk(
                        chunk_id=str(uuid.uuid4()),
                        document_name=document_name,
                        page_number=page_number,
                        raw_text=text,
                        section_header=section,
                    )
                )

    return chunks



