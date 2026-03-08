"""ctrlmap.index: Embedding, vector storage, and ANN query pipeline.

Modules
-------
embedder
    Sentence-Transformers embedding pipeline for local text vectorization.
vector_store
    ChromaDB-backed persistent vector database for chunk storage.
query
    ANN similarity search with metadata filtering.
index_command
    CLI subcommand wiring for ``ctrlmap index``.
"""

from ctrlmap.index.embedder import Embedder
from ctrlmap.index.query import QueryResult, query, query_by_embedding
from ctrlmap.index.vector_store import VectorStore

__all__ = ["Embedder", "QueryResult", "VectorStore", "query", "query_by_embedding"]
