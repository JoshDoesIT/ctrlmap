"""LLM enrichment pipeline for compliance mapping results.

.. versionchanged:: 0.9.0
   Simplified to 3-stage pipeline: Evaluate → Classify/Gap → Resolve.

Extracted from ``map_command.py`` to isolate the LLM pipeline from CLI
wiring, enabling independent testing and reuse.

Pipeline:
    0. Heuristic meta-detection (instant — skips meta from Step 1).
    1. **Evaluate** chunks via batch evaluation (14B, non-meta only).
    2. **Classify & Fill**: batch-classify meta-requirements (7B) +
       generate gap rationales for unmapped controls (7B, async).
    3. **Resolve** meta-requirements via sibling aggregation.

Performance:
    - **Meta-control skip** avoids evaluating ~22 governance controls
      whose compliance is always inferred from siblings.
    - **JSON mode** tells Ollama to constrain output to valid JSON,
      eliminating parse failures and retries.
    - **Batch evaluation** sends all chunks for ONE control in a single
      LLM call, reducing ``controls x chunks`` calls to just ``controls``.
    - **Batch meta-classification** sends ALL unmapped controls in a
      single LLM call, reducing ``N`` calls to ``1``.
    - **Sentence-aware truncation** caps chunk text at 1,200 chars
      using sentence boundaries to preserve evidence meaning.
    - **Model tiering** uses the fast 7B model for simple tasks
      (meta-classification, gap rationale) and 14B for
      accuracy-critical compliance evaluation.
    - **LLM cache** eliminates redundant calls during re-runs.
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
from ctrlmap.llm.structured_output import aggregate_rationales
from ctrlmap.map.meta_requirements import resolve_meta_requirements
from ctrlmap.models.schemas import MappedResult, MappingRationale, ParsedChunk

# Default cache directory (relative to cwd)
_DEFAULT_CACHE_DIR = Path(".ctrlmap_cache")

# Heuristic pre-filter: minimum chunk length to send to LLM (chars)
_MIN_CHUNK_LENGTH = 30


def enrich_with_rationale(
    results: list[MappedResult],
    *,
    llm_model: str,
    concurrency: int = 24,
    cache_enabled: bool = False,
) -> list[MappedResult]:
    """Enrich mapping results with LLM-generated rationales.

    Runs a four-step streaming pipeline:
    1. Evaluate chunks via batch evaluation (one LLM call per control).
    2. Batch-classify meta-requirements (one LLM call for all unmapped).
    3. Generate gap rationales for unmapped controls (async).
    4. Resolve meta-requirements via sibling aggregation.

    Args:
        results: List of MappedResult objects from vector similarity.
        llm_model: Ollama model name for inference.
        concurrency: Maximum concurrent LLM requests (default: 8).
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

    Pipeline:
        0. Heuristic meta-detection (instant — skips meta from Step 1)
        1. Evaluate chunks (14B model — non-meta controls only)
        2. LLM meta-classify remaining controls (7B model)
        3. Gap rationales for unmapped controls (7B model)
        4. Meta-resolution via sibling aggregation (no LLM)

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
    # Fast client (7B) for: meta-classify, gap rationale
    fast_client = OllamaClient(model=DEFAULT_FAST_MODEL, cache=cache)

    semaphore = asyncio.Semaphore(concurrency)

    # Warm up both models concurrently (pre-load into GPU memory)
    t_warmup = time.monotonic()
    await asyncio.gather(llm_client.warmup_async(), fast_client.warmup_async())
    console.print(f"[dim]  Model warmup: {time.monotonic() - t_warmup:.1f}s[/]")

    # Heuristic pre-filter: drop chunks that are too short
    _prefilter_chunks(results)

    # Step 0: Heuristic meta-detection (instant, before Step 1)
    from ctrlmap.map.meta_requirements import _heuristic_is_meta

    meta_ids: set[str] = set()
    for r in results:
        if _heuristic_is_meta(r.control):
            meta_ids.add(r.control.control_id)
    heuristic_count = len(meta_ids)

    # Partition into meta vs non-meta controls
    non_meta_results = [r for r in results if r.control.control_id not in meta_ids]




    # Step 0c: Deduplicate chunks within each control
    for r in non_meta_results:
        r.supporting_chunks = _deduplicate_chunks(r.supporting_chunks)

    total_chunks = sum(len(r.supporting_chunks) for r in non_meta_results)
    console.print(
        f"[bold blue]LLM:[/] Enriching {len(non_meta_results)} non-meta controls, "
        f"{total_chunks} chunks (concurrency={concurrency}, "
        f"skipped {heuristic_count} meta-controls)..."
    )

    # Step 1: Evaluate chunks (batch) — 14B model, non-meta only
    t0 = time.monotonic()
    per_control_tasks = [_process_one_control(r, llm_client, semaphore) for r in non_meta_results]
    await asyncio.gather(*per_control_tasks)
    console.print(f"[dim]  Step 1 (batch evaluate): {time.monotonic() - t0:.1f}s[/]")

    # Step 2: LLM batch meta-classification (only non-heuristic controls)
    t1 = time.monotonic()
    non_heuristic = [
        (i, r) for i, r in enumerate(results)
        if r.control.control_id not in meta_ids
    ]
    console.print(
        f"[bold blue]LLM:[/] Batch meta-classifying "
        f"{len(non_heuristic)} controls ({DEFAULT_FAST_MODEL}, "
        f"skipped {heuristic_count} heuristic)..."
    )
    if non_heuristic:
        control_texts = [r.control.as_prompt_text() for _, r in non_heuristic]
        async with semaphore:
            batch_flags = await fast_client.classify_controls_batch_async(
                control_texts=control_texts,
            )
        for (orig_idx, _), is_meta in zip(non_heuristic, batch_flags):
            if is_meta:
                meta_ids.add(results[orig_idx].control.control_id)

    console.print(
        f"[dim]  Step 2 (batch meta-classify): {time.monotonic() - t1:.1f}s "
        f"({heuristic_count} heuristic, {len(meta_ids)} total)[/]"
    )

    # Step 3: Generate gap rationales (concurrent, fast model)
    gap_count = sum(1 for r in results if r.rationale is None and not r.supporting_chunks)
    if gap_count:
        t2 = time.monotonic()
        console.print(
            f"[bold blue]LLM:[/] Generating {gap_count} gap rationales ({DEFAULT_FAST_MODEL})..."
        )
        await _step_generate_gaps(results, fast_client, semaphore)
        console.print(f"[dim]  Step 3 (gap rationales): {time.monotonic() - t2:.1f}s[/]")

    # Step 4: Resolve meta-requirements via sibling aggregation (no LLM)
    t3 = time.monotonic()
    console.print("[bold blue]LLM:[/] Resolving meta-requirements...")
    resolved = resolve_meta_requirements(results=results, meta_control_ids=meta_ids)
    console.print(f"[dim]  Step 4 (meta-resolution): {time.monotonic() - t3:.1f}s[/]")

    console.print(f"[bold green]Pipeline total:[/] {time.monotonic() - pipeline_start:.1f}s")

    if cache is not None:
        cache.flush()
        stats = cache.stats()
        console.print(f"[dim]Cache stats: {stats['hits']} hits, {stats['misses']} misses[/]")

    return resolved


def _prefilter_chunks(results: list[MappedResult]) -> None:
    """Drop chunks that are too short to contain meaningful policy text.

    Removes headers, footers, and other trivially short fragments
    before they reach the expensive LLM evaluation step.
    """
    for result in results:
        result.supporting_chunks = [
            chunk
            for chunk in result.supporting_chunks
            if len(chunk.raw_text.strip()) >= _MIN_CHUNK_LENGTH
        ]


def _deduplicate_chunks(chunks: list[ParsedChunk]) -> list[ParsedChunk]:
    """Remove duplicate chunks within a single control's chunk list.

    Deduplicates by ``(document_name, section_header, raw_text[:100])``
    key, keeping the first occurrence.
    """
    seen: set[tuple[str, str | None, str]] = set()
    unique: list[ParsedChunk] = []
    for chunk in chunks:
        key = (chunk.document_name, chunk.section_header, chunk.raw_text[:100])
        if key not in seen:
            seen.add(key)
            unique.append(chunk)
    return unique




async def _process_one_control(
    result: MappedResult,
    client: OllamaClient,
    semaphore: asyncio.Semaphore,
) -> None:
    """Process a single control: batch-evaluate all chunks.

    Uses **batch evaluation** to send all chunks for this control in a
    single LLM call, reducing LLM calls from N to 1 per control.
    Applies chunk truncation to reduce token count.

    Args:
        result: The MappedResult for this control.
        client: The primary OllamaClient (14B for rationale).
        semaphore: Concurrency limiter.
    """
    ctrl = result.control

    # Batch evaluate ALL chunks in one LLM call (14B model)
    if result.supporting_chunks:
        # Prepend source metadata so the LLM can detect domain mismatches
        chunk_texts = []
        for chunk in result.supporting_chunks:
            header = f"[Source: {chunk.document_name}"
            if chunk.section_header:
                header += f" | Section: {chunk.section_header}"
            header += "]\n"
            chunk_texts.append(header + client.truncate_chunk(chunk.raw_text))

        async with semaphore:
            chunk_results, sub_reqs = await client.evaluate_chunks_batch_async(
                control_text=ctrl.as_prompt_text(),
                chunk_texts=chunk_texts,
                requirement_family=ctrl.requirement_family,
            )

        # Collect valid rationales, their sub_requirements, and filter chunks
        valid_rationales: list[MappingRationale] = []
        valid_sub_reqs: list[list[dict[str, object]]] = []
        relevant_chunks = []
        for i, eval_result in enumerate(chunk_results):
            if isinstance(eval_result, MappingRationale):
                valid_rationales.append(eval_result)
                valid_sub_reqs.append(sub_reqs[i] if i < len(sub_reqs) else [])
                relevant_chunks.append(result.supporting_chunks[i])

        result.supporting_chunks = relevant_chunks

        # Aggregate sub-requirement coverage across all chunks
        best = aggregate_rationales(
            rationales=valid_rationales,
            sub_requirements=valid_sub_reqs,
        )
        if best is not None:
            result.rationale = best


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
