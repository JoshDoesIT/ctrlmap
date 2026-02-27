"""Vector-based clustering for control harmonization.

Groups semantically overlapping SecurityControl objects using embedding
cosine similarity, producing deduplicated CommonControl objects with
source references linking back to the originals.

Uses single-linkage clustering: two controls join the same cluster if
*either* is similar enough to *any* existing member of the cluster.
This captures transitive overlaps (A~B and B~C ⇒ A, B, C clustered).

Ref: GitHub Issue #17.
"""

from __future__ import annotations

import uuid

import numpy as np

from ctrlmap.index.embedder import Embedder
from ctrlmap.models.schemas import CommonControl, SecurityControl


def cluster_controls(
    *,
    controls: list[SecurityControl],
    similarity_threshold: float = 0.85,
    embedder: Embedder | None = None,
) -> list[CommonControl]:
    """Cluster semantically overlapping controls into CommonControl groups.

    Uses cosine similarity of control embeddings to identify overlapping
    requirements across frameworks, producing a deduplicated set of
    ``CommonControl`` objects.

    Args:
        controls: List of SecurityControl objects to cluster.
        similarity_threshold: Minimum cosine similarity to merge controls
            into the same cluster (default: 0.85). Higher = stricter.
        embedder: Optional Embedder instance. Creates a default one if None.

    Returns:
        A list of ``CommonControl`` objects, each with ``source_references``
        linking back to the original control IDs.
    """
    if not controls:
        return []

    if embedder is None:
        embedder = Embedder()

    # Embed all controls
    texts = [f"{c.control_id}: {c.title}. {c.description}" for c in controls]
    embeddings = embedder.embed_batch(texts)
    vectors = np.array(embeddings)

    # Normalize for cosine similarity
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = vectors / norms

    # Compute full pairwise similarity matrix
    sim_matrix = normalized @ normalized.T

    # Single-linkage clustering via Union-Find
    parent = list(range(len(controls)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(controls)):
        for j in range(i + 1, len(controls)):
            if sim_matrix[i, j] >= similarity_threshold:
                union(i, j)

    # Group controls by their cluster root
    cluster_map: dict[int, list[int]] = {}
    for i in range(len(controls)):
        root = find(i)
        cluster_map.setdefault(root, []).append(i)

    # Build CommonControl objects
    result: list[CommonControl] = []
    for cluster_indices in cluster_map.values():
        cluster_ctrls = [controls[i] for i in cluster_indices]
        source_refs = [c.control_id for c in cluster_ctrls]

        if len(cluster_ctrls) == 1:
            theme = cluster_ctrls[0].title
            unified_desc = cluster_ctrls[0].description
        else:
            theme = cluster_ctrls[0].title
            descriptions = [c.description for c in cluster_ctrls]
            unified_desc = " ".join(descriptions)

        result.append(
            CommonControl(
                common_id=f"CC-{uuid.uuid4().hex[:8]}",
                theme=theme,
                unified_description=unified_desc,
                source_references=source_refs,
            )
        )

    return result
