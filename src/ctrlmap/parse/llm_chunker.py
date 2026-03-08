"""LLM-based control extraction from raw PDF text.

Uses a local Ollama model to extract individual security controls
from raw PDF page text.  This replaces heuristic regex-based
chunking with a single LLM call per page that understands context
and produces clean, sentence-aligned control statements.

Each extracted control becomes a ``ParsedChunk`` with accurate
section headers and page numbers — no paragraph-joining, sentence
healing, or boilerplate filtering needed.

Performance:
    Uses ``asyncio.gather()`` with bounded semaphore to process
    multiple page segments concurrently, replacing the previous
    serial loop.  Uses the fast 7B model by default.
"""

from __future__ import annotations

import asyncio
import re
import uuid

from ctrlmap._console import err_console
from ctrlmap._defaults import DEFAULT_FAST_MODEL
from ctrlmap.llm._json_utils import extract_json_array
from ctrlmap.llm.client import OllamaClient
from ctrlmap.llm.prompts import load_prompt
from ctrlmap.models.schemas import ParsedChunk

_MAX_RETRIES = 2


_SECTION_HEADER_RE = re.compile(r"^\d+(?:\.\d+)*\s{2,}\S", re.MULTILINE)

# Max chars per LLM call — pages larger than this get split into sections
_PAGE_SPLIT_THRESHOLD = 1500

# Default concurrency for async extraction
_DEFAULT_CONCURRENCY = 4


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


async def _extract_section_async(
    *,
    section_text: str,
    page_number: int,
    document_name: str,
    client: OllamaClient,
    semaphore: asyncio.Semaphore,
) -> list[dict[str, str]]:
    """Send one text section to the LLM (async) and parse the response.

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
        async with semaphore:
            raw_response = (await client.call_llm_async(prompt, "control_extraction")).strip()
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


def _extract_section(
    *,
    section_text: str,
    page_number: int,
    document_name: str,
    client: OllamaClient,
) -> list[dict[str, str]]:
    """Send one text section to the LLM and parse the response (sync).

    Retained for backward compatibility. Prefer the async variant.

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
        raw_response = client.call_llm(prompt, "control_extraction").strip()
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


def _build_chunks_from_controls(
    controls: list[dict[str, str]],
    *,
    page_number: int,
    document_name: str,
    segment: str,
) -> list[ParsedChunk]:
    """Convert extracted control dicts to ParsedChunk instances.

    Verifies each control exists in the source segment to catch
    LLM hallucinations.

    Args:
        controls: List of dicts with ``section`` and ``text`` keys.
        page_number: Source page number.
        document_name: Source document name.
        segment: The original text segment (for hallucination checks).

    Returns:
        A list of ``ParsedChunk`` instances.
    """
    _norm_seg = " ".join(segment.split())

    def _text_position(ctrl: dict[str, str], _seg: str = _norm_seg) -> int:
        text = ctrl.get("text", "").strip()
        needle = " ".join(text[:60].split())
        pos = _seg.find(needle)
        return pos if pos >= 0 else len(_seg)

    controls.sort(key=_text_position)

    chunks: list[ParsedChunk] = []
    for ctrl in controls:
        text = ctrl.get("text", "").strip()
        section = ctrl.get("section", "").strip() or None
        if len(text) < 50:
            continue

        # Verify the control text exists in the source segment
        verify_needle = " ".join(text[:30].split())
        if _norm_seg.find(verify_needle) < 0:
            err_console.print(
                f'[yellow]  Page {page_number}: dropped hallucinated control "{text[:60]}…"[/]'
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


def extract_controls_with_llm(
    pages: list[dict[str, str | int]],
    *,
    document_name: str,
    model: str = DEFAULT_FAST_MODEL,
) -> list[ParsedChunk]:
    """Extract individual controls from raw page text using a local LLM.

    Dense pages (> 1500 chars) are split into per-section segments
    so the LLM processes a focused block of text and doesn't truncate
    or drop controls.

    Uses ``asyncio`` for concurrent extraction across all segments.

    Args:
        pages: List of dicts with ``page_number`` (int) and ``text`` (str).
        document_name: Source document filename.
        model: Ollama model name (default: fast 7B model).

    Returns:
        A list of ``ParsedChunk`` instances, one per extracted control.
    """
    return asyncio.run(_extract_async(pages, document_name=document_name, model=model))


async def _extract_async(
    pages: list[dict[str, str | int]],
    *,
    document_name: str,
    model: str,
) -> list[ParsedChunk]:
    """Async extraction pipeline — concurrent across page segments.

    Args:
        pages: List of dicts with ``page_number`` (int) and ``text`` (str).
        document_name: Source document filename.
        model: Ollama model name.

    Returns:
        A list of ``ParsedChunk`` instances, one per extracted control.
    """
    client = OllamaClient(model=model)
    semaphore = asyncio.Semaphore(_DEFAULT_CONCURRENCY)

    # Build all (segment, page_number) pairs
    tasks: list[asyncio.Task[list[dict[str, str]]]] = []
    segment_info: list[tuple[str, int]] = []  # (segment_text, page_number)

    for page in pages:
        page_number = int(page["page_number"])
        page_text = str(page["text"]).strip()

        if len(page_text) < 50:
            continue

        segments = _split_page_into_sections(page_text)

        for segment in segments:
            if len(segment) < 50:
                continue

            segment_info.append((segment, page_number))
            tasks.append(
                asyncio.ensure_future(
                    _extract_section_async(
                        section_text=segment,
                        page_number=page_number,
                        document_name=document_name,
                        client=client,
                        semaphore=semaphore,
                    )
                )
            )

    if not tasks:
        return []

    # Run all extractions concurrently
    all_results = await asyncio.gather(*tasks)

    # Build chunks from results
    chunks: list[ParsedChunk] = []
    for (segment, page_number), controls in zip(segment_info, all_results, strict=True):
        chunks.extend(
            _build_chunks_from_controls(
                controls,
                page_number=page_number,
                document_name=document_name,
                segment=segment,
            )
        )

    return chunks
