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

_log = logging.getLogger("ctrlmap.llm")

_DEFAULT_MODEL = "qwen2.5:14b"

_PROMPT_TEMPLATE = """You are a GRC compliance analyst. Given a security control requirement \
and a policy text excerpt, determine whether the policy text provides sufficient evidence \
to address the control requirement.

## Security Control
{control_text}

## Policy Text
{chunk_text}

## Instructions
Follow these steps IN ORDER. Think through each step before giving your answer.

### Step 1 — Decompose the Control
List EVERY distinct sub-requirement in the security control INDIVIDUALLY. \
Many controls contain 4-6 sub-requirements separated by commas, semicolons, \
or conjunctions. You MUST identify EACH ONE. For example, \
if the control says "Define account types, assign account managers, require \
approvals, and align with termination processes", that is FOUR separate \
sub-requirements. Do NOT skip any.
IMPORTANT: Controls often have MULTIPLE SENTENCES. Each sentence may \
introduce NEW sub-requirements beyond the first sentence's list. Read \
the ENTIRE control text, including ALL sentences after the first. For \
example, "Implement X, Y, and Z. Coordinate with A. Incorporate B." \
contains at least 5 sub-requirements, not 3.
NOTE: Compound verbs describing the SAME object are ONE sub-requirement, \
not multiple. For example, "Establish and document usage restrictions" is \
ONE sub-requirement about usage restrictions, not two separate requirements.\
 Count sub-requirements by their distinct OBJECTS/TOPICS, not by their verbs.

### Step 2 — Check Each Sub-Requirement Against the Policy Text
For EACH sub-requirement you listed in Step 1, determine whether the \
policy text provides DIRECT evidence addressing it. Mark each as COVERED \
or NOT COVERED with a brief justification.

SYNONYM TOLERANCE: Treat equivalent GRC concepts as COVERED. For example:
- "passwords expire every 90 days" = "refreshing authenticators periodically"
- "password complexity" = "authenticator strength"
- "VPN with MFA" = "configuration requirements for remote access"
- "automated scanning tools" = "assessors" is NOT equivalent (tools ≠ people)
Use GRC domain knowledge to identify genuine equivalences.

COMPENSATING CONTROLS: When a policy mentions compensating controls for a \
requirement, those compensating controls ARE evidence for the sub-requirements \
they address. For example, "enhanced logging" for shared accounts IS evidence \
for "every action attributable to an individual user." "Dual-authorization" IS \
evidence for "individual identity is confirmed before access."

### Step 3 — Classify Compliance Level
Count your results from Step 2. Apply these rules STRICTLY based on the COUNT:
- **fully_compliant**: ALL sub-requirements are COVERED. If you listed N \
sub-requirements and ALL N are COVERED, this is fully_compliant. If even \
ONE is NOT COVERED, this CANNOT be fully_compliant. \
VERIFICATION: Before answering fully_compliant, re-read the control and \
confirm that EVERY sub-requirement has a matching phrase or equivalent \
concept in the chunk. If you cannot point to specific evidence for any \
sub-requirement, change your answer to partially_compliant.
- **partially_compliant**: AT LEAST ONE sub-requirement is COVERED, but \
NOT ALL. For example, if 2 out of 5 sub-requirements are COVERED, this is \
partially_compliant. Even if only 1 out of 6 is covered, it is still \
partially_compliant (not non_compliant) because there IS evidence.
- **non_compliant**: ZERO sub-requirements are COVERED. The policy text \
provides NO evidence whatsoever for ANY sub-requirement. This should ONLY \
be used when the chunk is about a completely different topic. \
Before answering non_compliant, ask yourself: "Does the chunk discuss \
the same general domain as the control?" If YES, it is likely at least \
partially_compliant. For example, a chunk about "assessing security controls" \
IS relevant to a control about "control assessments" even if it only \
covers some sub-requirements.

CRITICAL: Pay close attention to the SUBJECT of each action. The same verb applied \
to DIFFERENT subjects does NOT count as evidence. For example:
- "Reviewing user access rights" is NOT evidence for "reviewing the information security policy"
- "Encrypting data in transit" is NOT evidence for "encrypting data at rest"
- "Training developers" is NOT evidence for "training all employees"
The policy text must address the EXACT SAME subject/object as the control.

### Step 4 — Respond with JSON ONLY
Do NOT include any text outside the JSON object.

If there is sufficient evidence, respond with:
{{"type": "MappingRationale", "is_compliant": true/false, \
"compliance_level": "fully_compliant" or "partially_compliant" or "non_compliant", \
"confidence_score": 0.0-1.0, \
"sub_requirements": [\
  {{"requirement": "<sub-requirement text>", "covered": true/false, \
"evidence": "<exact quote from policy text or empty string if not covered>"}}\
], \
"explanation": "your explanation grounded in the provided text"}}

IMPORTANT: The "sub_requirements" array MUST contain EVERY sub-requirement \
from Step 1. For each one, set "covered" to true or false, and provide the \
EXACT quote from the policy text as "evidence" (use empty string "" if not \
covered). The compliance_level MUST be consistent with your sub_requirements: \
if ALL are covered then fully_compliant, if SOME then partially_compliant, if \
NONE then non_compliant.

Set is_compliant to true for fully_compliant AND partially_compliant. \
Set is_compliant to false only for non_compliant.

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
- CRITICAL — Subject mismatch: The same action/verb applied to a \
DIFFERENT subject does NOT constitute evidence. For example, \
"reviewing user access rights" is NOT relevant to a control about \
"reviewing the access control policy document" — one is an \
OPERATIONAL activity, the other is a GOVERNANCE activity about THE \
POLICY ITSELF. Similarly, "performing security training" is NOT the \
same as "reviewing the training policy." When the control mentions \
"Policy and Procedures" or uses verbs like "develop, document, \
disseminate, review, update" applied to A POLICY, the policy text must \
be about THE POLICY DOCUMENT ITSELF — not about performing the \
activities that the policy describes.
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
- IMPORTANT — Same subject, different approach: If the policy text \
addresses the EXACT SAME subject as the control (e.g. both discuss \
shared/group IDs, or both discuss password requirements), the text IS \
relevant even if the policy's specific stance differs from the \
control's wording (e.g. "prohibited" in the policy vs "only used on \
exception basis" in the control — both address shared/group IDs).
- IMPORTANT — Synonyms and paraphrases: Different wording for the \
SAME concept counts as relevant. In GRC, many terms are used \
INTERCHANGEABLY. You MUST treat these as equivalent:
  * "security awareness training" = "security literacy training" = \
"security training" (NIST uses "literacy", industry uses "awareness")
  * "authenticator management" = "password policy" = "credential management"
  * "role-based access control" and "access enforcement" → SAME concept
  * "automated vulnerability scanning" and "continuous monitoring" → SAME concept
  * "encrypt data at rest" and "AES-256 encryption on storage" → SAME concept
  * "audit record generation" and "system logging capability" → SAME concept
If the policy text clearly addresses the control's underlying concept \
using different terminology, mark it as relevant.
- IMPORTANT — Partial coverage IS relevant: If the control has \
MULTIPLE sub-requirements and the policy text addresses at least ONE \
of them substantively, it IS relevant. Relevance means "provides \
evidence related to this control" — it does NOT require covering every \
sub-requirement. For example, a chunk about password complexity IS \
relevant to a control about authenticator management, even if the \
chunk does not address initial authenticator content or default \
authenticator changes. However, partial coverage does NOT mean \
"related topic" — the chunk must directly implement at least one of \
the control's STATED ACTIONS, not merely describe a related concept \
from a different control (e.g., audit record CONTENT is not relevant \
to audit record REVIEW).
- REJECT the following as NOT relevant:
  * Approval or signature blocks (e.g. "This policy has been approved by the CISO")
  * Purpose or scope statements that describe what a policy covers \
WITHOUT prescribing specific controls (e.g. "This policy defines the \
requirements for protecting sensitive data..." or "This policy applies \
to all systems...")
  * Text that only describes who the policy applies to, without stating requirements
  * Boilerplate disclaimers, headers, footers, or effective-date notices
- Answer ONLY with a JSON object: {{"relevant": true}} or {{"relevant": false}}
"""

_META_CLASSIFY_PROMPT = """\
You are a GRC compliance analyst. Classify whether the following \
security control is a META-REQUIREMENT or a SUBSTANTIVE CONTROL.

## Definitions

A META-REQUIREMENT is a control whose SOLE purpose is to ensure that \
another set of numbered requirements are properly documented, maintained, \
and communicated. It does NOT itself prescribe any specific security \
action — it only governs OTHER requirements.

A SUBSTANTIVE CONTROL prescribes a specific security action, technical \
measure, data handling rule, role assignment, or procedural requirement. \
Most controls are substantive.

## Examples

META-REQUIREMENTS (is_meta: true):
- "All security policies and operational procedures that are identified \
in Requirement 1 are documented, kept up to date, in use, and known to \
all affected parties." → ONLY governs Requirement 1 documentation.
- "Roles and responsibilities for performing activities in Requirement 3 \
are documented, assigned, and understood." → ONLY governs Requirement 3 roles.

SUBSTANTIVE CONTROLS (is_meta: false):
- "All users are assigned a unique ID before access is allowed." → prescribes unique IDs.
- "Bespoke software is developed securely." → prescribes secure development.
- "An overall information security policy is established." → prescribes establishing a policy.
- "The security policy defines roles and responsibilities." → prescribes defining roles.
- "Responsibility is formally assigned to a CISO." → prescribes a CISO assignment.
- "The card verification code is not stored after authorization." → prescribes data handling.
- "Access for terminated users is immediately revoked." → prescribes access revocation.
- "All changes to network connections are approved." → prescribes change approval.

## Control
{control_text}

## Instructions
Think step by step:
1. What specific action does this control prescribe?
2. Does it EXPLICITLY reference other numbered requirements (e.g., \
"Requirement 1", "Requirement 6") as the subject it governs?
3. Is its SOLE purpose to ensure documentation/governance of those \
other requirements, with NO specific security action of its own?

If ALL three answers point to meta, answer is_meta: true. \
Otherwise, answer is_meta: false. Most controls are substantive.

End your response with ONLY a JSON object on the last line: \
{{"is_meta": true}} or {{"is_meta": false}}
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
        prompt = _META_CLASSIFY_PROMPT.format(control_text=control_text)
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
        prompt = _GAP_PROMPT_TEMPLATE.format(control_text=control_text)
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
        prompt = _RELEVANCE_PROMPT.format(
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
