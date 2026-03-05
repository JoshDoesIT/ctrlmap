"""ChromaDB vector store for local disk persistence.

Wraps ChromaDB's ``PersistentClient`` to provide a local embedded
vector database that persists across CLI invocations without requiring
a background daemon.

Ref: GitHub Issues #12, #13, #14.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import chromadb

from ctrlmap.models.schemas import ParsedChunk

if TYPE_CHECKING:
    from chromadb.api.models.Collection import Collection


class VectorStore:
    """Local ChromaDB vector store for embedding persistence and search.

    Args:
        db_path: Directory for ChromaDB local file storage.

    Raises:
        OSError: If the database path cannot be created or accessed.
    """

    def __init__(self, db_path: Path) -> None:
        try:
            db_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            msg = f"Cannot create database directory: {db_path}"
            raise OSError(msg) from exc

        self._client = chromadb.PersistentClient(path=str(db_path))
        self._db_path = db_path

    def get_or_create_collection(self, name: str) -> Collection:
        """Get an existing collection or create a new one.

        Args:
            name: The collection name.

        Returns:
            A ChromaDB Collection instance.
        """
        return self._client.get_or_create_collection(name=name)

    def list_collections(self) -> list[str]:
        """List all collection names in the database.

        Returns:
            A list of collection name strings.
        """
        return [c.name for c in self._client.list_collections()]

    def index_chunks(
        self,
        collection_name: str,
        chunks: list[ParsedChunk],
        *,
        on_progress: Any | None = None,
    ) -> int:
        """Index ParsedChunk objects with their embeddings and metadata.

        Uses upsert semantics. Duplicate ``chunk_id`` values are updated
        rather than rejected.

        Args:
            collection_name: Target collection name.
            chunks: ParsedChunk instances with populated ``embedding`` fields.
            on_progress: Optional callback ``(current, total) -> None``.

        Returns:
            The number of chunks indexed.

        Raises:
            ValueError: If any chunk is missing its embedding vector.
        """
        collection = self.get_or_create_collection(collection_name)
        total = len(chunks)

        ids: list[str] = []
        embeddings: list[list[float]] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for i, chunk in enumerate(chunks):
            if chunk.embedding is None:
                msg = f"Chunk {chunk.chunk_id} is missing its embedding vector."
                raise ValueError(msg)

            ids.append(chunk.chunk_id)
            embeddings.append(chunk.embedding)
            documents.append(chunk.raw_text)
            metadatas.append(
                {
                    "document_name": chunk.document_name,
                    "page_number": chunk.page_number,
                    "section_header": chunk.section_header or "",
                    "chunk_id": chunk.chunk_id,
                    "extraction_order": i,
                }
            )

            if on_progress is not None:
                on_progress(i + 1, total)

        if ids:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,  # type: ignore[arg-type]
                documents=documents,
                metadatas=metadatas,  # type: ignore[arg-type]
            )

        return total

    def get_all_chunks(self, collection_name: str) -> list[ParsedChunk]:
        """Retrieve all chunks from a collection.

        Args:
            collection_name: Name of the collection to query.

        Returns:
            A list of ``ParsedChunk`` instances (without embeddings).
        """
        collection = self.get_or_create_collection(collection_name)
        result = collection.get(include=["documents", "metadatas"])

        chunks: list[ParsedChunk] = []
        ids = result.get("ids", [])
        docs = result.get("documents", []) or []
        metas = result.get("metadatas", []) or []

        for i, chunk_id in enumerate(ids):
            doc = docs[i] if i < len(docs) else ""
            meta = metas[i] if i < len(metas) else {}
            chunks.append(
                ParsedChunk(
                    chunk_id=chunk_id,
                    document_name=meta.get("document_name", ""),
                    page_number=int(meta.get("page_number", 1)),
                    raw_text=doc or "",
                    section_header=meta.get("section_header") or None,
                )
            )

        # Sort by extraction_order to preserve original document order
        order_map = {
            ids[i]: metas[i].get("extraction_order", i)
            for i in range(len(ids))
            if i < len(metas)
        }
        chunks.sort(key=lambda c: order_map.get(c.chunk_id, 0))

        return chunks
