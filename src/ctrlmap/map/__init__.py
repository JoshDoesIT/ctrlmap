"""ctrlmap.map: RAG retrieval logic, similarity scoring, and harmonization.

Public API:
    map_controls: Map security controls to supporting chunks via vector search.
    enrich_with_rationale: LLM enrichment pipeline for mapping results.
    cluster_controls: Cluster semantically similar controls for harmonization.
    classify_meta_controls: Identify governance/documentation meta-requirements.
    resolve_meta_requirements: Infer meta-requirement compliance from siblings.
"""

from ctrlmap.map.cluster import cluster_controls
from ctrlmap.map.enrichment import enrich_with_rationale
from ctrlmap.map.mapper import map_controls
from ctrlmap.map.meta_requirements import classify_meta_controls, resolve_meta_requirements

__all__ = [
    "classify_meta_controls",
    "cluster_controls",
    "enrich_with_rationale",
    "map_controls",
    "resolve_meta_requirements",
]
