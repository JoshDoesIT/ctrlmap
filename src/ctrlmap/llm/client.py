"""Ollama LLM client for local inference.

Wraps the ``ollama`` Python SDK to generate rationales by sending
policy chunk text and control descriptions to a local Ollama instance.
Supports configurable model selection and graceful connection handling.

Ref: GitHub Issue #18.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ctrlmap.llm.cache import LLMCache
    from ctrlmap.models.schemas import InsufficientEvidence, MappingRationale

import ollama

from ctrlmap._defaults import DEFAULT_LLM_MODEL
from ctrlmap.llm._json_utils import extract_json_object
from ctrlmap.llm.prompts import load_prompt

_log = logging.getLogger("ctrlmap.llm")


class OllamaConnectionError(Exception):
    """Raised when Ollama is not running or unreachable."""


class OllamaClient:
    """Client for local Ollama LLM inference.

    Args:
        model: The Ollama model name to use (default: ``qwen2.5:14b``).
        timeout: Timeout in seconds for inference requests (default: 120).
    """

    def __init__(
        self,
        model: str = DEFAULT_LLM_MODEL,
        timeout: int = 120,
        cache: LLMCache | None = None,
    ) -> None:
        self._model = model
        self._timeout = timeout
        self._cache = cache
        self._async_client = ollama.AsyncClient()

    def is_available(self) -> bool:
        """Check if Ollama is reachable.

        Returns:
            True if Ollama responds to a list request, False otherwise.
        """
        try:
            ollama.list()
            return True
        except Exception:
            return False

    def check_connection(self) -> None:
        """Verify Ollama is running and raise a descriptive error if not.

        Raises:
            OllamaConnectionError: If Ollama is not running or unreachable.
        """
        try:
            ollama.list()
        except Exception as exc:
            msg = (
                "Ollama is not running. Start it with 'ollama serve' "
                "or install from https://ollama.com"
            )
            raise OllamaConnectionError(msg) from exc

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    def call_llm(self, prompt: str, method_name: str) -> str:
        """Send a prompt to Ollama, log timing, and return raw response.

        Centralizes the call → log → return pattern so that every public
        method only needs to build its prompt and interpret the result.

        Args:
            prompt: The fully-formatted LLM prompt string.
            method_name: Identifier for structured log entries
                (e.g. ``"generate"``, ``"classify_control_type"``).

        Returns:
            The raw LLM response content as a string.
        """
        t0 = time.monotonic()
        response = ollama.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
        )
        raw = str(response.message.content)
        _log.debug(
            json.dumps(
                {
                    "method": method_name,
                    "model": self._model,
                    "latency_ms": round((time.monotonic() - t0) * 1000),
                    "output_len": len(raw),
                }
            )
        )
        return raw

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, *, control_text: str, chunk_text: str) -> str:
        """Generate a rationale by sending control + chunk to the LLM.

        Args:
            control_text: The security control description.
            chunk_text: The policy text excerpt.

        Returns:
            The raw LLM response content as a string.

        Raises:
            OllamaConnectionError: If Ollama is not reachable.
        """
        template = load_prompt("compliance_rationale.txt")
        prompt = template.format(
            control_text=control_text,
            chunk_text=chunk_text,
        )
        return self.call_llm(prompt, "generate")

    def classify_control_type(self, *, control_text: str) -> bool:
        """Ask the LLM whether a control is a meta-requirement.

        Uses a focused classification prompt to determine if the control
        is a governance/documentation requirement about other requirements
        (meta) vs. a specific technical/procedural control (substantive).

        Args:
            control_text: The security control description.

        Returns:
            ``True`` if the control is a meta-requirement, ``False`` otherwise.
        """
        template = load_prompt("meta_classification.txt")
        prompt = template.format(control_text=control_text)
        try:
            raw = self.call_llm(prompt, "classify_control_type").strip()
            cleaned = extract_json_object(raw)
            data = json.loads(cleaned)
            return bool(data.get("is_meta", False))
        except Exception:
            return False

    def generate_gap(self, *, control_text: str) -> str:
        """Generate a gap rationale for a control with no policy evidence.

        Args:
            control_text: The security control description.

        Returns:
            The raw LLM response content as a string.

        Raises:
            OllamaConnectionError: If Ollama is not reachable.
        """
        template = load_prompt("gap_rationale.txt")
        prompt = template.format(control_text=control_text)
        return self.call_llm(prompt, "generate_gap")

    def verify_chunk_relevance(
        self,
        *,
        control_text: str,
        chunk_text: str,
        requirement_family: str = "",
    ) -> bool:
        """Ask the LLM whether a chunk directly addresses a control.

        Uses a focused yes/no prompt that is faster than full rationale
        generation. Returns ``False`` when the policy text only shares
        keywords with the control but does not provide direct evidence.

        Args:
            control_text: The security control description.
            chunk_text: The policy text excerpt.
            requirement_family: The parent requirement family title
                (e.g. "Requirement 6: Develop and Maintain Secure Systems").

        Returns:
            ``True`` if the LLM confirms direct relevance, ``False`` otherwise.
        """
        template = load_prompt("relevance_check.txt")
        prompt = template.format(
            control_text=control_text,
            chunk_text=chunk_text,
            requirement_family=requirement_family or "Not specified",
        )
        try:
            raw = self.call_llm(prompt, "verify_chunk_relevance").strip()
            cleaned = extract_json_object(raw)
            data = json.loads(cleaned)
            return bool(data.get("relevant", False))
        except Exception:
            # On error, keep the chunk to avoid false drops
            return True

    # ------------------------------------------------------------------
    # Async API
    # ------------------------------------------------------------------

    async def call_llm_async(self, prompt: str, method_name: str) -> str:
        """Async version of :meth:`call_llm` using ``ollama.AsyncClient``.

        Checks the cache (if configured) before calling the LLM, and
        stores the result after a successful call.

        Args:
            prompt: The fully-formatted LLM prompt string.
            method_name: Identifier for structured log entries.

        Returns:
            The raw LLM response content as a string.
        """
        # Check cache first
        if self._cache is not None:
            cached = self._cache.get(model=self._model, prompt=prompt)
            if cached is not None:
                return cached

        t0 = time.monotonic()
        response = await self._async_client.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
        )
        raw = str(response.message.content)
        _log.debug(
            json.dumps(
                {
                    "method": method_name,
                    "model": self._model,
                    "latency_ms": round((time.monotonic() - t0) * 1000),
                    "output_len": len(raw),
                }
            )
        )

        # Store in cache
        if self._cache is not None:
            self._cache.put(model=self._model, prompt=prompt, response=raw)

        return raw

    async def generate_async(self, *, control_text: str, chunk_text: str) -> str:
        """Async version of :meth:`generate`.

        Args:
            control_text: The security control description.
            chunk_text: The policy text excerpt.

        Returns:
            The raw LLM response content as a string.
        """
        template = load_prompt("compliance_rationale.txt")
        prompt = template.format(
            control_text=control_text,
            chunk_text=chunk_text,
        )
        return await self.call_llm_async(prompt, "generate")

    async def classify_control_type_async(self, *, control_text: str) -> bool:
        """Async version of :meth:`classify_control_type`.

        Args:
            control_text: The security control description.

        Returns:
            ``True`` if the control is a meta-requirement, ``False`` otherwise.
        """
        template = load_prompt("meta_classification.txt")
        prompt = template.format(control_text=control_text)
        try:
            raw = (await self.call_llm_async(prompt, "classify_control_type")).strip()
            cleaned = extract_json_object(raw)
            data = json.loads(cleaned)
            return bool(data.get("is_meta", False))
        except Exception:
            return False

    async def generate_gap_async(self, *, control_text: str) -> str:
        """Async version of :meth:`generate_gap`.

        Args:
            control_text: The security control description.

        Returns:
            The raw LLM response content as a string.
        """
        template = load_prompt("gap_rationale.txt")
        prompt = template.format(control_text=control_text)
        return await self.call_llm_async(prompt, "generate_gap")

    async def verify_chunk_relevance_async(
        self,
        *,
        control_text: str,
        chunk_text: str,
        requirement_family: str = "",
    ) -> bool:
        """Async version of :meth:`verify_chunk_relevance`.

        Args:
            control_text: The security control description.
            chunk_text: The policy text excerpt.
            requirement_family: The parent requirement family title.

        Returns:
            ``True`` if the LLM confirms direct relevance, ``False`` otherwise.
        """
        template = load_prompt("relevance_check.txt")
        prompt = template.format(
            control_text=control_text,
            chunk_text=chunk_text,
            requirement_family=requirement_family or "Not specified",
        )
        try:
            raw = (await self.call_llm_async(prompt, "verify_chunk_relevance")).strip()
            cleaned = extract_json_object(raw)
            data = json.loads(cleaned)
            return bool(data.get("relevant", False))
        except Exception:
            # On error, keep the chunk to avoid false drops
            return True

    async def evaluate_chunk_async(
        self,
        *,
        control_text: str,
        chunk_text: str,
        requirement_family: str = "",
    ) -> MappingRationale | InsufficientEvidence:
        """Evaluate a chunk in a single LLM call (merged relevance + rationale).

        Combines the relevance check and rationale generation into one
        prompt to halve the number of LLM calls. Returns
        ``InsufficientEvidence`` for irrelevant chunks and
        ``MappingRationale`` for relevant ones.

        Args:
            control_text: The security control description.
            chunk_text: The policy text excerpt.
            requirement_family: The parent requirement family title.

        Returns:
            A ``MappingRationale`` or ``InsufficientEvidence`` instance.
        """
        from ctrlmap.llm.structured_output import _parse_response
        from ctrlmap.models.schemas import InsufficientEvidence

        template = load_prompt("merged_relevance_rationale.txt")
        prompt = template.format(
            control_text=control_text,
            chunk_text=chunk_text,
            requirement_family=requirement_family or "Not specified",
        )

        max_retries = 2
        for _attempt in range(max_retries + 1):
            raw = await self.call_llm_async(prompt, "evaluate_chunk")
            result = _parse_response(raw)
            if result is not None:
                return result

        return InsufficientEvidence(
            reason="Invalid LLM output after retries.",
            required_context="A well-formed JSON response from the LLM.",
        )

    async def evaluate_chunks_batch_async(
        self,
        *,
        control_text: str,
        chunk_texts: list[str],
        requirement_family: str = "",
    ) -> list[MappingRationale | InsufficientEvidence]:
        """Evaluate multiple chunks in a single LLM call for performance.

        Sends all chunks for one control in a single prompt and asks the
        LLM to return a JSON array of evaluations.  This turns
        ``controls x chunks`` calls into just ``controls`` calls.

        Falls back to ``InsufficientEvidence`` for all chunks if the
        response cannot be parsed.

        Args:
            control_text: The security control description.
            chunk_texts: List of policy text excerpts to evaluate.
            requirement_family: The parent requirement family title.

        Returns:
            A list of ``MappingRationale`` or ``InsufficientEvidence``,
            one per input chunk, in the same order.
        """
        from ctrlmap.llm.structured_output import _parse_batch_response
        from ctrlmap.models.schemas import InsufficientEvidence

        template = load_prompt("batch_evaluation.txt")

        # Build numbered chunk listing
        numbered_chunks = "\n".join(
            f"### Chunk {i}\n{text}" for i, text in enumerate(chunk_texts)
        )

        prompt = template.format(
            control_text=control_text,
            chunk_count=len(chunk_texts),
            numbered_chunks=numbered_chunks,
            requirement_family=requirement_family or "Not specified",
        )

        raw = await self.call_llm_async(prompt, "evaluate_chunks_batch")
        results = _parse_batch_response(raw, expected_count=len(chunk_texts))

        if results is not None:
            return results

        # Fallback: return InsufficientEvidence for all chunks
        return [
            InsufficientEvidence(
                reason="Batch evaluation failed: invalid LLM output.",
                required_context="A well-formed JSON array from the LLM.",
            )
            for _ in chunk_texts
        ]
