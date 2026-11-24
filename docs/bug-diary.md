# Bug diary (D4)

There is currently no PaperTrace business bug that can be claimed as reproduced and fixed, because the five modules are not yet developed. The genuine output of the contract RED/GREEN runs is stored in `artifacts/verification/`; those are not production incidents.

## ENV-001: the generic extractor fails on the course PDFs
- Symptom: read_file reports 0 pages/no text; it is not that the course material does not exist.
- Reproduction: the generic extractor fails on the two specified original files; pypdf actually reads 10/27 pages respectively.
- Category/root cause: environment compatibility; the PDFs have xref and duplicate-dictionary-entry warnings; the absence of content in the original cannot be inferred from a single extraction tool.
- Handling: use the existing pypdf for read-only extraction; keep the original bytes and SHA256, and do not modify the originals.
- Invariant gap: source verification cannot be equated with one particular extractor succeeding; this is unrelated to execution of the product INV.
- Status: material reading for this round is restored; no claim is made that the PDF format was fixed.

## CONTRACT-001: the initial empty review state cannot be serialized
- Symptom/reproduction: when the real ledger has no human event yet, revision=0; initially AnswerDraft/ReleaseDecision accepted only >=1, so a legitimate abstention/blocking was rejected too.
- Category/root cause: the shared data boundary missed the initial state; it is not a model failure or a business release incident that occurred.
- Fix: shared ReviewRevision allows a strict integer >=0; draft/released still require non-zero. ReviewDecision event revision still starts at 1.
- Invariants exposed: INV-01/03 must not fabricate human review events in order to serialize. Independent negative tests and legitimate controls were added, and the genuine RED and GREEN are stored in artifacts/verification; both Schemas and the C/D charters were synchronized.
- Status: 170 offline tests pass; the ledger and the release-time business code are not yet developed.

## UNBLOCK-001: development/gate deadlock (an engineering problem, not student business)
Measured and fixed the all-provider denial, the "tests cannot be generated before tests are approved" deadlock, the permanently BLOCKED entry, and full-run omissions/timeouts/marker bypass; each category was RED before GREEN. A genuine OpenCode test-preparation run once wrote to a non-owned test path, was correctly refused, and switched to test_library; the nested fixture uses an explicit pytest.ini to avoid inheriting the upstream configuration. Real build metadata from SCM/egg-info receives only a narrow exemption, and adding upstream source still FAILs.

## UNBLOCK-002: the full upstream regression still does not pass
The fixed uv.lock was actually installed; 377 base/current nodes match, the first index test attempted an API call under the default network ban and was refused by the socket, full execution has genuine failures/timeouts, and 9 live items await authorization. Keep the FAIL, the original tests and the manifest; do not unlock the network, use a private key, or use fake results. The 250 team offline tests and 1 runtime test passing do not mean full.

## CLOSEOUT-001: a semantic report wrongly passed and an unrelated configuration wrongly blocked
- Reproduction: recomputed request/report hashes could mask a fixed problem, or a mismatch between the approved body text and the sent ID; changing the runtime lock and refreshing the head record could still use the old environment; pure Ruff/pytest changes were required to go through real model evaluation. All were first observed failing by actual offline negative tests.
- Root cause/fix: self-reported hashes do not verify material provenance, the configuration summary missed runtime inputs, and triggering looked only at file names. Changed to an exact request contract, the v3 runtime lock and actual interpreter version verification, and production dependency closure content determination; kept conservative triggering for unknown/malformed configuration and coverage of B/D/upstream model code.
- Regression: all 299 team offline tests, 0 skip; 1 PaperQA2 offline integration item; Ruff/mypy/static/schema pass. This is not a formal business implementation, genuine human pre-approval, or evidence of real model quality; the original full failures are unchanged. Evidence for this round is in artifacts/verification/closeout-semantic.json.

## FINAL-CI-001: push incorrectly reuses the open-PR approval entry
- Reproduction: the original workflow listened to both push and PR, but push passes an empty PR number, so an applicable code change genuinely returned missing-pr-number; even with a number added, the original implementation accepted only open PRs and could not look back at merged evidence.
- Fix: an explicit event contract; PRs still use base, while main-origin items are bound one by one to the native merged PR and the same tree, then the original test/semantic evidence is replayed, and the quality check acts on the actual new main. Reverts/wrong SHAs/unapproved tests/pushes without a PR are refused; positive and negative tests were also added for native list/detail field differences and for closing a RED proposal after merge.
- Acceptance: kept the 299 items and added 33 event checks, 332 offline in total, 0 skip; the original PaperQA2 smoke of 1 and Ruff/mypy pass, and an independent scope-limited re-run of 92 items passed with matching file SHAs. The real main is not merged, so simulated events must not be described as completed verification on the live main. First adoption still requires genuine human review and the course acceptance boundary; the original full failures are retained.

Subsequent significant bugs must record the symptom, minimal reproduction, root-cause evidence, fix diff and regression test; assumptions must not be written as reproductions.
