"""Standalone Module D answer panel: display state and command surface.

Traceability: FR-D-01, FR-D-02, FR-D-03, INV-01, INV-03, INV-04. The panel keeps
only the last display scope and the last displayed view in memory. It asks
``AnswerGenerationService`` for one controlled generation on an explicit
Generate request and asks ``ReleaseGate`` only about a validated ``draft``. It
never computes an approved set, rewrites a digest, converts a result into
``accepted``, persists anything or publishes; the UI port carries no publication
command. The display scope is UI state, not an authorization token.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from papertrace.answer.generation import (
    AnswerGenerationOutcome,
    AnswerGenerationRequest,
    AnswerGenerationService,
)
from papertrace.answer.release import ReleaseGate
from papertrace.contracts import (
    AnswerDraft,
    EvidenceId,
    QuestionId,
    ReleaseDecision,
    Sha256,
    SnapshotId,
)

_DraftStatus = Literal["draft", "abstained", "failed"]


@dataclass(frozen=True)
class PanelScope:
    """UI display scope: the question, snapshot and review version shown.

    This is display state only. A change of scope makes the previous view
    ineligible to remain visible; it never grants evidence or release authority.
    """

    question_id: QuestionId
    snapshot_id: SnapshotId
    review_revision: int
    review_digest: Sha256


@dataclass(frozen=True)
class PanelView:
    """INV-04: one displayed state, copied from a validated outcome only.

    ``body`` and ``citation_evidence_ids`` come from ``AnswerDraft``, which D
    already empties for a rejected result, so a rejected raw output cannot leak
    into the panel. ``accounting_observed`` records whether D exposed a
    validated accounting value at all; the attempt count is the one D copied
    from B's public result.
    """

    scope: PanelScope
    question_text: str
    draft_status: _DraftStatus | None
    body: str
    citation_evidence_ids: tuple[EvidenceId, ...]
    refusal_reason: str | None
    release_decision: ReleaseDecision | None
    accounting_observed: bool
    observed_answer_model_attempts: int | None


class PanelUI(Protocol):
    """Display surface: render a view and report one explicit Generate request.

    Deliberately no publication method: the panel is a display and command
    surface, and the UI double is not an authorization source.
    """

    def render(self, view: PanelView | None) -> None:
        """Show one view, or the empty panel when there is nothing to show."""
        ...

    def take_generate_request(self) -> bool:
        """Return ``True`` when this render carries an explicit Generate action."""
        ...


class AnswerPanel:
    """FR-D-01/FR-D-03: render and command surface over the real D services."""

    def __init__(
        self,
        *,
        generation: AnswerGenerationService,
        release_gate: ReleaseGate,
        ui: PanelUI,
    ) -> None:
        self._generation = generation
        self._release_gate = release_gate
        self._ui = ui
        self._scope: PanelScope | None = None
        self._view: PanelView | None = None

    def render(
        self, *, request: AnswerGenerationRequest, scope: PanelScope
    ) -> PanelView | None:
        """Render one display state; generation happens only for a request.

        A changed scope discards the stored view, renders nothing and ignores any
        Generate request in that render. An unchanged scope re-renders the stored
        view unless this render carries an explicit Generate request.
        """
        if self._scope is not None and scope != self._scope:
            self._scope = scope
            self._view = None
            self._ui.render(None)
            return None
        self._scope = scope
        if self._ui.take_generate_request():
            self._view = self._generate(request=request, scope=scope)
        elif self._view is None:
            self._ui.render(None)
            return None
        self._ui.render(self._view)
        return self._view

    def _generate(
        self, *, request: AnswerGenerationRequest, scope: PanelScope
    ) -> PanelView:
        """Call the service once and ask the release gate only for a draft."""
        outcome = self._generation.run(request)
        draft = outcome.draft
        release = (
            self._release_gate.check(draft=draft)
            if draft is not None and draft.status == "draft"
            else None
        )
        return _panel_view(
            scope=scope, outcome=outcome, draft=draft, release=release
        )


def _panel_view(
    *,
    scope: PanelScope,
    outcome: AnswerGenerationOutcome,
    draft: AnswerDraft | None,
    release: ReleaseDecision | None,
) -> PanelView:
    """INV-04: copy only validated draft fields and D's accounting diagnostics."""
    accounting = outcome.accounting
    return PanelView(
        scope=scope,
        question_text=outcome.question_text,
        draft_status=None if draft is None else draft.status,
        body="" if draft is None else draft.body,
        citation_evidence_ids=() if draft is None else draft.citation_evidence_ids,
        refusal_reason=None if draft is None else draft.refusal_reason,
        release_decision=release,
        accounting_observed=accounting is not None,
        observed_answer_model_attempts=(
            None if accounting is None else accounting.answer_model_attempts
        ),
    )
