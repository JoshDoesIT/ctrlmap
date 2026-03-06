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
{{"type": "MappingRationale", "is_compliant": true/false, \
"compliance_level": "fully_compliant" or "partially_compliant" or "non_compliant", \
"confidence_score": 0.0-1.0, \
"explanation": "your explanation grounded in the provided text"}}

Use "fully_compliant" when the policy text fully addresses ALL aspects of the control. \
Use "partially_compliant" when the policy addresses SOME but not ALL requirements \
of the control (e.g. password length but not complexity). \
Use "non_compliant" when the policy does not address the control at all.

If there is insufficient evidence, respond with:
{{"type": "InsufficientEvidence", "reason": "why the evidence is insufficient", \
"required_context": "what additional context would be needed"}}
"""
_RELEVANCE_PROMPT = """\
You are a strict GRC compliance auditor. Determine whether the \
POLICY TEXT below provides DIRECT evidence that the CONTROL REQUIREMENT \
is addressed.

## Requirement Family
{requirement_family}

## Control Requirement
{control_text}

## Policy Text
{chunk_text}

## Rules
- The policy text must DIRECTLY address the specific requirement, \
not merely mention related topics.
- Sharing a keyword (e.g. "NSC", "access", "security") is NOT enough.
- The REQUIREMENT FAMILY above describes the broad topic this control \
belongs to. If the policy text is about a DIFFERENT domain (e.g. the \
control is about software development but the policy text is about \
key management or data classification), it is NOT relevant.
- If the control references a SPECIFIC requirement family or topic \
(e.g. "Requirement 6", "secure development", "network security"), \
the policy text must address THAT specific topic. A policy about a \
DIFFERENT topic (e.g. key management, data classification) that \
happens to use similar language ("designated", "responsibilities") \
is NOT relevant.
- REJECT the following as NOT relevant:
  * Approval or signature blocks (e.g. "This policy has been approved by the CISO")
  * Generic scope or purpose statements that do not prescribe specific controls
  * Text that only describes who the policy applies to, without stating requirements
  * Boilerplate disclaimers, headers, footers, or effective-date notices
- Answer ONLY with a JSON object: {{"relevant": true}} or {{"relevant": false}}
"""
_META_CLASSIFY_PROMPT = """\
You are a GRC compliance analyst. Classify whether the following \
security control is a META-REQUIREMENT or a SUBSTANTIVE CONTROL.

A META-REQUIREMENT is ONLY a control that:
1. EXPLICITLY references "Requirement X" (another requirement family) by name
2. Describes governance, documentation, or role assignment FOR that \
other requirement — NOT a specific security measure itself
3. Would be satisfied by properly managing/documenting the OTHER requirements

Examples of META-REQUIREMENTS (answer is_meta: true):
- "All security policies and operational procedures that are identified \
in Requirement 1 are documented, kept up to date, in use, and known to \
all affected parties."
- "Roles and responsibilities for performing activities in Requirement 3 \
are documented, assigned, and understood."

Examples of SUBSTANTIVE CONTROLS (answer is_meta: false):
- "Account data storage is kept to a minimum."
- "Configuration standards for NSC rulesets are defined, implemented, \
and maintained."
- "SAD is not stored after authorization, even if encrypted."
- "An overall information security policy is established, published, \
maintained, and disseminated."

IMPORTANT: A control that prescribes a SPECIFIC security action is ALWAYS \
a substantive control, even if it mentions "documentation", "policies", \
or "procedures". Only classify as meta if the control's SOLE purpose is \
to govern/document OTHER numbered requirements.

## Control
{control_text}

## Rules
- Answer ONLY with a JSON object: {{"is_meta": true}} or {{"is_meta": false}}
"""
_GAP_PROMPT_TEMPLATE = """\
You are a GRC compliance analyst. The following security control \
requirement has NO matching policy documentation in the organization's \
policy library.

## Security Control
{control_text}

## Instructions
Explain why this control is non-compliant due to missing policy coverage. \
Briefly describe what policy documentation would be needed to address it. \
Respond ONLY with a JSON object. Do NOT include any text outside the JSON object.

{{"type": "MappingRationale", "is_compliant": false, "confidence_score": 0.0-1.0, \
"explanation": "your explanation of the gap"}}
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
        prompt = _META_CLASSIFY_PROMPT.format(control_text=control_text)
        try:
            response = ollama.chat(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = str(response.message.content).strip()
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
        prompt = _GAP_PROMPT_TEMPLATE.format(control_text=control_text)
        response = ollama.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return str(response.message.content)

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
        prompt = _RELEVANCE_PROMPT.format(
            control_text=control_text,
            chunk_text=chunk_text,
            requirement_family=requirement_family or "Not specified",
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
