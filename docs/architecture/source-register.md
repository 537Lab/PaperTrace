# Architecture source register

The numbering in this directory uses this round's independent register and does not follow the audit draft's numbering. All source links are pinned to commit `c692d0dfeac4a0296599f7fe21a253a58b7ac12a`. The `urn:sha256` values for the course and the audit are material fingerprints, not download addresses; the fingerprints come from the source manifest that was read, this subtask did not recompute the hash of the original PDF/ZIP, and no private absolute path is recorded in the team files.

| Source | Actually read / direct location | Evidence boundary |
|---|---|---|
| [1] Project text | Authorized extracted full text of `CS5351-2026-2027-project.pdf`, PDF pages 1–10; p3 real AI/deterministic boundary; p4 role rotation; p5 architecture; p6 governance/three-tier verification/D5; p6–7 D6; p9 layout; p10 six gates | A local snapshot of the original text, not live Canvas; the D5 count/baseline reuse and the blueprint location ambiguity await student confirmation |
| [2] Teaching introduction | Authorized extracted full text of `cs5351-2026-2027-introduction.pdf`, PDF pages 1–27; p5/20 OpenCode; p6 evaluation model; p7 Week13; p23 video/secret keys; p25 ADD/low coupling/token | Week13 has no exact date; specifying a tool is not authorization to send models/amounts/data out |
| [3] `src/paperqa/docs.py` | 171–311 ingestion/upfront outbound calls; 340–386 embedding; 437–585 retrieval/summary; 588–721 answer/factory/evidence backfill/pre-post | Static source, not a full run on this machine |
| [4] `src/paperqa/types.py` | 155–235 Text; 238–316 Context identity; 319–433 session/post-hoc metering; 442–526 filtering/citation formatting | A legitimate key is not human authorization; formatting is not semantic proof |
| [5] `src/paperqa/settings.py` | 148–154 automatic evidence backfill; 169–184 parser; 235–275 details/media/defer; 411–421 pre/post; 756–830 default configuration; 915–955 factory; 1179–1250 serializer | top-N/cutoff is not a hard token cap; the model default string has not been approved by this project for calls |
| [6] `src/paperqa/core.py` | 227–400 summary/JSON/Context/partial retry | Having retries does not mean the budget for the whole run or the quality has passed |
| [7] `src/paperqa/agents/search.py` | 63–93 document pickle; 118–145 storage default; 242–274 mapping loader and filecheck | Two loaders; no malicious PoC was executed this round |
| [8] `src/paperqa/agents/main.py` | 91–216 index building, runner, fallback outside the timeout, fake-agent entry | A fake-agent is not a fake model, nor is it free |
| [9] `src/paperqa/readers.py` | 92–143 PDF chunk page ranges | Does not guarantee exact sentence coordinates/bbox |
| [10] `pyproject.toml` | 19–49 version/dependencies; 53–61 license/release information | A Python support declaration is not proof that all dependencies are compatible on this machine |
| [11] PyMuPDF subpackage `pyproject.toml` | 9–12 AGPL declaration; 21–27 dependencies/licenses | The root Apache license does not automatically cover optional packages or papers |
| [12] Audit handover package | Read-only unpacked 01–06 reports plus the final scope/technical review | Audit suggestions/historical narrow probes/upstream CI do not pretend to be new runs of this round |
| [13] `src/paperqa/agents/env.py` | 243–272 initial state clearing Docs; 309–345 tool flow | Not a human review ledger or a complete persistent recovery |

## Label rules

“Confirmed in the source” refers only to the control flow of the fixed source; “test defined” does not mean executed; “monitor to be developed” has no run receipt; the “12k/9k/2k default” is an engineering proposal awaiting approval; `proposed-awaiting-human` is not accepted. All approvals, real OpenCode sessions, real model evaluations and remote protection must keep real evidence and are not fabricated by AI.

## Sources

[1] urn:sha256:6af742d3cbc0973b056a084ba54ff413a5885b1bb4d6a97b0b08b93f64f2ef7e — CS5351-2026-2027-project.pdf (local text extraction, 10 pages)
[2] urn:sha256:16d399f7ca14e0c49dea382cec3893bbee8f589edcaee5131f10fad257d3acb5 — cs5351-2026-2027-introduction.pdf (local text extraction, 27 pages)
[3] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/docs.py — fixed baseline src/paperqa/docs.py
[4] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/types.py — fixed baseline src/paperqa/types.py
[5] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/settings.py — fixed baseline src/paperqa/settings.py
[6] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/core.py — fixed baseline src/paperqa/core.py
[7] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/search.py — fixed baseline src/paperqa/agents/search.py
[8] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/main.py — fixed baseline src/paperqa/agents/main.py
[9] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/readers.py — fixed baseline src/paperqa/readers.py
[10] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/pyproject.toml — fixed baseline pyproject.toml
[11] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/packages/paper-qa-pymupdf/pyproject.toml — fixed baseline PyMuPDF subpackage license declaration
[12] urn:sha256:21f1c516a57e975a284d1d278926fedd9755a6d0036314279663c4074063942a — PaperQA2 audit handover ZIP (Markdown extracted from it only, read-only)
[13] https://github.com/Future-House/paper-qa/blob/c692d0dfeac4a0296599f7fe21a253a58b7ac12a/src/paperqa/agents/env.py — fixed baseline src/paperqa/agents/env.py
