# Module D generation accounting test proposal

Status: local test preparation with supervisor verification. Implementation and
independent approval of the test commit are pending.

The tests pin the accounting carried from the public B result into D's neutral
`GenerationCallResult`. The fields are the configured `provider`, configured
`model`, and B-observed `answer_model_attempts`. The count describes entries into
B's answer-model boundary. The number of calls through D's gateway spy is measured
separately. The accounting is diagnostic. Citation, evidence and publication
rules continue to apply independently.

## Test cases

| Case | Required observation |
| --- | --- |
| Successful call | The draft retains valid citations. One gateway call can report one or two model attempts. Provider, model and attempts match the B result. |
| Unknown count | The accounting object is present and its count is `None`. |
| Absent accounting | A post-call D result has an accounting field with value `None`. |
| B preflight refusal | The model factory stays unused while the B result carries an explicit count of `0`. D retains it and maps the refusal to a failed draft. |
| D abstention | No approved IDs means no gateway call and no per-call result. |
| Gateway exception | The same exception and its original cause are visible to the caller after exactly one gateway call. |
| Unknown citation | A B success containing `(b999)` produces a failed D draft and retains the unknown key. A separate test checks that accounting survives the failure. |
| Invalid sent evidence | D keeps invalid IDs for diagnosis and returns a failed draft. Sent IDs and citation aliases stay empty. A separate test checks that the unknown attempt count survives. |

The fixture obtains a real frozen `GenerationResult` and nested accounting from
B's public `Gateway.generate` on an empty approved set with a model factory that
fails on entry. It uses `dataclasses.replace` on those objects to create other
synthetic inputs, including the two-attempt case. The reported provider and model
differ from D's request values to detect reconstruction from the request.
`BGatewayGenerationAdapter` processes the real B result class and enum values.
The inherited D projection and the fake gateway use only inline synthetic data.

The exception test exercises D's existing propagation behavior. Reading attempt
counts from real B exceptions depends on a public typed error interface. Provider
request IDs, actual tokens and fees can be handled in a separate slice.

## Offline verification on November 23, 2026 HKT

The isolated verification snapshot used approved D test base
`5709a962618907c3cd73a4490e137235cd3e1cd5`, the local D generation candidate,
and the B retrieval package from `a9440e6767e9ba90642dbe5cf2bb46a526125540`.
The project interpreter was already installed. A separate archive of the D test
base was used for collection without the local D or B packages.

| Check | Result |
| --- | --- |
| New file collection on the test base | Exit 0. 11 collected. |
| Full offline collection on the verification snapshot | Exit 0. 585 collected. |
| New file in the verification snapshot | Exit 1. 7 failed and 4 passed. |
| Existing D slice 1 and token tests | Exit 0. 56 passed. |
| Ruff on the new file | Exit 0. All checks passed. |
| Full offline suite | Exit 1. 39 failed, 544 passed, 2 skipped. |
| Same snapshot excluding the new file | Exit 1. 32 failed, 540 passed, 2 skipped. |

All seven new failures reach the existing D adapter and fail at the missing D
`accounting` field. Both guard controls, abstention and exception propagation
pass. The two full-run failure node lists differ by exactly those seven cases.
The 32 common failures comprise 29 release tests without the release implementation
in this snapshot and three existing bridge tests blocked by missing `lmi`.
The results cover the reported accounting behavior in the fake-gateway scenarios.
Real product model calls, end-to-end public page integration, release verification
with its implementation, upstream regression and GitHub Actions remain unverified.

## AI use and handoff

The supervisor approved this two-file test preparation in chat. OpenCode desktop
API attempts to use the configured D Build role and a read-only drafting fallback
returned `Agent not found` and produced no draft. Codex wrote the tests and design,
corrected a draft field name after the first verification, and reran the tests.
The private archive records the exact prompt, delivery receipts, session outcomes
and verification output. The configured OpenCode model label was
`deepseek/deepseek-flash` with variant `max`. No product model was called in these
checks. After the test proposal is published, an independent student must approve
its exact commit before D implements the accounting transfer.
