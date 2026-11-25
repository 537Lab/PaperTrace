"""Standalone Streamlit preview for the Module D answer panel.

Traceability: FR-D-01, FR-D-03, INV-01, INV-03, INV-04. This is a synthetic,
offline preview: a fixed synthetic corpus, a fixed synthetic review projection
and a deterministic counting double at D's generation port, driven through the
real ``AnswerGenerationService`` and ``ReleaseGate``. It makes no product model,
SDK, HTTP or PaperQA2 call, writes nothing and publishes nothing.

Streamlit is resolved through :func:`_streamlit` at call time only, so importing
this module never requires the Streamlit runtime or a Streamlit type stub. The
preview keeps one panel per Streamlit session and that panel retains only the
current scope and the current view.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import TYPE_CHECKING, Any, cast

from papertrace.answer.generation import (
    AnswerGenerationRequest,
    AnswerGenerationService,
    GenerationAccounting,
    GenerationCallRequest,
    GenerationCallResult,
    GenerationPolicySpec,
)
from papertrace.answer.model import AnswerRequest
from papertrace.answer.release import ReleaseGate
from papertrace.answer.view import AnswerPanel, PanelScope, PanelUI, PanelView
from papertrace.contracts import (
    CorpusSnapshot,
    DocumentVersion,
    EvidenceRecord,
    SourceLocator,
)

QUESTION_ID = "q-synthetic-1"
ANSWER_ID = "ans-synthetic-1"
QUESTION_TEXT = "What does the synthetic resonance cell store?"
ANSWER_ALIAS = "b1"
EXPECTED_ANSWER = (
    "The synthetic resonance cell stores 12 units of daylight energy (b1)."
)
FIXED_TIME = datetime(2026, 11, 25, 0, 0, tzinfo=timezone.utc)
DOCUMENT_ID = "doc-synthetic-a"
CORPUS_NAME = "synthetic-corpus-a.txt"
CORPUS_TEXT = (
    "Synthetic corpus for the PaperTrace answer panel preview.\n"
    "The synthetic resonance cell stores 12 units of daylight energy.\n"
)
PROJECTION_DIGEST = sha256(b"papertrace synthetic panel projection v1").hexdigest()
_STATE_KEY = "papertrace-answer-panel-preview"
_GENERATE_KEY = "papertrace-answer-panel-generate"
_RESUMABLE_FIELDS = (
    "ui",
    "request",
    "scope",
    "panel",
    "projection_port",
    "current_port",
    "generation_port",
)


@dataclass(frozen=True)
class SyntheticProjection:
    """Read-only stand-in for C's projection: one fixed accepted evidence ID."""

    snapshot_id: str
    question_id: str
    revision: int
    digest: str
    accepted_evidence_ids: tuple[str, ...]
    events: tuple[object, ...] = ()


@dataclass
class SyntheticProjectionPort:
    """Read-only projection port over the synthetic projection."""

    projection: SyntheticProjection
    reads: int = 0

    def read_projection(self, question_id: str) -> SyntheticProjection:
        """Return the fixed synthetic projection and count the read."""
        self.reads += 1
        return self.projection


@dataclass
class SyntheticCurrentPort:
    """Read-only captured release bundle over the synthetic corpus."""

    bundle: tuple[CorpusSnapshot, SyntheticProjection, tuple[EvidenceRecord, ...]]
    reads: int = 0

    def read_current(
        self, question_id: str
    ) -> tuple[CorpusSnapshot, SyntheticProjection, tuple[EvidenceRecord, ...]]:
        """Return the fixed captured bundle and count the read."""
        self.reads += 1
        return self.bundle


@dataclass
class SyntheticGenerationPort:
    """Deterministic counting double at D's generation boundary.

    It observes entries into D's port without any provider, SDK or network call
    and never authorizes a draft or release by itself.
    """

    calls: int = 0

    def call(self, request: GenerationCallRequest) -> GenerationCallResult:
        """Return one deterministic B-neutral result for the selected evidence."""
        self.calls += 1
        if not request.selected_evidence_ids:
            return GenerationCallResult(
                status="REFUSED",
                raw_output="",
                sent_evidence_ids=(),
                citation_aliases=(),
                unknown_citation_keys=(),
                ambiguous_citation_keys=(),
                refusal_reason="GENERATION_REFUSED",
            )
        first = request.selected_evidence_ids[0]
        return GenerationCallResult(
            status="SUCCESS",
            raw_output=EXPECTED_ANSWER,
            sent_evidence_ids=(first,),
            citation_aliases=((ANSWER_ALIAS, first),),
            unknown_citation_keys=(),
            ambiguous_citation_keys=(),
            refusal_reason=None,
            accounting=GenerationAccounting(
                provider="synthetic-provider",
                model="synthetic-model",
                answer_model_attempts=1,
            ),
        )


def _streamlit() -> Any:
    """Import Streamlit for local runtime use, or raise :class:`ImportError`.

    Streamlit is an optional local preview convenience and is not a pinned CI
    dependency. Under type checking the module is treated as an ``Any``-typed
    facade so this module never needs a Streamlit stub or ``# type: ignore``; at
    runtime the ordinary explicit :mod:`streamlit` import is performed here.
    """
    if TYPE_CHECKING:
        st: Any = None
    else:
        import streamlit as st

    return st


class StreamlitPanelUI:
    """Minimal Streamlit display adapter; it exposes no publication command.

    Streamlit is resolved through :func:`_streamlit` on every call, never at
    module scope, so a panel retained from an earlier rerun still reaches the
    live session instead of a stale import.
    """

    def take_generate_request(self) -> bool:
        """Report one explicit Generate click for this rerun."""
        st = _streamlit()

        clicked: bool = st.button(
            "Generate answer", type="primary", key=_GENERATE_KEY
        )
        return clicked

    def render(self, view: PanelView | None) -> None:
        """Display one panel view, or the empty panel, without writing state."""
        st = _streamlit()

        if view is None:
            st.info("No validated answer is displayed for the current scope.")
            return
        st.subheader("Question")
        st.write(view.question_text)
        st.caption(
            f"scope: {view.scope.question_id} | {view.scope.snapshot_id} | "
            f"review revision {view.scope.review_revision} | review digest "
            f"{view.scope.review_digest}"
        )
        st.subheader("Draft")
        st.text(f"status: {view.draft_status}")
        if view.body:
            st.write(view.body)
        else:
            st.caption("no draft body is displayed")
        citations = ", ".join(view.citation_evidence_ids) or "(none)"
        st.text(f"canonical citation evidence ids: {citations}")
        st.text(f"refusal reason: {view.refusal_reason or '(none)'}")
        st.subheader("Generation accounting")
        st.text(f"accounting observed: {view.accounting_observed}")
        st.text(
            "observed answer-model attempts: "
            f"{view.observed_answer_model_attempts}"
        )
        st.subheader("Release decision")
        decision = view.release_decision
        if decision is None:
            st.caption(
                "no release decision: only a validated draft is checked and this "
                "panel never publishes"
            )
            return
        st.text(f"status: {decision.status}")
        st.text(f"reason codes: {', '.join(decision.reason_codes) or '(none)'}")
        st.caption(
            "checks: "
            f"snapshot={decision.snapshot_check_passed} "
            f"review={decision.review_check_passed} "
            f"evidence={decision.evidence_check_passed} "
            f"citation={decision.citation_check_passed} "
            f"answer={decision.answer_check_passed}"
        )


@dataclass
class PreviewState:
    """Objects retained for one Streamlit session; no file or database writes."""

    ui: StreamlitPanelUI
    request: AnswerGenerationRequest
    scope: PanelScope
    panel: AnswerPanel
    projection_port: SyntheticProjectionPort
    current_port: SyntheticCurrentPort
    generation_port: SyntheticGenerationPort


def synthetic_corpus() -> CorpusSnapshot:
    """Build one fixed synthetic corpus snapshot over a single document."""
    document = DocumentVersion(
        schema_version=1,
        document_id=DOCUMENT_ID,
        version_sha256=sha256(CORPUS_TEXT.encode("utf-8")).hexdigest(),
        title="Synthetic corpus A",
        source_name=CORPUS_NAME,
        status="ready",
    )
    return CorpusSnapshot(
        schema_version=1, documents=(document,), created_at=FIXED_TIME
    )


def synthetic_evidence(snapshot: CorpusSnapshot) -> EvidenceRecord:
    """Build one exact synthetic excerpt with matching provenance."""
    return EvidenceRecord(
        schema_version=1,
        snapshot_id=snapshot.snapshot_id,
        document_id=DOCUMENT_ID,
        version_sha256=snapshot.documents[0].version_sha256,
        locator=SourceLocator(
            schema_version=1,
            line_start=2,
            line_end=2,
            chunk_id=f"chunk-{DOCUMENT_ID}-2",
            parser_name="papertrace-synthetic",
            parser_version="1",
        ),
        excerpt=CORPUS_TEXT.splitlines()[1],
        retrieved_at=FIXED_TIME,
    )


def synthetic_projection(
    snapshot: CorpusSnapshot, evidence: EvidenceRecord
) -> SyntheticProjection:
    """Build one fixed review projection accepting the synthetic evidence."""
    return SyntheticProjection(
        snapshot_id=snapshot.snapshot_id,
        question_id=QUESTION_ID,
        revision=1,
        digest=PROJECTION_DIGEST,
        accepted_evidence_ids=(evidence.evidence_id,),
    )


def _build_preview_state() -> PreviewState:
    """Wire the synthetic state through the real D services, once per session."""
    snapshot = synthetic_corpus()
    evidence = synthetic_evidence(snapshot)
    projection = synthetic_projection(snapshot, evidence)
    projection_port = SyntheticProjectionPort(projection=projection)
    current_port = SyntheticCurrentPort(bundle=(snapshot, projection, (evidence,)))
    generation_port = SyntheticGenerationPort()
    ui = StreamlitPanelUI()
    request = AnswerGenerationRequest(
        base=AnswerRequest(
            snapshot=snapshot,
            question_id=QUESTION_ID,
            answer_id=ANSWER_ID,
            requested_at=FIXED_TIME,
            evidence=(evidence,),
        ),
        question_text=QUESTION_TEXT,
        selected_evidence_ids=(evidence.evidence_id,),
        policy=GenerationPolicySpec(
            provider="synthetic-provider", model="synthetic-model"
        ),
    )
    scope = PanelScope(
        question_id=QUESTION_ID,
        snapshot_id=snapshot.snapshot_id,
        review_revision=projection.revision,
        review_digest=projection.digest,
    )
    panel = AnswerPanel(
        generation=AnswerGenerationService(
            projections=projection_port, generation=generation_port
        ),
        release_gate=ReleaseGate(current=current_port, clock=lambda: FIXED_TIME),
        ui=ui,
    )
    return PreviewState(
        ui=ui,
        request=request,
        scope=scope,
        panel=panel,
        projection_port=projection_port,
        current_port=current_port,
        generation_port=generation_port,
    )


def _resumable_preview_state(value: object) -> bool:
    """Recognise the retained state across Streamlit script re-execution.

    Streamlit re-executes this module on every rerun, so ``PreviewState`` is a
    new class object each run and an ``isinstance`` check would reject the
    object a previous run stored. The stored value is identified by the display
    fields it must carry instead, and it lives only in ``st.session_state``.
    """
    if isinstance(value, PreviewState):
        return True
    return value is not None and all(
        hasattr(value, name) for name in _RESUMABLE_FIELDS
    )


def _preview_state(streamlit_module: Any) -> PreviewState:
    """Return this session's retained state, building it on the first rerun."""
    stored = streamlit_module.session_state.get(_STATE_KEY)
    if _resumable_preview_state(stored):
        # An earlier rerun's PreviewState instance: same fields, different class
        # object, and still the only retained scope and view for this session.
        return cast(PreviewState, stored)
    state = _build_preview_state()
    streamlit_module.session_state[_STATE_KEY] = state
    return state


def render_preview(
    *,
    ui: PanelUI,
    generation: AnswerGenerationService,
    release_gate: ReleaseGate,
    request: AnswerGenerationRequest,
    scope: PanelScope,
) -> PanelView | None:
    """Drive one panel render and return the displayed view.

    This helper performs a single render over the supplied services. Callers
    that need the scope/view retained across reruns keep one ``AnswerPanel``
    instance themselves, as the standalone preview does.
    """
    panel = AnswerPanel(generation=generation, release_gate=release_gate, ui=ui)
    return panel.render(request=request, scope=scope)


def main() -> None:
    """Standalone Streamlit entrypoint; imports Streamlit at call time only."""
    st = _streamlit()

    st.set_page_config(page_title="PaperTrace answer panel preview", layout="wide")
    st.title("PaperTrace answer panel preview")
    st.caption(
        "Synthetic corpus, synthetic review projection and a deterministic "
        "generation double. No product model call, no publication, no persistence."
    )
    state = _preview_state(st)
    state.panel.render(request=state.request, scope=state.scope)
    st.divider()
    st.caption(
        "generation-boundary calls: "
        f"{state.generation_port.calls} | projection reads: "
        f"{state.projection_port.reads} | captured-bundle reads: "
        f"{state.current_port.reads}"
    )


if __name__ == "__main__":
    main()
