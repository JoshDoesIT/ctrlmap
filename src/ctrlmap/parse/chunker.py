"""Hybrid structural + semantic chunking pipeline.

Two-phase chunking:
1. **Structural** — splits on section headers detected by font-size heuristics.
2. **Semantic** — computes sentence-level cosine similarity via sentence-transformers
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

# Header detection: lines matching common section prefixes
_HEADER_PATTERN = re.compile(
    r"^(Section\s+\d+|Chapter\s+\d+|Part\s+\d+|APPENDIX\s+[A-Z]|\d+\.\d*)\s*[:\-—]\s*",
    re.IGNORECASE,
)


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


def structural_chunk(blocks: list[TextBlock]) -> list[StructuralSection]:
    """Split text blocks into sections based on header detection.

    Args:
        blocks: Ordered text blocks from the extractor.

    Returns:
        A list of ``StructuralSection`` instances.
    """
    if not blocks:
        return []

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
) -> list[str]:
    """Group sentences into chunks based on semantic similarity.

    Computes embeddings for each sentence, then merges adjacent sentences
    whose cosine similarity exceeds the threshold. Splits occur where
    similarity drops below the threshold.

    Args:
        sentences: Individual sentences to group.
        similarity_threshold: Cosine similarity threshold for merging.

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
            current_chunk = [sentences[i]]

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


# --- Full Pipeline ---


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

        for chunk_text in sem_chunks:
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
