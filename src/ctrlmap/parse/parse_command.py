"""Parse subcommand for the ctrlmap CLI.

Wires the extraction → chunking pipeline and outputs
a `.jsonl` file of serialized ``ParsedChunk`` objects.

Supports three strategies:
  - ``semantic`` (default): Heuristic structural + semantic similarity chunking.
  - ``fixed``: Simple character-based splitting.
  - ``llm``: LLM-based control extraction via local Ollama.

Usage::

    ctrlmap parse --input <path> --output <path> [--strategy semantic|fixed|llm]

Ref: GitHub Issue #9.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import typer
from rich.console import Console

from ctrlmap.models.schemas import ParsedChunk
from ctrlmap.parse.chunker import chunk_document
from ctrlmap.parse.extractor import TextBlock, extract_page_texts, extract_text_blocks
from ctrlmap.parse.heuristics import ElementRole, classify_block, order_blocks_by_columns

console = Console()


class Strategy(StrEnum):
    """Chunking strategy."""

    SEMANTIC = "semantic"
    FIXED = "fixed"
    LLM = "llm"


def parse(
    input_path: Path = typer.Option(  # noqa: B008
        ...,
        "--input",
        "-i",
        help="Path to the PDF file to parse.",
        exists=True,
        readable=True,
        resolve_path=True,
    ),
    output_path: Path = typer.Option(  # noqa: B008
        ...,
        "--output",
        "-o",
        help="Path for the .jsonl output file.",
        resolve_path=True,
    ),
    strategy: Strategy = typer.Option(  # noqa: B008
        Strategy.SEMANTIC,
        "--strategy",
        "-s",
        help="Chunking strategy: 'semantic' (default), 'fixed', or 'llm'.",
    ),
    chunk_size: int = typer.Option(
        512,
        "--chunk-size",
        "-c",
        help="Max chunk size in characters (only used with 'fixed' strategy).",
        min=50,
    ),
    model: str = typer.Option(
        "llama3",
        "--model",
        "-m",
        help="Ollama model name (only used with 'llm' strategy).",
    ),
) -> None:
    """Extract and chunk a PDF document into structured ParsedChunk JSONL."""
    console.print(f"[bold blue]Parsing:[/] {input_path.name}")

    if strategy == Strategy.LLM:
        chunks = _llm_extract(input_path, model=model)
    else:
        # Heuristic path: extract blocks → classify → chunk
        blocks = extract_text_blocks(input_path)

        if not blocks:
            console.print("[yellow]No text blocks found in the PDF.[/]")
            raise typer.Exit(code=0)

        # Filter out headers/footers from the primary text
        body_blocks = [b for b in blocks if classify_block(b) == ElementRole.BODY]

        # Reorder for column-aware reading
        ordered_blocks = order_blocks_by_columns(body_blocks)

        if strategy == Strategy.SEMANTIC:
            chunks = chunk_document(
                ordered_blocks,
                document_name=input_path.name,
            )
        else:
            chunks = _fixed_chunk(ordered_blocks, input_path.name, chunk_size)

    # Write JSONL output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        for chunk in chunks:
            f.write(chunk.model_dump_json() + "\n")

    console.print(f"[bold green]Done:[/] {len(chunks)} chunks → {output_path}")


def _fixed_chunk(
    blocks: list[TextBlock],
    document_name: str,
    chunk_size: int,
) -> list[ParsedChunk]:
    """Simple fixed-size character-based chunking.

    Args:
        blocks: Ordered text blocks.
        document_name: Source file name.
        chunk_size: Max characters per chunk.

    Returns:
        A list of ``ParsedChunk`` instances.
    """
    import uuid

    all_text = " ".join(b.text for b in blocks)
    page_number = blocks[0].page_number if blocks else 1
    chunks: list[ParsedChunk] = []

    for i in range(0, len(all_text), chunk_size):
        segment = all_text[i : i + chunk_size].strip()
        if len(segment) >= 10:
            chunks.append(
                ParsedChunk(
                    chunk_id=str(uuid.uuid4()),
                    document_name=document_name,
                    page_number=page_number,
                    raw_text=segment,
                )
            )

    return chunks


def _llm_extract(input_path: Path, *, model: str) -> list[ParsedChunk]:
    """Extract controls using LLM-based analysis via Ollama.

    Args:
        input_path: Path to the PDF file.
        model: Ollama model name.

    Returns:
        A list of ``ParsedChunk`` instances.
    """
    from ctrlmap.parse.llm_chunker import extract_controls_with_llm

    pages = extract_page_texts(input_path)
    if not pages:
        console.print("[yellow]No text found in the PDF.[/]")
        return []

    console.print(
        f"[dim]LLM: Extracting controls from {len(pages)} pages with model '{model}'...[/]"
    )
    return extract_controls_with_llm(
        pages,
        document_name=input_path.name,
        model=model,
    )
