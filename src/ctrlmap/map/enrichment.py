"""LLM enrichment pipeline for compliance mapping results.

Extracted from ``map_command.py`` to isolate the LLM pipeline from CLI
wiring, enabling independent testing and reuse.

Pipeline (streaming per-control):
    1. Evaluate chunks via **batch evaluation** (one LLM call per control).
    2. Classify meta-requirements (only for unmapped controls).
    3. Generate gap rationales for unmapped controls (async).
    4. Resolve meta-requirements via sibling aggregation.

Performance:
    - **Batch evaluation** sends all chunks for ONE control in a single
      LLM call, reducing ``controls x chunks`` calls to just ``controls``.
    - **Streaming pipeline** processes each control independently instead
      of waiting for all controls to finish each step.
    - **Model tiering** uses the fast 7B model for simple tasks
      (meta-classification, gap rationale) and 14B for accuracy-critical
      compliance evaluation.
    - **LLM cache** eliminates redundant calls during re-runs.
    - **Skip-meta** avoids classifying controls that already have rationales.
    - ``asyncio.gather()`` with bounded semaphore controls concurrency.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ctrlmap.llm.client import OllamaClient

from ctrlmap._console import console
from ctrlmap._defaults import DEFAULT_FAST_MODEL
from ctrlmap.llm.cache import LLMCache
from ctrlmap.llm.structured_output import select_best_rationale
from ctrlmap.map.meta_requirements import resolve_meta_requirements
from ctrlmap.models.schemas import MappedResult, MappingRationale

# Default cache directory (relative to cwd)
_DEFAULT_CACHE_DIR = Path(".ctrlmap_cache")


def enrich_with_rationale(
    results: list[MappedResult],
    *,
    llm_model: str,
    concurrency: int = 4,
    cache_enabled: bool = False,
) -> list[MappedResult]:
    """Enrich mapping results with LLM-generated rationales.

    Runs a four-step streaming pipeline:
    1. Evaluate chunks via batch evaluation (one LLM call per control).
    2. Classify meta-requirements (only unmapped controls).
    3. Generate gap rationales for unmapped controls (async).
    4. Resolve meta-requirements via sibling aggregation.

    Args:
        results: List of MappedResult objects from vector similarity.
        llm_model: Ollama model name for inference.
        concurrency: Maximum concurrent LLM requests (default: 4).
        cache_enabled: Whether to use the LLM response cache.

    Returns:
        The enriched list of MappedResult objects.
    """
    return asyncio.run(
        _enrich_async(
            results,
            llm_model=llm_model,
            concurrency=concurrency,
            cache_enabled=cache_enabled,
        )
    )


async def _enrich_async(
    results: list[MappedResult],
    *,
    llm_model: str,
    concurrency: int,
    cache_enabled: bool,
) -> list[MappedResult]:
    """Async enrichment pipeline — streaming per-control.

    Each control flows through evaluate → classify independently,
    maximizing concurrency utilization.

    Args:
        results: List of MappedResult objects from vector similarity.
        llm_model: Ollama model name for inference.
        concurrency: Maximum concurrent LLM requests.
        cache_enabled: Whether to use the LLM response cache.

    Returns:
        The enriched list of MappedResult objects.
    """
    from ctrlmap.llm.client import OllamaClient

    pipeline_start = time.monotonic()

    cache = LLMCache(cache_dir=_DEFAULT_CACHE_DIR) if cache_enabled else None

    # Primary client (14B) for accuracy-critical compliance evaluation
    llm_client = OllamaClient(model=llm_model, cache=cache)
    # Fast client (7B) for simple tasks: meta-classify + gap rationale
    fast_client = OllamaClient(model=DEFAULT_FAST_MODEL, cache=cache)

    semaphore = asyncio.Semaphore(concurrency)

    total_chunks = sum(len(r.supporting_chunks) for r in results)
    console.print(
        f"[bold blue]LLM:[/] Enriching {len(results)} controls, "
        f"{total_chunks} chunks (concurrency={concurrency})..."
    )

    # Step 1+2: Evaluate chunks (batch) AND classify meta — streamed per-control
    t0 = time.monotonic()
    per_control_tasks = [
        _process_one_control(r, llm_client, fast_client, semaphore) for r in results
    ]
    meta_flags = await asyncio.gather(*per_control_tasks)
    console.print(f"[dim]  Step 1+2 (evaluate + classify): {time.monotonic() - t0:.1f}s[/]")

    meta_ids = {results[i].control.control_id for i, is_meta in enumerate(meta_flags) if is_meta}

    # Step 3: Generate gap rationales (concurrent, fast model)
    gap_count = sum(1 for r in results if r.rationale is None and not r.supporting_chunks)
    if gap_count:
        t1 = time.monotonic()
        console.print(
            f"[bold blue]LLM:[/] Generating {gap_count} gap rationales ({DEFAULT_FAST_MODEL})..."
        )
        await _step_generate_gaps(results, fast_client, semaphore)
        console.print(f"[dim]  Step 3 (gap rationales): {time.monotonic() - t1:.1f}s[/]")

    # Step 4: Resolve meta-requirements via sibling aggregation (no LLM)
    t2 = time.monotonic()
    console.print("[bold blue]LLM:[/] Resolving meta-requirements...")
    resolved = resolve_meta_requirements(results=results, meta_control_ids=meta_ids)
    console.print(f"[dim]  Step 4 (meta-resolution): {time.monotonic() - t2:.1f}s[/]")

    console.print(f"[bold green]Pipeline total:[/] {time.monotonic() - pipeline_start:.1f}s")

    if cache is not None:
        stats = cache.stats()
        console.print(f"[dim]Cache stats: {stats['hits']} hits, {stats['misses']} misses[/]")

    return resolved


async def _process_one_control(
    result: MappedResult,
    client: OllamaClient,
    fast_client: OllamaClient,
    semaphore: asyncio.Semaphore,
) -> bool:
    """Process a single control: batch-evaluate all chunks then classify.

    Uses **batch evaluation** to send all chunks for this control in a
    single LLM call, reducing LLM calls from N to 1 per control.

    Args:
        result: The MappedResult for this control.
        client: The primary OllamaClient (14B for rationale).
        fast_client: The fast OllamaClient (7B for meta-classify).
        semaphore: Concurrency limiter.

    Returns:
        ``True`` if this control is a meta-requirement.
    """
    ctrl = result.control

    # Batch evaluate ALL chunks in one LLM call (14B model)
    if result.supporting_chunks:
        chunk_texts = [chunk.raw_text for chunk in result.supporting_chunks]

        async with semaphore:
            chunk_results = await client.evaluate_chunks_batch_async(
                control_text=ctrl.as_prompt_text(),
                chunk_texts=chunk_texts,
                requirement_family=ctrl.requirement_family,
            )

        # Collect valid rationales and filter chunks
        valid_rationales: list[MappingRationale] = []
        relevant_chunks = []
        for i, eval_result in enumerate(chunk_results):
            if isinstance(eval_result, MappingRationale):
                valid_rationales.append(eval_result)
                relevant_chunks.append(result.supporting_chunks[i])

        result.supporting_chunks = relevant_chunks
        best = select_best_rationale(valid_rationales)
        if best is not None:
            result.rationale = best

    # #7 Skip meta-classify for controls that already have rationales —
    # meta-classification only matters for controls without direct evidence
    if result.rationale is not None:
        return False

    # Classify meta-requirement (7B fast model)
    async with semaphore:
        is_meta = await fast_client.classify_control_type_async(
            control_text=ctrl.as_prompt_text(),
        )

    return is_meta


async def _step_generate_gaps(
    results: list[MappedResult],
    client: OllamaClient,
    semaphore: asyncio.Semaphore,
) -> None:
    """Generate gap rationales concurrently (async, fast model).

    Uses ``generate_gap_async()`` for true async execution instead
    of wrapping a sync call.
    """

    async def _gap_one(
        result: MappedResult,
    ) -> tuple[MappedResult, MappingRationale | None]:
        async with semaphore:
            raw = await client.generate_gap_async(
                control_text=result.control.as_prompt_text(),
            )
            from ctrlmap.llm.structured_output import _parse_response

            parsed = _parse_response(raw)
            if isinstance(parsed, MappingRationale):
                return result, parsed
            return result, None

    gap_results = [r for r in results if r.rationale is None and not r.supporting_chunks]
    if not gap_results:
        return

    tasks = [_gap_one(r) for r in gap_results]
    outcomes = await asyncio.gather(*tasks)
    for result, rationale in outcomes:
        if rationale is not None:
            result.rationale = rationale
