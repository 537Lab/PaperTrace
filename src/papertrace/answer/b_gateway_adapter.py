"""D adapter from its B-neutral generation port to Module B's public gateway.

Traceability: FR-D-03, INV-04, INV-07 (partial). This is the only D module that
names B; it imports ``papertrace.retrieval.gateway`` lazily inside ``call`` so
module import stays B-neutral. Conversion is explicit and field-by-field, and
external type/shape errors fail closed as ``GenerationResultShapeError`` without
filtering, coercion or a broad gateway-exception catch. Review, approval and
release decisions remain in the coordinator.
"""

from collections.abc import Sequence
from typing import Any, Literal, cast

from papertrace.answer.generation import (
    GenerationAccounting,
    GenerationCallRequest,
    GenerationCallResult,
    GenerationResultShapeError,
)

_MISSING = object()


def _accounting(value: object) -> GenerationAccounting | None:
    """FR-D-03: copy B's optional accounting without defaults or coercion."""
    if value is None:
        return None
    provider = getattr(value, "provider", _MISSING)
    model = getattr(value, "model", _MISSING)
    attempts = getattr(value, "answer_model_attempts", _MISSING)
    if provider is _MISSING or model is _MISSING or attempts is _MISSING:
        raise GenerationResultShapeError(
            "accounting must expose provider, model and answer_model_attempts"
        )
    if not isinstance(provider, str) or not provider.strip():
        raise GenerationResultShapeError("accounting.provider must be a nonblank string")
    if not isinstance(model, str) or not model.strip():
        raise GenerationResultShapeError("accounting.model must be a nonblank string")
    if attempts is not None:
        if (
            not isinstance(attempts, int)
            or isinstance(attempts, bool)
            or attempts < 0
        ):
            raise GenerationResultShapeError(
                "accounting.answer_model_attempts must be a nonnegative int or None"
            )
    return GenerationAccounting(
        provider=provider,
        model=model,
        answer_model_attempts=attempts,
    )


def _text_sequence(value: object, *, name: str) -> tuple[str, ...]:
    """Return a nonblank, duplicate-free string sequence without coercion."""
    if isinstance(value, (str, bytes, bytearray, memoryview)):
        raise GenerationResultShapeError(f"{name} must not be a string or bytes")
    if not isinstance(value, Sequence):
        raise GenerationResultShapeError(f"{name} must be a sequence of strings")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise GenerationResultShapeError(f"{name} must contain nonblank strings")
        items.append(item)
    if len(set(items)) != len(items):
        raise GenerationResultShapeError(f"{name} must not contain duplicates")
    return tuple(items)


def _alias_pairs(value: object) -> tuple[tuple[str, str], ...]:
    """Return valid two-item aliases; repeated targets stay allowed, keys may not."""
    if isinstance(value, (str, bytes, bytearray, memoryview)):
        raise GenerationResultShapeError("citation_aliases must be a sequence of pairs")
    if not isinstance(value, Sequence):
        raise GenerationResultShapeError("citation_aliases must be a sequence of pairs")
    pairs: list[tuple[str, str]] = []
    keys: list[str] = []
    for entry in value:
        if isinstance(entry, (str, bytes, bytearray, memoryview)):
            raise GenerationResultShapeError("citation alias must be a two-item pair")
        if not isinstance(entry, Sequence) or len(entry) != 2:
            raise GenerationResultShapeError("citation alias must be a two-item pair")
        key, target = entry
        if (
            not isinstance(key, str)
            or not isinstance(target, str)
            or not key.strip()
            or not target.strip()
        ):
            raise GenerationResultShapeError(
                "citation alias needs a nonblank string key and target"
            )
        keys.append(key)
        pairs.append((key, target))
    if len(set(keys)) != len(keys):
        raise GenerationResultShapeError("citation alias keys must be unique")
    return tuple(pairs)


class BGatewayGenerationAdapter:
    """FR-D-03: explicit conversion between D's neutral port and B's gateway."""

    def __init__(self, *, gateway: Any) -> None:
        self._gateway = gateway

    def call(self, request: GenerationCallRequest) -> GenerationCallResult:
        """Send one approved request to B and convert its result explicitly."""
        from papertrace.retrieval import gateway as b_gateway

        policy = b_gateway.GenerationPolicy(
            provider=request.policy.provider,
            model=request.policy.model,
            max_input_tokens=request.policy.max_input_tokens,
            compress_at_tokens=request.policy.compress_at_tokens,
            max_output_tokens=request.policy.max_output_tokens,
            max_sources=request.policy.max_sources,
            get_evidence_if_no_contexts=request.policy.get_evidence_if_no_contexts,
            pre_prompt=request.policy.pre_prompt,
            post_prompt=request.policy.post_prompt,
            autonomous_agent=request.policy.autonomous_agent,
        )
        b_request = b_gateway.GenerationRequest(
            snapshot=request.snapshot,
            question=request.question_text,
            approved_evidence=request.approved_evidence,
            selected_evidence_ids=request.selected_evidence_ids,
            policy=policy,
            review_revision=request.review_revision,
            review_digest=request.review_digest,
        )
        result: object = self._gateway.generate(b_request)
        return self._convert(result, b_gateway)

    @staticmethod
    def _convert(result: object, b_gateway: Any) -> GenerationCallResult:
        """Validate the real B runtime type/fields, then build D's typed result."""
        result_type = b_gateway.GenerationResult
        status_type = b_gateway.GenerationStatus
        if not isinstance(result, result_type):
            raise GenerationResultShapeError(
                "gateway did not return a real B GenerationResult"
            )
        b_result = cast(Any, result)
        status = b_result.status
        if not isinstance(status, status_type):
            raise GenerationResultShapeError(
                "generation status is not a real B GenerationStatus member"
            )
        raw_output = b_result.raw_output
        if not isinstance(raw_output, str):
            raise GenerationResultShapeError("raw_output must be a string")
        sent = _text_sequence(b_result.sent_evidence_ids, name="sent_evidence_ids")
        unknown = _text_sequence(
            b_result.unknown_citation_keys, name="unknown_citation_keys"
        )
        ambiguous = _text_sequence(
            b_result.ambiguous_citation_keys, name="ambiguous_citation_keys"
        )
        aliases = _alias_pairs(b_result.citation_aliases)
        refusal_reason = b_result.refusal_reason
        if refusal_reason is not None and (
            not isinstance(refusal_reason, str) or not refusal_reason.strip()
        ):
            raise GenerationResultShapeError(
                "refusal_reason must be a nonblank string or None"
            )
        accounting = _accounting(getattr(b_result, "accounting", None))

        invalid_status = getattr(status_type, "INVALID_SENT_EVIDENCE", None)
        if not isinstance(invalid_status, status_type):
            invalid_status = None
        if invalid_status is not None and status is invalid_status:
            if sent or aliases:
                raise GenerationResultShapeError(
                    "INVALID_SENT_EVIDENCE must report empty sent/aliases"
                )
            if not hasattr(b_result, "invalid_sent_evidence_ids"):
                raise GenerationResultShapeError(
                    "INVALID_SENT_EVIDENCE requires invalid_sent_evidence_ids"
                )
            invalid_ids = _text_sequence(
                b_result.invalid_sent_evidence_ids,
                name="invalid_sent_evidence_ids",
            )
            return GenerationCallResult(
                status="REFUSED",
                raw_output=raw_output,
                sent_evidence_ids=(),
                citation_aliases=(),
                unknown_citation_keys=unknown,
                ambiguous_citation_keys=ambiguous,
                refusal_reason="INVALID_SENT_EVIDENCE",
                invalid_sent_evidence_ids=invalid_ids,
                accounting=accounting,
            )

        mapped_status: Literal["REFUSED", "SUCCESS", "AMBIGUOUS_CITATIONS"]
        if status is status_type.REFUSED:
            mapped_status = "REFUSED"
        elif status is status_type.SUCCESS:
            mapped_status = "SUCCESS"
        elif status is status_type.AMBIGUOUS_CITATIONS:
            mapped_status = "AMBIGUOUS_CITATIONS"
        else:
            raise GenerationResultShapeError("unknown B generation status")

        # A fixed B16 shape lacks this field; it defaults to empty only here,
        # for ordinary statuses. The invalid-sent branch above requires it.
        invalid_ids = _text_sequence(
            getattr(b_result, "invalid_sent_evidence_ids", ()),
            name="invalid_sent_evidence_ids",
        )
        return GenerationCallResult(
            status=mapped_status,
            raw_output=raw_output,
            sent_evidence_ids=sent,
            citation_aliases=aliases,
            unknown_citation_keys=unknown,
            ambiguous_citation_keys=ambiguous,
            refusal_reason=refusal_reason,
            invalid_sent_evidence_ids=invalid_ids,
            accounting=accounting,
        )
