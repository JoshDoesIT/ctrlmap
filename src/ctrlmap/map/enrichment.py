"""LLM enrichment pipeline for compliance mapping results.

Extracted from ``map_command.py`` to isolate the 5-step LLM pipeline
from CLI wiring, enabling independent testing and reuse.

Steps:
    1. Verify chunk relevance (filter false positives).
    2. Generate per-chunk compliance rationales and select the best.
    3. Classify which controls are meta-requirements.
    4. Generate gap rationales for unmapped controls.
    5. Resolve meta-requirements via sibling aggregation.
"""

from __future__ import annotations

from ctrlmap._console import console
from ctrlmap.llm.structured_output import (
    generate_gap_rationale,
    generate_rationale,
    select_best_rationale,
)
from ctrlmap.map.meta_requirements import classify_meta_controls, resolve_meta_requirements
from ctrlmap.models.schemas import MappedResult, MappingRationale, ParsedChunk


def enrich_with_rationale(
    results: list[MappedResult],
    *,
    llm_model: str,
) -> list[MappedResult]:
    """Enrich mapping results with LLM-generated rationales.

    Runs a five-step pipeline:
    1. Verify chunk relevance (filter false-positive retrievals).
    2. Generate per-chunk compliance rationales and select the best.
    3. Classify which controls are meta-requirements.
    4. Generate gap rationales for unmapped controls.
    5. Resolve meta-requirements via sibling aggregation.

    Args:
        results: List of MappedResult objects from vector similarity.
        llm_model: Ollama model name for inference.

    Returns:
        The enriched list of MappedResult objects.
    """
    from ctrlmap.llm.client import OllamaClient

    llm_client = OllamaClient(model=llm_model)

    # Step 1: LLM relevance verification
    console.print("[bold blue]LLM:[/] Verifying evidence relevance...")
    for result in results:
        if not result.supporting_chunks:
            continue
        ctrl = result.control
        control_text = ctrl.as_prompt_text()
        verified: list[ParsedChunk] = []
        for chunk in result.supporting_chunks:
            is_relevant = llm_client.verify_chunk_relevance(
                control_text=control_text,
                chunk_text=chunk.raw_text,
                requirement_family=ctrl.requirement_family,
            )
            if is_relevant:
                verified.append(chunk)
            else:
                console.print(
                    f"[yellow]  {ctrl.control_id}: dropped "
                    f'irrelevant chunk "{chunk.raw_text[:50]}…"[/]'
                )
        result.supporting_chunks = verified

    # Step 2: Score each chunk individually, keep the best rationale
    console.print("[bold blue]LLM:[/] Generating per-chunk rationales...")
    for result in results:
        if not result.supporting_chunks:
            continue
        control_text = result.control.as_prompt_text()
        chunk_rationales: list[MappingRationale] = []
        for chunk in result.supporting_chunks:
            rat = generate_rationale(
                control_text=control_text,
                chunk_text=chunk.raw_text,
                model=llm_model,
            )
            if isinstance(rat, MappingRationale):
                chunk_rationales.append(rat)
        best = select_best_rationale(chunk_rationales)
        if best is not None:
            result.rationale = best

    # Step 3: Classify which unresolved controls are meta-requirements
    console.print("[bold blue]LLM:[/] Classifying meta-requirements...")
    meta_ids = classify_meta_controls(results=results, client=llm_client)

    # Step 4: Generate gap rationale for unmapped controls
    console.print("[bold blue]LLM:[/] Generating gap rationales...")
    for result in results:
        if result.rationale is None and not result.supporting_chunks:
            result.rationale = generate_gap_rationale(
                control_text=result.control.as_prompt_text(),
                model=llm_model,
                client=llm_client,
            )

    # Step 5: Resolve meta-requirements via sibling aggregation
    console.print("[bold blue]LLM:[/] Resolving meta-requirements...")
    return resolve_meta_requirements(results=results, meta_control_ids=meta_ids)
