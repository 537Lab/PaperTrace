# Module D | Answers from approved evidence and the deterministic release gate

> **Owner D:** end-to-end responsibility for the answer feature, call authorization, context/budget, citation checks, the release gate, their own view, supervised development, tests and PRs. B maintains the only PaperQA2 low-level adapter; D still owns answer and release policy.
>
> Always start from the [team start entry](../../TEAM_START_HERE.md); shared models/handoffs follow [`integration-contract.md`](integration-contract.md) and `src/papertrace/contracts.py`.

## User outcome and responsibilities

The researcher requests an answer for a given question, library snapshot and C's human-reviewed revision. D computes `approved` from the real ledger projection, sets the budget/order/trimming and records the `sent` of the final payload, then parses `cited` from the raw output returned by B; the answer becomes a release candidate only when both freshness and the deterministic release gate pass. With no approved evidence D explains the abstention, but **does not call a model to generate the abstention**.

| Set | Definition and authority |
|---|---|
| `approved` | The full set of human-approved accepted evidence valid for the given question/snapshot/revision; a trusted projection from C, not taken from a model or the UI. |
| `sent` | The evidence that actually entered this round's request after trimming and serialization; must be reconstructible from the final payload/call record. |
| `cited` | The real citations reliably parsed from the raw output and mapped; unknown keys must not be silently dropped by the formatter. |

Hard constraint: `cited ⊆ sent ⊆ approved`. A set relation is not proof of semantic support; an answer being cited does not mean a scientific claim has been confirmed by the source text.

## Must and reviewable outcomes

| Requirement/invariant | Required behaviour and acceptance |
|---|---|
| `FR-D-01`, `INV-01/03` | When approved is empty, do not enter B's generation port, the model factory, the SDK or HTTP; the attempt counters at all four layers are zero. Do not build a model first and let upstream abstain, and do not call a model to explain the abstention. |
| `FR-D-02`, `INV-04/05` | Citations may only come from this round's actually sent and still-valid approved evidence; check the snapshot and the review revision/digest at start/return/before commit, and block on any change. Keep the diagnostics for bad citations rather than deleting them and pretending released. |
| `FR-D-03` | The controlled B port performs only the mechanical call on the input D filtered; new session, with automatic evidence addition/pre/post/Agent disabled; raw output, final sent and the citation key mapping are inspectable. D itself does not `import paperqa`. |
| `INV-07`, `COST-01` | Follow the registry's proposed caps of 12,000 input, compaction at 9,000 and 2,000 output; the final count includes template/system messages and fits the approved model window. Re-inject identity/constraints; when over the limit or when no sent remains after trimming, make zero calls. |

The real v1 contracts only allow AnswerDraft `draft/abstained/failed` and ReleaseDecision `released/blocked`; `stale` is a blocked reason/label and must not gain an enum of its own. revision 0 is used only for the contract-permitted abstained/failed and blocked, never to fabricate a review event.

## Boundaries and proposed change scope

- D decides the authorized input, budget/context, prompt version, answer and release; B executes the controlled adapter and provides raw/sent/mapping/call accounting; C provides the human-review projection; A/E and the app orchestration provide approved interfaces for freshness and the final write. D does not write C's ledger, does not call A's private files and does not decide E's history content.
- **Routine module scope (confirmed once at Plan; routine edits/new files inside the scope are not approved one by one):** `src/papertrace/answer/` (pure rules, control service and view), `test/offline/test_answer.py`, `test/fixtures/answer/`. The module prompt, shared contracts, app orchestration/critical sections, CI and dependencies/lock are approved when the scope expands; inside the approved module scope, per-file authorization is not requested again.
- The approved plan may inspect exact `src/paperqa/` source files read-only to verify `aquery`/serialization behaviour; PaperQA2 must not be imported/called directly. Upstream fixes are not ordinary D PRs and go through ADR-002.

## Fake-first development and acceptance without waiting for B

First use a valid snapshot/evidence and a synthetic C ledger, and inject a fake generation port that **records the payload, initialization, SDK/HTTP attempts, the returned raw output and a controllable freshness token**. This path lets D implement and test independently; it needs no real PaperQA2, provider or model. The fake must not merely return a fixed "OK".

Minimum verification: no decision/only AI suggestions/all excluded → zero calls at every layer; one valid accepted → exact sent; approved larger than sent, a citation not sent though approved, excluded/pending/unknown keys are all blocked; unknown citations in the raw output are preserved; automatic evidence addition/pre/post/old sessions do not appear; compaction/trimming boundaries and re-injection; changing snapshot/revision both during generation and before the final save blocks; timeout/truncation/empty answer/bad ledger produce no released; a direct service call enforces the same boundaries. Do not claim faithfulness/relevance PASS without passing the real fixed evaluation.

## D1–D9: module evidence D should leave behind

| Item | Evidence for this module |
|---|---|
| D1 | Set, budget and error fit/test mapping for `FR-D-01/02/03`, `INV-01/03/04/07`. |
| D2 | Sources of the three sets, context/compaction and freshness/commit policy; ADRs for security-critical decisions. |
| D3 | Exact write paths for answer/prompt, the exact upstream read-only list, B's single-import boundary and measured permissions. |
| D4 | Prior approval, payload/attempt spy, citation/race negative tests, team regression, real semantic status and review memo. |
| D5 | The complete original OpenCode session under student supervision and the reasons for the authorization/citation interventions; Hermes initialization is not D5. The count basis awaits student/instructor confirmation. |
| D6 | D's real feature/collaboration contribution and reflection material; identity/ratio filled in by the student. |
| D7 | Local diff/real PR/CI/independent review and remote protection read-back; the earlier 403 did not take effect and must be re-checked. |
| D8 | Answer service/view, synthetic fixtures, payload/race spies, positive/negative/regression and reproducible steps. |
| D9 | The Plan stop, test/plan/path approvals and supervised execution records in the root `Prompt.md`. |

Acceptance requires a non-UI zero-call negative test, real payload observation and final freshness; a schema passing on its own, a hidden UI button or a model reporting success are not proof of release safety.
