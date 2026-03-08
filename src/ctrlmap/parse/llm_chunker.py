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

import json
import re
import sys
import uuid

import ollama
from rich.console import Console

from ctrlmap.models.schemas import ParsedChunk

_DEFAULT_MODEL = "qwen2.5:14b"
_MAX_RETRIES = 2

_console = Console(stderr=True)

_EXTRACT_PROMPT = """\
You are a meticulous GRC (Governance, Risk, Compliance) document analyst. \
Your job is to extract EVERY security control and requirement from policy text. \
Missing even one control is a critical failure.

Below is the raw text from **page {page_number}** of the policy document \
"{document_name}".

## Raw Page Text
{page_text}

## What counts as a control
Extract ANY statement that:
- Mandates an action (uses words like MUST, SHALL, REQUIRED, PROHIBITED)
- Sets a constraint (minimum length, timeframe, frequency)
- Defines an exception or compensating control
- Specifies a review cycle or retention period
- Requires logging, monitoring, or alerting
- Assigns responsibility to a role or department

## Rules
1. Extract EVERY individual control — it is better to extract too many than \
to miss one.
2. Each control must be COMPLETE and self-contained.
3. Do NOT include boilerplate (title pages, disclaimers, page numbers, \
confidentiality notices, version info).
4. Do NOT merge separate requirements — if a paragraph contains two distinct \
obligations, extract them separately.
5. DO include conditional requirements (e.g. "In cases where X, then Y must \
be done").
6. Include the section header each control belongs to.
7. Output controls in the SAME ORDER they appear in the text, from top to \
bottom. Do not reorder or group them.

## Output format
Respond ONLY with a JSON array. Each element must have:
- "section": the section header/number (string)
- "text": the full control statement (string)

Example:
[
  {{"section": "2.1 Unique User Identification", "text": "All users must be \
assigned a unique user ID before they are allowed access to any system \
component or cardholder data."}},
  {{"section": "2.1 Unique User Identification", "text": "In cases where \
shared accounts are technically unavoidable, compensating controls including \
enhanced logging and dual-authorization must be implemented and documented."}}
]

If the page contains no extractable controls (e.g. cover page), respond \
with: []
"""

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
    model: str,
) -> list[dict[str, str]]:
    """Send one text section to the LLM and parse the response.

    Retries up to ``_MAX_RETRIES`` times on parse failure.

    Returns:
        A list of dicts with ``section`` and ``text`` keys.
    """
    prompt = _EXTRACT_PROMPT.format(
        page_number=page_number,
        document_name=document_name,
        page_text=section_text,
    )

    for attempt in range(_MAX_RETRIES + 1):
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_response = str(response.message.content).strip()
        controls = _parse_llm_response(raw_response)

        if controls:
            return controls

        if attempt < _MAX_RETRIES:
            _console.print(
                f"[yellow]  Page {page_number}: JSON parse failed, "
                f"retrying ({attempt + 1}/{_MAX_RETRIES})…[/]"
            )
        else:
            _console.print(
                f"[red]  Page {page_number}: extraction failed "
                f"after {_MAX_RETRIES + 1} attempts "
                f"({len(section_text)} chars).[/]"
            )
            print(
                f"DEBUG page {page_number} raw LLM response:\n{raw_response[:500]}",
                file=sys.stderr,
            )

    return []


def extract_controls_with_llm(
    pages: list[dict[str, str | int]],
    *,
    document_name: str,
    model: str = _DEFAULT_MODEL,
) -> list[ParsedChunk]:
    """Extract individual controls from raw page text using a local LLM.

    Dense pages (> 1500 chars) are split into per-section segments
    so the LLM processes a focused block of text and doesn't truncate
    or drop controls.

    Args:
        pages: List of dicts with ``page_number`` (int) and ``text`` (str).
        document_name: Source document filename.
        model: Ollama model name (default: ``llama3``).

    Returns:
        A list of ``ParsedChunk`` instances, one per extracted control.
    """
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
                model=model,
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
                    _console.print(
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


def _parse_llm_response(raw: str) -> list[dict[str, str]]:
    """Parse the LLM's JSON array response, handling common formatting issues.

    Args:
        raw: Raw LLM response string.

    Returns:
        A list of dicts with ``section`` and ``text`` keys.
    """
    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1 :]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Fallback: try to find JSON array in the response
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            result = json.loads(cleaned[start : end + 1])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    return []
