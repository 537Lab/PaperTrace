# E metadata validation boundary review tests

Stage: test preparation only. Independent approval of the new precise PR8 head
is required before source repair. PR18 a7f2fb458ce08079edc78065de00f7fdb79d3b13
remains open and unmerged. Existing 75 tests from approved 9b6629b are unchanged.

The reviewer reproduced nested sensitive metadata bypass and post-construction
metadata pollution reaching storage. ConfigDict(frozen=True) does not deeply
freeze dict/list values. Rejecting a polluted file on later load is too late.

Append six initial-validation negatives covering sensitive keys and absolute
paths in nested list/tuple/mapping combinations. Plain synthetic strings are
not inherently secrets; tests use forbidden keys or actual synthetic absolute
paths. Add three post-construction mutation cases with an injected writer that
must never be reached, a real-writer no-secret-on-disk case, an external alias
mutation case allowing defensive copying or pre-write rejection, and two safe
nested metadata persistence controls. Preserve prior history bytes and IDs.

After independent approval, proposed implementation scope is only E record.py
and store.py: recursively inspect every Mapping/list/tuple container, then
serialize once and validate those exact bytes before any persistence writer is
called. Persist the exact validated bytes, not a second serialization of a
potentially changed object. Do not rely solely on model_validate(existing_model),
do not mutate old history, and do not replace runtime validation with UI checks.
No contract, other-module, CI, dependency or protected-rule change is proposed.

Development uses actual OpenCode session ses_df98a9403ffez3WmrShwwGU8oX,
papertrace-build-E, configured cityucs/CS5351/DeepSeek-V4-Flash. Codex supervises,
executes validation and identifies harness defects before publication. Initial
test drafts had inappropriate plain-string negative data and positive cases
using the rejection sentinel writer; these were corrected, not counted as
production defects. A denied shell discovery attempt was not executed.

Parallel local integration preparation: Team/E-synthetic-handoff.py and
E-handoff-checklist-20261123.md exercise E with explicitly synthetic data. Three
cases (draft/blocked, abstained/blocked, failed/blocked) passed save, reopen,
default JSON/Markdown export, list and superseded-byte-preservation checks.
This does not run actual C/D adapters, generation, provider calls or permission
issuance, and does not establish the metadata defects are repaired.

## Final targeted verification

88 E cases: 79 pass, nine behavioral RED, zero errors/skips. Of 13 additions,
nine expose the defects and four pass as safe-data or existing-rejection controls.
All original 75 pass unchanged. Four RED reach the sentinel writer and fail
explicitly, proving unsafe data reached the persistence boundary; five RED fail
because expected ValueError was not raised. Configured test Ruff passes.
JUnit and full output: Team/E-metadata-red.xml and .txt. Complete offline results
are retained separately as Team/E-metadata-full-offline.txt. No source repair
has occurred, and no old approval is reused for these new cases.
