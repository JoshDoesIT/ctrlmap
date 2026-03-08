"""Ollama LLM client for local inference.

Wraps the ``ollama`` Python SDK to generate rationales by sending
policy chunk text and control descriptions to a local Ollama instance.
Supports configurable model selection and graceful connection handling.

Ref: GitHub Issue #18.
"""

from __future__ import annotations

import json
import logging
import re
import time

import ollama

from ctrlmap._defaults import DEFAULT_LLM_MODEL
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

    def __init__(self, model: str = DEFAULT_LLM_MODEL, timeout: int = 120) -> None:
        self._model = model
        self._timeout = timeout

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
                    "method": "generate",
                    "model": self._model,
                    "latency_ms": round((time.monotonic() - t0) * 1000),
                    "output_len": len(raw),
                }
            )
        )
        return raw

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
            t0 = time.monotonic()
            response = ollama.chat(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0},
            )
            raw = str(response.message.content).strip()
            _log.debug(
                json.dumps(
                    {
                        "method": "classify_control_type",
                        "model": self._model,
                        "latency_ms": round((time.monotonic() - t0) * 1000),
                        "output_len": len(raw),
                    }
                )
            )
            cleaned = _extract_json(raw)
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
                    "method": "generate_gap",
                    "model": self._model,
                    "latency_ms": round((time.monotonic() - t0) * 1000),
                    "output_len": len(raw),
                }
            )
        )
        return raw

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
            t0 = time.monotonic()
            response = ollama.chat(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0},
            )
            raw = str(response.message.content).strip()
            _log.debug(
                json.dumps(
                    {
                        "method": "verify_chunk_relevance",
                        "model": self._model,
                        "latency_ms": round((time.monotonic() - t0) * 1000),
                        "output_len": len(raw),
                    }
                )
            )
            # Extract JSON from potential markdown fences / preamble
            cleaned = _extract_json(raw)
            data = json.loads(cleaned)
            return bool(data.get("relevant", False))
        except Exception:
            # On error, keep the chunk to avoid false drops
            return True


def _extract_json(raw: str) -> str:
    """Extract a JSON object from raw LLM output.

    Handles markdown code fences, preamble text, and trailing
    explanations surrounding the JSON object.
    """
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return brace_match.group(0)
    return text
