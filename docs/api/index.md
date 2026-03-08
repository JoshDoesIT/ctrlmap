# Index

Embedding, vector storage, and ANN query pipeline. This is the second stage of the ctrlmap pipeline — it vectorizes parsed chunks and stores them in a local ChromaDB instance.

## Key Exports

| Symbol | Description |
|--------|-------------|
| `Embedder` | Sentence-Transformers embedding pipeline (`all-MiniLM-L6-v2` by default) |
| `VectorStore` | ChromaDB `PersistentClient` wrapper for chunk storage and retrieval |
| `query(store, collection, query_text, ...)` | ANN similarity search with metadata filtering |
| `QueryResult` | Dataclass containing matched chunks with similarity scores |

## Modules

- **`embedder.py`** — Local text vectorization via Sentence-Transformers
- **`vector_store.py`** — ChromaDB persistent vector database
- **`query.py`** — Vector similarity search with embedding
- **`index_command.py`** — CLI wiring for `ctrlmap index`

## Full API Reference

::: ctrlmap.index
