"""Ollama LLM client for local inference.

Wraps the ``ollama`` Python SDK to generate rationales by sending
policy chunk text and control descriptions to a local Ollama instance.
Supports configurable model selection and graceful connection handling.

Ref: GitHub Issue #18.
"""

from __future__ import annotations

import json
import re

import ollama

_DEFAULT_MODEL = "llama3"

_PROMPT_TEMPLATE = """You are a GRC compliance analyst. Given a security control requirement \
and a policy text excerpt, determine whether the policy text provides sufficient evidence \
to address the control requirement.

## Security Control
{control_text}

## Policy Text
{chunk_text}

## Instructions
Analyze whether the policy text addresses the security control requirement. \
Respond ONLY with a JSON object. Do NOT include any text outside the JSON object.

If there is sufficient evidence, respond with:
{{"type": "MappingRationale", "is_compliant": true/false, "confidence_score": 0.0-1.0, \
"explanation": "your explanation grounded in the provided text"}}

If there is insufficient evidence, respond with:
{{"type": "InsufficientEvidence", "reason": "why the evidence is insufficient", \
"required_context": "what additional context would be needed"}}
"""
_RELEVANCE_PROMPT = """\
You are a strict GRC compliance auditor. Determine whether the \
POLICY TEXT below provides DIRECT evidence that the CONTROL REQUIREMENT \
is addressed.

## Control Requirement
{control_text}

## Policy Text
{chunk_text}

## Rules
- The policy text must DIRECTLY address the specific requirement, \
not merely mention related topics.
- Sharing a keyword (e.g. "NSC", "access") is NOT enough.
- Answer ONLY with a JSON object: {{"relevant": true}} or {{"relevant": false}}
"""


class OllamaConnectionError(Exception):
    """Raised when Ollama is not running or unreachable."""


class OllamaClient:
    """Client for local Ollama LLM inference.

    Args:
        model: The Ollama model name to use (default: ``llama3``).
        timeout: Timeout in seconds for inference requests (default: 120).
    """

    def __init__(self, model: str = _DEFAULT_MODEL, timeout: int = 120) -> None:
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
        prompt = _PROMPT_TEMPLATE.format(
            control_text=control_text,
            chunk_text=chunk_text,
        )

        response = ollama.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return str(response.message.content)

    def verify_chunk_relevance(self, *, control_text: str, chunk_text: str) -> bool:
        """Ask the LLM whether a chunk directly addresses a control.

        Uses a focused yes/no prompt that is faster than full rationale
        generation. Returns ``False`` when the policy text only shares
        keywords with the control but does not provide direct evidence.

        Args:
            control_text: The security control description.
            chunk_text: The policy text excerpt.

        Returns:
            ``True`` if the LLM confirms direct relevance, ``False`` otherwise.
        """
        prompt = _RELEVANCE_PROMPT.format(
            control_text=control_text,
            chunk_text=chunk_text,
        )
        try:
            response = ollama.chat(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = str(response.message.content).strip()
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
