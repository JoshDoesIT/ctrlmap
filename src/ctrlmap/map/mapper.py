"""Core mapping algorithm: control → vector DB → ranked chunks.

Iterates through SecurityControl objects, queries the vector database
for top-K matching policy chunks, and returns MappedResult objects
ranked by cosine similarity.

Ref: GitHub Issue #16.
"""

from __future__ import annotations

from ctrlmap.index.embedder import Embedder
from ctrlmap.index.query import query
from ctrlmap.index.vector_store import VectorStore
from ctrlmap.models.schemas import MappedResult, ParsedChunk, SecurityControl

# Static keyword map for query expansion.
# Maps abstract GRC concepts to domain-specific terms that improve retrieval.
_EXPANSION_MAP: dict[str, str] = {
    "information at rest": (
        "encryption, AES, TDE, full-disk encryption, data-at-rest, "
        "disk encryption, database encryption, storage encryption, "
        "encrypted at rest, data protection"
    ),
    "information in transit": "TLS, SSL, HTTPS, transport encryption, VPN, IPsec",
    "cryptographic protection": "encryption, key management, PKI, certificate, AES",
    "audit events": "logging, SIEM, log retention, audit trail, event monitoring",
    "flaw remediation": "patching, vulnerability management, CVE, security update",
    "access enforcement": "RBAC, ACL, permissions, authorization, least privilege",
    "incident response": "breach notification, forensics, incident handling, CSIRT",
    "risk assessment": "risk analysis, threat modeling, vulnerability assessment",
    "system monitoring": "IDS, IPS, intrusion detection, network monitoring, SIEM",
    "boundary protection": "firewall, DMZ, network segmentation, NSC, perimeter",
    "information flow": (
        "data flow, network flow, ACL, firewall rules, flow control, "
        "flow enforcement, data transfer, cross-domain"
    ),
    "physical access": (
        "badge, biometric, door lock, visitor escort, card reader, "
        "facility access, building entry, physical security"
    ),
    "physical access control": (
        "badge reader, security camera, visitor sign-in, escort, "
        "two-factor entry, biometric scanner, server room access, "
        "entry point, building access"
    ),
    "policy and procedures": (
        "policy document, security procedures, disseminate, document, "
        "develop policy, maintain policy, policy review"
    ),
    "maintenance": (
        "maintenance activities, scheduled maintenance, authorized personnel, "
        "maintenance tools, maintenance records, preventive maintenance, "
        "system maintenance, hardware maintenance"
    ),
    "system and services acquisition": (
        "acquisition contracts, vendor compliance, security requirements, "
        "procurement, supply chain, third-party assessment"
    ),
    "system and communications protection": (
        "network security architecture, secure communication, boundary protection, "
        "TLS, communication protocols, network security, data in transit"
    ),
    "flow enforcement": (
        "network segmentation, firewall rules, information flow, "
        "data flow control, transfer gateway, traffic inspection, "
        "cross-domain, security domain"
    ),
}


def _expand_query(query_text: str) -> str:
    """Expand abstract control descriptions with domain-specific terms.

    Scans the query text for abstract GRC concepts from ``_EXPANSION_MAP``
    and appends relevant domain synonyms to improve vector search recall.

    Args:
        query_text: The original query string.

    Returns:
        The query string, possibly augmented with expansion terms.
    """
    lower = query_text.lower()
    expansions: list[str] = []

    for concept, terms in _EXPANSION_MAP.items():
        if concept in lower:
            expansions.append(terms)

    if expansions:
        return f"{query_text} [{'; '.join(expansions)}]"
    return query_text


def map_controls(
    *,
    controls: list[SecurityControl],
    store: VectorStore,
    collection_name: str,
    top_k: int = 10,
    min_score: float = 0.35,
    embedder: Embedder | None = None,
) -> list[MappedResult]:
    """Map security controls to supporting policy chunks via vector similarity.

    For each control, queries the vector DB for the top-K most similar
    policy chunks and filters out results below ``min_score`` to prevent
    weak/irrelevant matches from appearing as false positives.

    Args:
        controls: List of SecurityControl objects to map.
        store: The VectorStore instance containing indexed policy chunks.
        collection_name: Name of the ChromaDB collection to search.
        top_k: Maximum number of supporting chunks per control (default: 10).
        min_score: Minimum similarity score to include a chunk (default: 0.35).
            Chunks below this threshold are dropped to avoid false matches.
        embedder: Optional Embedder instance. Creates a default one if None.

    Returns:
        A list of ``MappedResult`` objects, one per input control.
    """
    if embedder is None:
        embedder = Embedder()

    results: list[MappedResult] = []

    for control in controls:
        query_text = f"{control.control_id}: {control.title}. {control.description}"
        # Include the requirement family context to anchor embeddings
        # to the correct domain (e.g. "Develop and Maintain Secure
        # Systems and Software") and reduce cross-family false matches.
        if control.requirement_family:
            query_text = f"[{control.requirement_family}] {query_text}"
        query_text = _expand_query(query_text)

        query_results = query(
            store=store,
            collection_name=collection_name,
            query_text=query_text,
            top_k=top_k,
            embedder=embedder,
        )

        supporting_chunks: list[ParsedChunk] = []
        for qr in query_results:
            if qr.score < min_score:
                continue
            supporting_chunks.append(
                ParsedChunk(
                    chunk_id=qr.chunk_id,
                    document_name=qr.metadata.get("document_name", ""),
                    page_number=int(qr.metadata.get("page_number", 1)),
                    raw_text=qr.raw_text,
                    section_header=qr.metadata.get("section_header") or None,
                )
            )

        results.append(
            MappedResult(
                control=control,
                supporting_chunks=supporting_chunks,
            )
        )

    return results
