# Architecture candidate comparison table

> Status: **qualitative engineering comparison, not a measured ranking; the proposed option awaits student approval.** What this table compares is how to implement the already-fixed PaperTrace topic; it does not re-choose the topic and does not promise any time/token savings.

## 1. Evaluation basis and hard conditions

Pages 3 and 5 of the course project text require real AI, a deterministic boundary, candidate comparison and architecture constraints; pages 6 and 10 require complete governance and verification. Page 25 of the teaching introduction advocates low coupling, clear responsibility, several ADD design rounds and reduced waste, and gives no performance numbers for this project. [1][2]

Hard conditions precede convenience: keep the fixed PaperQA2 baseline; A–E all have real functions; accepted is decided by humans only; zero generation on an empty approved set; three sets + freshness; history is not overwritten; code/data/model permissions are deny-by-default; the 12k context proposal must be enforceable; untrusted pickle is forbidden. If any hard condition cannot be met, “fast to integrate” alone must not win.

## 2. Comparison on the same basis

| Dimension | O1 As-is high-level Agent/CLI + UI | O2 Five-module thin adapter (proposed) | O3 Rewrite/rework the upstream core | O4 Multi-user front end and back end + database service | O5 Index recovery/physical revocation as the main line |
|---|---|---|---|---|---|
| Fixed baseline reuse | Keeps the source code, but the default behavior must be intercepted | Original code frozen, B the only boundary | Heavy modification/replacement, conflicts with this round's constraints | Reusable, but the deployment layer adds a lot | Goes deep into index/lifecycle hot spots, likely to touch the original code |
| Hard ordering human review → generation | Automatic evidence backfill/tool loop needs extra control | D front gate, C ledger, B controlled session direct connection | Possible, but rebuilds existing capability | Possible, and additionally needs multi-person authorization/conflict design | Needs an extra human review/release gate; fixing the cache alone is not enough |
| Empty set, zero factory/HTTP | The factory early in the original aquery must be avoided | D blocks before B; still needs real spies to verify | Designable, high cost | Designable; service startup side effects need extra checking | Still needs an independent D front gate |
| Three sets and freshness | Upstream contexts and sent are not fully equivalent | Custom serializer + raw mapping + final lock | Maintain the whole chain yourself | Needs cross-request/multi-writer concurrency control | Easily expands into multi-index transactions |
| Five-function ownership | Easily degrades into UI wrapping/config tasks | A–E stable contracts, end-to-end responsibility clear | Hot-spot conflicts, task boundaries harder | Headcount may be consumed by deployment/front end | Multiple people editing the same SearchIndex hot spot |
| Deployment/dependency burden | Low, but many implicit calls/indexes | Local Streamlit + files, single writer | High, compatibility and regression burden | High, authentication/service/data migration | Medium-high, native index and multiple stores |
| Offline deterministic acceptance | Partly doable but needs extra truncation bypass | Contracts/outbound spy/clock/source/race clear | Doable but the test surface is large | Needs extra concurrency/network/deployment tests | Fault injection suits it, but native details require real runs |
| Cost and privacy boundary | Default metadata/enrichment/Agent extra paths | Off by default, explicit controlled call list | Requires re-review of every self-built path | Adds network and multi-user secret management | Most reliability can be offline, RAG still needs approval |
| Risk of duplicating upstream work | Much existing capability, cannot be claimed as original | Human review/authorization/traceability are the application increment | High risk of recreating existing RAG | Large UI/service is not the course's main contribution | Several bugs already have public PRs, attribution burden is high |
| Trade-off this term | Not adopted directly | **Proposed, conditional** | Rejected | Deferred | Future option, not merged into the MVP |

The evaluation is not a sum of unargued weighted scores; there are no invented metrics such as “30% faster” or “50% cheaper”. O2's low coupling/testability comes from the boundary design, not from running performance already beating every option.

## 3. How the source affects the trade-offs

| Evidence | Impact on the candidates |
|---|---|
| `docs.py:602–624` constructs the factory first and can backfill evidence automatically; `:626–639,694–711` pre/post extra calls [3] | The high-level flow cannot directly replace the human authorization chain; O2 uses the D gate first, then controlled B |
| `settings.py:1179–1250` selects contexts only by relevance/count [5] | The token cap and sent records must be implemented by the team; the existing serializer is not treated as a hard budget |
| `types.py:304–316,400–402,480–515` ID/used_contexts/format cleaning [4] | New source IDs and raw validation are necessary, to avoid equating a legitimate key with authorization or with a real send |
| `agents/search.py:86–93,242–257` two pickle entry points [7] | This term does not import third-party indexes, rather than migrating all formats; O5's full scheme is estimated separately |
| `agents/main.py:121–124,155–183` index building and outer timeout fallback [8] | The high-level Agent's extra outbound calls are hard to control fully; disabled by default, and the fake-agent name is not used to infer that it is free |
| Main package/optional parser licenses differ [10][11] | Minimal explicit PyPDF text route; extra parsers and paper distribution reviewed separately |

## 4. O2's acceptance conditions and experiment plan

| Decision assumption | Real verification needed | How to converge if it fails |
|---|---|---|
| B can integrate the low-level API without changing upstream | Offline adapter smoke in an isolated environment, explicit model objects, one-to-one raw alias mapping | Narrow the upstream entry point first; if it cannot be covered, reopen the ADR and do not modify the core unilaterally |
| A single gateway covers all calls claimed to be controlled | Factory/SDK/HTTP spies, including ingestion embedding/summary/retry | Keep everything disabled by default, close each path before authorizing, and do not claim the whole chain is safe |
| Single-writer files suit the MVP | Negative tests for crash/half-write/lock conflict/release TOCTOU | Reduce concurrency; re-evaluate a database only if multi-user is genuinely needed |
| 12k/9k/2k suits the chosen model | Offline boundary/reinjection tests with a fixed tokenizer, then protocol acceptance for the approved model | Take a smaller window/reduce data; do not keep releasing after truncating the input |
| Real answers meet the quality requirements | Fixed eval set, human-labeled rubric, receipts from the approved real model; thresholds frozen after the baseline | State that it falls short, adjust the design/evidence, and re-evaluate; do not fabricate a PASS |
| Functional split and role rotation are compatible | Per-module plan/test/PR + real human review of the rotation records | Keep functional ownership and rotate process responsibility; no permanent management post |

Current status: this table contains no dynamic candidate performance comparison and no real model semantic data. The actual results of contracts and basic checks are provided by the controller's execution receipts; course D5, test/plan approval, remote gates and model budget still separately await student confirmation/authorization.

## 5. Decision boundary

Adopting O2 does not mean an ADR that is already accepted. Before student approval only this round's limited initialization may be done; after approval each member must still go through OpenCode to plan first, stop for human review, and only then build. Future reopening conditions and historical options are in [ADR-001](adr/001-architecture.md) and [option-ledger.md](option-ledger.md).

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf (local text extraction, 10 pages)
[2] urn:sha256:16d399f7ca14e0c49dea382cec3893bbee8f589edcaee5131f10fad257d3acb5 — cs5351-2026-2027-introduction.pdf (local text extraction, 27 pages)
[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — fixed baseline src/paperqa/docs.py
[4] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/types.py — fixed baseline src/paperqa/types.py
[5] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/settings.py — fixed baseline src/paperqa/settings.py
[7] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/search.py — fixed baseline src/paperqa/agents/search.py
[8] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/main.py — fixed baseline src/paperqa/agents/main.py
[10] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/pyproject.toml — fixed baseline pyproject.toml
[11] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/packages/paper-qa-pymupdf/pyproject.toml — fixed baseline PyMuPDF subpackage license declaration
