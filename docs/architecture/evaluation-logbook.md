# Architecture evidence log

> This log separates **facts read, design inferences, planned acceptance and real execution**. It does not replace the D5 raw OpenCode session, student interventions/approvals, per-PR memos or the D6 contribution record. Page 5 of the course project lists the evaluation logbook as optional; it is provided this round for auditability, and no claim is made that a complete run experiment has been done. [1]

## 1. Actual material and results this round

| Evidence ID | Actual work / checkable location | Permitted conclusion | Must not be upgraded to |
|---|---|---|---|
| EV-ARCH-01 | Read `project.txt` (PDF pages 1–10) and `introduction.txt` (PDF pages 1–27) of the course in full; see source-register for the source summary | The architecture and open points rest on the course text, and citations use PDF page numbers | Canvas updates were not checked live; no exact deadline or reuse-permission guarantee is given |
| EV-ARCH-02 | Read-only `git rev-parse HEAD` returned `c692d0dfeac4a0296599f7fe21a253a58b7ac12a`; at that time `git diff --name-only <baseline> -- src/paperqa packages tests` produced no output | No difference from the baseline was seen in the core/packages/upstream tests when architecture drafting began | Does not represent the final diff of the whole initialization, dependency compatibility or model runs |
| EV-ARCH-03 | Read the fixed `docs.py:156–721`, `types.py:155–526`, the specified sections of `settings.py`, `core.py:227–400`, `readers.py:92–143`, the two SearchIndex loaders and the Agent control chain directly | Baseline call sites, Context identity, the sent gap, implicit calls and the pickle scope can be located | Not a local PaperQA2 integration test, an exploit or a full supply-chain audit |
| EV-ARCH-04 | Read the unpacked audit Markdown: 01–06 plus the final scope/technical review; the audit originals were not modified | Reuses the existing analysis input and keeps the lessons on candidates/scope/evidence level | The audit's historical narrow probes/upstream CI are not new runs of this round |
| EV-ARCH-05 | Read the shared contracts and registry plus the existing contract/gate test definitions, aligning fields, INVs and requirement IDs | The semantics of the architecture and the current initialization contracts can be checked; the goal of full trace coverage is clear | Test definitions existing does not mean they have run or that A–E are implemented |
| EV-ARCH-06 | The root canonical, the pointing page and the architecture Markdown in this directory were created by this task; the file tool returned verified | The documents are genuinely on disk, not merely planned | Document creation is not student approval, enforced OpenCode permissions or remote gates |

Source and audit citations: [source-register.md](source-register.md). This round did not import/run `paperqa`, did not run model/embedding/metadata APIs, did not read credentials, did not modify the original course/audit files and did not git commit/push; this is the action scope of the architecture subtask and does not pretend to be a global network audit of other parallel tasks.

## 2. Design conclusions and evidence gaps

| Conclusion | Current level | Next acceptance / stop condition |
|---|---|---|
| The five-module thin adapter suits the current scope better than a rewrite/multi-user service | Qualitative design inference; not measured | Student reviews the ADR; module plan/tests approved in advance |
| Human review ledger + source hash + freshness can constrain the defined release boundary | Testable design, awaiting implementation | Runtime positive and negative cases for T-INV-01…08, not just Pydantic |
| 12k/9k/2k can serve as engineering defaults | Unapproved proposal; not a measured optimum | Fixed tokenizer boundary/reinjection; real verification of the model window/output parameters |
| The B gateway covers factory/SDK/HTTP and every represented call | Design contract; internals of external dependencies not verified | Spy on each item of the call list; keep that path closed if a bypass is found |
| Local single-writer file storage is usable for the MVP | Design assumption | Half-write/lock/race/recovery tests; if it fails, narrow it or reopen the persistence ADR |
| History is locatable and anonymized export is safe by default | Design contract | Original hash/locator/export redaction and license tests; paper licenses cannot be guessed |
| The coding-role path table can be expressed in the OpenCode2 configuration | Controller tool fact + plan constraint; this subtask ran no permission probes | Actual version/schema/loading and allow/deny receipts, including the shell bypass |

## 3. Real model and performance results: no fake data

| Item | Status in this document | Why PASS cannot be written |
|---|---|---|
| Full PaperQA2 dependency install/real offline integration of the low-level API | Not executed by this architecture subtask | Source support for Python 3.14 does not mean all native/parser runs are compatible |
| Latency/token/cost improvement of the new vs old approach | **Not measured** | No real comparison on the same data/model/hardware, so no percentage is filled in |
| PERF-01 100 contract round trips ≤2 seconds | Follows the controller's real benchmark receipt; not run here | Not inferred from the design threshold or the existence of a unit test, and not extrapolated to RAG speed |
| Real embedding/summary/answer and fixed semantic eval | **Not authorized/not executed by this subtask** | Requires approval of provider/model/data/amount and request count; a stub tests policy only |
| D5 raw OpenCode supervised session and student interventions | **Not produced by this subtask** | A student session or approval cannot be synthesized from an architecture drafting log |
| All six GitHub gates blocking remotely and branch protection | **Not verified by this subtask** | A local script or YAML cannot replace required checks and failing-PR evidence |

## 4. Rules for appending evidence

A new real verification entry must contain: execution scope, command/tool, source commit or file version, fixture/eval version, model/replay identity, environment, real output location, failures/skip/unknown, the conclusion and the scope it must not be extrapolated to. Model-related entries also need the actual provider/model, attempt/usage/finish reason and whether the cost is known; approval-related entries need a trusted human-review source and must not self-fill approved.

Document validation, contract tests, upstream offline integration, real semantic eval and remote gates each have their own evidence chain and do not substitute for each other. Re-verify against the new version after a revision, keep old failures, and do not rewrite a plan into the past tense.

## 5. Record of this document validation

One necessary documentation consistency check was executed: all 13 Markdown files are non-empty; the relative-link and fence checks report no errors; 27 registry requirements correspond to 27 trace rows; INV-01 to 08 are complete; all 13 source numbers resolve and the Sources mapping is consistent; no private absolute paths were found. The read-only Git check returns the fixed baseline, and the changed paths of `src/paperqa`, `packages` and the original `tests` relative to the baseline are empty. The check process exit code was 0 with errors empty. This result covers only documents/trace/citations/links and the frozen paths; it does not mean the application runs, model evaluation, actual OpenCode permissions or remote gates have passed.

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf (local text extraction, 10 pages)
