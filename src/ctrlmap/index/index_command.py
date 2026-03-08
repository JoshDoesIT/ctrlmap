"""Index subcommand for the ctrlmap CLI.

Ingests parsed JSON chunks and OSCAL framework controls, embeds them
using Sentence-Transformers, and populates the local ChromaDB vector
database.

Usage::

    ctrlmap index --chunks <path> --framework <path> [--db-path <path>] [--embedding-model <string>]

Ref: GitHub Issue #15.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from ctrlmap._console import console
from ctrlmap._defaults import DEFAULT_EMBEDDING_MODEL
from ctrlmap.index.embedder import Embedder
from ctrlmap.index.vector_store import VectorStore
from ctrlmap.models.oscal import parse_oscal_catalog
from ctrlmap.models.schemas import ParsedChunk


def index(
    chunks_path: Path = typer.Option(  # noqa: B008
        ...,
        "--chunks",
        help="Path to a .jsonl file of parsed chunks.",
        exists=True,
        readable=True,
        resolve_path=True,
    ),
    framework_path: Path = typer.Option(  # noqa: B008
        ...,
        "--framework",
        help="Path to an OSCAL JSON framework file.",
        exists=True,
        readable=True,
        resolve_path=True,
    ),
    db_path: Path = typer.Option(  # noqa: B008
        Path("./ctrlmap_db"),
        "--db-path",
        help="ChromaDB persistence directory.",
        resolve_path=True,
    ),
    embedding_model: str = typer.Option(
        DEFAULT_EMBEDDING_MODEL,
        "--embedding-model",
        help="Sentence-Transformers model name.",
    ),
) -> None:
    """Embed parsed chunks and framework controls into the local vector database."""
    console.print("[bold blue]Indexing:[/] Initializing embedding model...")
    embedder = Embedder(model_name=embedding_model)
    store = VectorStore(db_path=db_path)

    # Phase 1: Load and embed parsed chunks
    console.print(f"[bold blue]Loading chunks:[/] {chunks_path.name}")
    chunks = _load_chunks(chunks_path)

    console.print(f"[dim]Embedding {len(chunks)} chunks...[/]")
    texts = [c.raw_text for c in chunks]
    embeddings = embedder.embed_batch(texts)

    embedded_chunks = []
    for chunk, emb in zip(chunks, embeddings, strict=True):
        embedded_chunks.append(chunk.model_copy(update={"embedding": emb}))

    chunk_count = store.index_chunks("chunks", embedded_chunks)
    console.print(f"[green]Indexed {chunk_count} chunks.[/]")

    # Phase 2: Load and embed framework controls
    console.print(f"[bold blue]Loading framework:[/] {framework_path.name}")
    controls = parse_oscal_catalog(framework_path)

    console.print(f"[dim]Embedding {len(controls)} controls...[/]")
    control_texts = [f"{c.control_id}: {c.title}. {c.description}" for c in controls]
    control_embeddings = embedder.embed_batch(control_texts)

    control_chunks = []
    for ctrl, emb in zip(controls, control_embeddings, strict=True):
        control_chunks.append(
            ParsedChunk(
                chunk_id=f"ctrl-{ctrl.control_id}",
                document_name=f"framework:{ctrl.framework}",
                page_number=1,
                raw_text=f"{ctrl.control_id}: {ctrl.title}. {ctrl.description}",
                section_header=ctrl.title,
                embedding=emb,
            )
        )

    control_count = store.index_chunks("controls", control_chunks)
    console.print(f"[green]Indexed {control_count} controls.[/]")

    console.print(
        f"[bold green]Done:[/] Embedded {chunk_count} chunks + {control_count} controls → {db_path}"
    )


def _load_chunks(path: Path) -> list[ParsedChunk]:
    """Load ParsedChunk objects from a .jsonl file.

    Args:
        path: Path to the .jsonl file.

    Returns:
        A list of ParsedChunk instances.
    """
    chunks: list[ParsedChunk] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                chunks.append(ParsedChunk.model_validate(data))
    return chunks
