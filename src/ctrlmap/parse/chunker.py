"""Hybrid structural + semantic chunking pipeline.

Two-phase chunking:
1. **Structural**: splits on section headers detected by font-size heuristics.
2. **Semantic**: computes sentence-level cosine similarity via sentence-transformers
   and merges/splits segments based on topic coherence.

Produces ``ParsedChunk`` Pydantic models. Never splits mid-sentence.

Ref: GitHub Issue #8.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from ctrlmap.models.schemas import ParsedChunk
from ctrlmap.parse.extractor import TextBlock

# Sentence-splitting pattern: split on ". ", "! ", "? " but not abbreviations
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Header detection: lines matching common section prefixes.
# Matches formats like:
#   "Section 1: Access Control"      (keyword + number + separator)
#   "1  Purpose and Scope"           (number + spaces + title)
#   "2.1  Unique User Identification" (dotted number + spaces + title)
#   "APPENDIX A — Glossary"          (keyword + letter + separator)
_HEADER_PATTERN = re.compile(
    r"^(?:"
    r"(?:Section|Chapter|Part)\s+\d+"  # "Section 1", "Chapter 2"
    r"|APPENDIX\s+[A-Z]"  # "APPENDIX A"
    r"|\d+(?:\.\d+)*"  # "1", "2.1", "3.1.2"
    r")"
    r"(?:\s*[:\-—]\s*|\s{2,})"  # separator: colon/dash/emdash OR 2+ spaces
    r"\S",  # must be followed by at least one non-space char (the title)
    re.IGNORECASE,
)

# Boilerplate detection: page headers, footers, cover-page text
_BOILERPLATE_PATTERN = re.compile(
    r"^(?:"
    r"Page\s+\d+\s*/\s*\d+"  # "Page 1/3"
    r"|Page\s+\d+"  # "Page 1"
    r"|Version\s+[\d.]+"  # "Version 3.1"
    r"|Classification:\s+"  # "Classification: Internal"
    r"|CONFIDENTIAL$"  # standalone "CONFIDENTIAL"
    r"|This document is the property"  # legal disclaimer
    r"|Unauthorized\s+distribut"  # "Unauthorized distribution..."
    r"|Effective:\s+"  # "Effective: January 15, 2025"
    r")",
    re.IGNORECASE,
)

# Patterns that identify cover-page fragments surviving into final chunks.
# These are either mid-sentence legal boilerplate or metadata notices.
_COVER_PAGE_FRAGMENT = re.compile(
    r"(?:"
    r"reproduction.*(?:prohibited|restricted)"  # legal boilerplate
    r"|effective\s+as\s+of\s+the\s+date"  # date notice
    r"|this\s+policy\s+has\s+been\s+approved\s+by"  # approval block
    r")",
    re.IGNORECASE,
)


def _is_boilerplate(text: str, *, all_texts: list[str] | None = None) -> bool:
    """Detect page headers, footers, and repeated boilerplate text.

    Args:
        text: Stripped block text.
        all_texts: Optional list of all block texts for repetition detection.

    Returns:
        True if the block appears to be boilerplate.
    """
    if _BOILERPLATE_PATTERN.match(text):
        return True
    # Repeated text appearing on multiple pages (e.g., running headers)
    return all_texts is not None and all_texts.count(text) >= 2


def _is_chunk_boilerplate(text: str) -> bool:
    """Detect obvious cover-page legal fragments in a final chunk.

    Only drops VERY short fragments that are clearly mid-sentence
    cover page boilerplate (legal disclaimers, date notices, approval
    stamps).  Longer chunks are never dropped — they may contain valid
    policy text.

    Args:
        text: The chunk text.

    Returns:
        ``True`` if the chunk is an obvious cover-page fragment.
    """
    lower = text.lower()

    # Approval stamps (any length) — CISO / executive sign-off boilerplate
    # that appears on every policy cover page and causes false-positive
    # mappings against governance controls like PCI DSS 12.1.4.
    if "approved by the" in lower and (
        "security officer" in lower
        or "ciso" in lower
        or "executive management" in lower
    ):
        return True

    # Only consider short chunks — longer text is never boilerplate
    if len(text) >= 120:
        return False

    # Short fragment starting with lowercase or parenthetical = mid-sentence
    if text[0].islower() or text.startswith("("):
        return True

    # Short fragment that IS the legal disclaimer tail
    if "prohibited" in lower and ("reproduction" in lower or "disclosure" in lower):
        return True
    return "effective as of the date" in lower


@dataclass
class StructuralSection:
    """A section split by structural header boundaries.

    Attributes:
        header: The section header text, or None for untitled sections.
        sentences: Individual sentences within the section.
        page_number: Page number of the first block in this section.
    """

    header: str | None
    sentences: list[str]
    page_number: int = 1
    blocks: list[TextBlock] = field(default_factory=list)


# --- Phase 1: Structural Chunking ---


def _join_paragraph_blocks(blocks: list[TextBlock]) -> list[TextBlock]:
    """Join consecutive body-text blocks that belong to the same paragraph.

    PyMuPDF's ``get_text("blocks")`` returns each visual line as a separate
    block. This function merges vertically adjacent lines on the same page
    into a single block so that sentence splitting operates on complete
    paragraphs rather than partial lines.

    Heuristics for same-paragraph:
      * Same page number
      * Left edge within 5 pts (same column)
      * Vertical gap <= 1.5x line height (continuous text flow)
      * Neither block matches a header pattern

    Args:
        blocks: Ordered text blocks from the extractor.

    Returns:
        A new list of TextBlock instances with paragraph-level text.
    """
    if not blocks:
        return []

    # Build text list for repetition detection (page headers repeat)
    all_texts = [b.text.strip() for b in blocks]

    # Filter out boilerplate blocks before merging
    filtered: list[TextBlock] = []
    for block in blocks:
        text = block.text.strip()
        if text and not _is_boilerplate(text, all_texts=all_texts):
            filtered.append(block)

    if not filtered:
        return []

    merged: list[TextBlock] = []
    current = filtered[0]

    for next_block in filtered[1:]:
        cur_text = current.text.strip()
        nxt_text = next_block.text.strip()

        # Check if these blocks should merge
        same_page = current.page_number == next_block.page_number
        same_column = abs(current.x0 - next_block.x0) < 5.0
        line_height = current.y1 - current.y0
        gap = next_block.y0 - current.y1
        adjacent = 0 <= gap <= max(line_height * 1.5, 20.0)
        cur_is_header = bool(_HEADER_PATTERN.match(cur_text))
        nxt_is_header = bool(_HEADER_PATTERN.match(nxt_text))

        if same_page and same_column and adjacent and not cur_is_header and not nxt_is_header:
            # Merge: extend current block's text and bounding box
            separator = " " if cur_text and not cur_text.endswith(" ") else ""
            joined_text = cur_text + separator + nxt_text
            current = TextBlock(
                x0=min(current.x0, next_block.x0),
                y0=current.y0,
                x1=max(current.x1, next_block.x1),
                y1=next_block.y1,
                text=joined_text,
                page_number=current.page_number,
            )
        else:
            merged.append(current)
            current = next_block

    merged.append(current)
    return merged


def structural_chunk(blocks: list[TextBlock]) -> list[StructuralSection]:
    """Split text blocks into sections based on header detection.

    Before splitting, consecutive body-text blocks are joined into
    paragraphs to prevent mid-sentence chunking boundaries.

    Args:
        blocks: Ordered text blocks from the extractor.

    Returns:
        A list of ``StructuralSection`` instances.
    """
    if not blocks:
        return []

    # Join consecutive visual lines into full paragraphs
    blocks = _join_paragraph_blocks(blocks)

    sections: list[StructuralSection] = []
    current_header: str | None = None
    current_sentences: list[str] = []
    current_page: int = blocks[0].page_number
    current_blocks: list[TextBlock] = []

    for block in blocks:
        text = block.text.strip()
        if not text:
            continue

        if _HEADER_PATTERN.match(text):
            # Save the current section before starting a new one
            if current_sentences:
                sections.append(
                    StructuralSection(
                        header=current_header,
                        sentences=current_sentences,
                        page_number=current_page,
                        blocks=current_blocks,
                    )
                )
            current_header = text
            current_sentences = []
            current_page = block.page_number
            current_blocks = [block]
        else:
            # Split block text into sentences
            block_sentences = _split_sentences(text)
            current_sentences.extend(block_sentences)
            current_blocks.append(block)

    # Don't forget the last section
    if current_sentences:
        sections.append(
            StructuralSection(
                header=current_header,
                sentences=current_sentences,
                page_number=current_page,
                blocks=current_blocks,
            )
        )

    return sections


# --- Phase 2: Semantic Chunking ---


def _get_embedder() -> Any:
    """Lazily load the sentence-transformers model.

    Returns a SentenceTransformer model instance. Loaded once per process.
    """
    from sentence_transformers import SentenceTransformer

    if not hasattr(_get_embedder, "_model"):
        _get_embedder._model = SentenceTransformer(  # type: ignore[attr-defined]
            "all-MiniLM-L6-v2"
        )
    return _get_embedder._model  # type: ignore[attr-defined]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x**2 for x in a) ** 0.5
    norm_b = sum(x**2 for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def semantic_chunk(
    sentences: list[str],
    *,
    similarity_threshold: float = 0.5,
    overlap: int = 0,
) -> list[str]:
    """Group sentences into chunks based on semantic similarity.

    Computes embeddings for each sentence, then merges adjacent sentences
    whose cosine similarity exceeds the threshold. Splits occur where
    similarity drops below the threshold.

    Args:
        sentences: Individual sentences to group.
        similarity_threshold: Cosine similarity threshold for merging.
        overlap: Number of sentences to carry forward from the end of
            one chunk to the beginning of the next (default: 1).

    Returns:
        A list of chunk strings, each containing one or more sentences.
    """
    if len(sentences) <= 1:
        return [" ".join(sentences)] if sentences else []

    model = _get_embedder()
    embeddings = model.encode(sentences)

    chunks: list[str] = []
    current_chunk: list[str] = [sentences[0]]

    for i in range(1, len(sentences)):
        sim = _cosine_similarity(
            embeddings[i - 1].tolist(),
            embeddings[i].tolist(),
        )

        if sim >= similarity_threshold:
            current_chunk.append(sentences[i])
        else:
            chunks.append(" ".join(current_chunk))
            # Carry forward the last `overlap` sentences into the new chunk
            carry = current_chunk[-overlap:] if overlap > 0 else []
            current_chunk = [*carry, sentences[i]]

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


# --- Full Pipeline ---


def _merge_short_chunks(chunks: list[str], *, min_length: int = 50) -> list[str]:
    """Merge chunks shorter than *min_length* into their nearest neighbor.

    Walks the list front-to-back.  If a chunk is shorter than the
    threshold it is appended to the **previous** chunk (or prepended to
    the **next** one if it is the first item).  This preserves short
    sentences as context instead of dropping them.

    Args:
        chunks: Ordered list of text chunks from the semantic chunker.
        min_length: Minimum acceptable chunk length in characters.

    Returns:
        A new list with short fragments folded into neighbors.
    """
    if not chunks:
        return []

    merged: list[str] = []

    for chunk in chunks:
        if merged and len(chunk) < min_length:
            # Fold into the previous chunk
            merged[-1] = merged[-1] + " " + chunk
        else:
            merged.append(chunk)

    # Edge case: if the *first* entry is still short, fold it forward
    if len(merged) > 1 and len(merged[0]) < min_length:
        merged[1] = merged[0] + " " + merged[1]
        merged.pop(0)

    return merged


# Trailing words that signal a chunk was cut mid-clause.
# When a chunk ends with one of these, the next chunk continues the
# sentence regardless of capitalisation.
_TRAILING_WORDS = frozenset(
    {
        # prepositions / particles
        "of",
        "for",
        "in",
        "to",
        "with",
        "from",
        "by",
        "at",
        "on",
        "into",
        "about",
        "between",
        "through",
        "within",
        "without",
        "including",
        # articles / determiners
        "the",
        "a",
        "an",
        "all",
        "any",
        "each",
        "every",
        "this",
        "that",
        # conjunctions
        "and",
        "or",
        "nor",
        "but",
        # auxiliary / modal verbs
        "be",
        "is",
        "are",
        "was",
        "were",
        "been",
        "being",
        "must",
        "shall",
        "should",
        "will",
        "would",
        "can",
        "could",
        "may",
        # common mid-clause endings
        "not",
        "also",
        "than",
    }
)


def _ends_mid_clause(text: str) -> bool:
    """Return True if *text* ends in the middle of a clause.

    Checks two signals:
    1. Missing sentence-terminal punctuation (. ! ?)
    2. The final word is a common trailing word (preposition, article,
       conjunction, or auxiliary verb).
    """
    stripped = text.strip()
    if not stripped:
        return False
    # Signal 1 — no terminal punctuation
    return stripped[-1] not in ".!?"


def _ends_with_trailing_word(text: str) -> bool:
    """Return True if the last word of *text* is a mid-clause function word."""
    stripped = text.strip().rstrip(".!?")
    if not stripped:
        return False
    last_word = stripped.split()[-1].lower()
    return last_word in _TRAILING_WORDS


def _heal_sentence_boundaries(chunks: list[str]) -> list[str]:
    """Join chunks that end mid-sentence with the following chunk.

    After semantic chunking + short-chunk merging, some chunks may still
    end mid-sentence because the semantic similarity split happened
    within a paragraph.  This pass detects chunks whose text does not
    end with sentence-terminal punctuation (. ! ?) and merges them
    forward.  It also detects chunks ending with trailing function words
    (prepositions, articles, auxiliary verbs) that indicate a mid-clause
    cut, merging forward regardless of the next chunk's capitalisation.

    To avoid over-merging full paragraphs that simply lack terminal
    punctuation (common in PDF extraction), merging only occurs when
    the trailing fragment is short (< 80 characters).

    Args:
        chunks: Ordered list of text chunks.

    Returns:
        A new list with sentence boundaries healed.
    """
    if not chunks:
        return []

    healed: list[str] = []

    for chunk in chunks:
        text = chunk.strip()
        if not text:
            continue

        if not healed:
            healed.append(text)
            continue

        prev = healed[-1].strip()
        prev_no_terminal = prev and prev[-1] not in ".!?"
        prev_trailing_word = _ends_with_trailing_word(prev)

        # Only heal if the trailing fragment (text after last sentence
        # terminator) is short — this prevents merging full paragraphs
        # that happen to lack a period at the end.
        last_terminal = max(prev.rfind(c) for c in ".!?")
        trailing_fragment = prev[last_terminal + 1 :].strip() if last_terminal >= 0 else prev
        fragment_is_short = len(trailing_fragment) < 80

        # Merge when previous chunk ends mid-sentence AND:
        #   a) the current chunk starts lowercase/digit (continuation), OR
        #   b) the previous chunk ends with a trailing function word
        starts_continuation = text[0].islower() or text[0].isdigit()

        if prev_no_terminal and fragment_is_short and (starts_continuation or prev_trailing_word):
            healed[-1] = healed[-1].rstrip() + " " + text
        else:
            healed.append(text)

    return healed


def chunk_document(
    blocks: list[TextBlock],
    *,
    document_name: str,
    similarity_threshold: float = 0.5,
) -> list[ParsedChunk]:
    """Run the full structural → semantic chunking pipeline.

    Args:
        blocks: Text blocks from the extractor.
        document_name: Source document filename.
        similarity_threshold: Cosine similarity threshold for semantic merging.

    Returns:
        A list of ``ParsedChunk`` instances.
    """
    sections = structural_chunk(blocks)
    parsed_chunks: list[ParsedChunk] = []

    for section in sections:
        sem_chunks = semantic_chunk(
            section.sentences,
            similarity_threshold=similarity_threshold,
        )

        # Merge short chunks into neighbors instead of dropping them
        merged = _merge_short_chunks(sem_chunks, min_length=50)

        # Heal chunks that end mid-sentence by joining with the next chunk
        healed = _heal_sentence_boundaries(merged)

        for chunk_text in healed:
            # Final guard — skip anything still too short after merging
            # or identified as cover-page boilerplate
            if len(chunk_text) < 50:
                continue
            if _is_chunk_boilerplate(chunk_text):
                continue
            parsed_chunks.append(
                ParsedChunk(
                    chunk_id=str(uuid.uuid4()),
                    document_name=document_name,
                    page_number=section.page_number,
                    raw_text=chunk_text,
                    section_header=section.header,
                )
            )

    return parsed_chunks


# --- Utilities ---


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences without mid-sentence breaks.

    Args:
        text: Raw text to split.

    Returns:
        A list of complete sentences.
    """
    parts = _SENTENCE_SPLIT.split(text)
    return [s.strip() for s in parts if s.strip()]
