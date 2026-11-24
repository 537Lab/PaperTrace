# OpenCode v2.0.12: restricted development workflow

This guide corresponds to the OpenCode native v2 configuration indicated by the `$schema` in the repository. The permission key is `permissions: [{action, resource, effect}]` together with agent-local lists of the same shape; do not apply the v1 `permission`/`instructions` configuration. The checklist `.opencode/permissions.jsonc` is only a manifest read by the static checks and is not loaded automatically by OpenCode; the engine actually reads `opencode.jsonc`, and project instructions follow OpenCode's discovery mechanism for the root `AGENTS.md`.

## Model and credentials are decided by the student separately

`opencode.jsonc` deliberately sets no `model`, `provider` or `provider.use` deny policy: this configuration neither blocks an approved coding model that the student configures separately nor chooses or calls a model on its own. Students should complete the authorization in OpenCode themselves and confirm the model, the data sent, the cost, the number of calls and retries. Do not write API keys, `.env` files or private auth data into the project, test output or this guide.

The development assistant's coding model and the LLM that the PaperTrace product runtime calls for papers/documents are two different paths. The development assistant's provider configuration grants no product-call permission and does not change the product's human approval/citation/budget governance. Offline verification uses only a local fake OpenAI-compatible endpoint and an explicitly synthetic token; no real provider or paid model was touched.

## Plan → test preparation → GitHub test approval → source Build → Verify

1. In the PaperTrace root, check `.opencode/rules.md`, `AGENTS.md`, `.agent/rules.md` and `Prompt.md`. Running `opencode` directly defaults to `papertrace-plan`; Plan is read-only, outputs a precise plan for a single module and stops.
2. The student reviews and approves the precise plan first. After that, the same module's `papertrace-build-A`…`papertrace-build-E` role generates only that module's standalone tests/, fixtures/ and module design record; writing anything under `src/` is strictly forbidden, even though the native tool permissions allow source paths at that point. Running the approved offline tests shows RED.
3. The test proposal PR may stay open and RED; merging it for approval is not required. Another student who did not take part in the test implementation must genuinely Approve on GitHub, on the PR bound to the specific test commit. Before the real approval, Build must not behaviorally write any of this module's src.
4. After approval, the implementation PR is created from the test head and its description contains the exact field `Test approval PR: #N`; only then does the same module's Build role continue with the source implementation, after which Verify checks it independently. Refusal, silence, a fake review, or merely holding a role/permission grants no authorization.
5. Once the student has confirmed the module scope and the exact common offline commands one time, routine edits within that scope do not need repeated per-file authorization; the independent GitHub approval of the specific test commit is still a required step. Shared contracts, cross-module work, dependencies, paid/cost-incurring calls, safety paths or budget overruns still stop immediately.

Role permissions only define the role/path range a tool can reach; they do not prove a real person's identity or an approval. Not writing src during test preparation is a behavioral rule, not a new role, a machine stage gate, an OS sandbox or an identity service. OpenCode path matching is lexical; preflight can reject symlinks that exist at that moment but cannot prevent later replacement or be claimed as permanent isolation.

Command-line one-shot examples (replace `<approved-provider/model-id>` with the coding model identifier the student has already approved and configured; no credentials are provided):

```sh
opencode run --agent papertrace-plan --model <approved-provider/model-id> \
  "Read Prompt.md and AGENTS.md; list a plan for only the one module I specify, then stop and wait for human review."

# After the plan is approved, proceed only to test preparation; the source Build happens only after the specific test commit is approved on GitHub by another student.
opencode run --agent papertrace-build-A --model <approved-provider/model-id> \
  "Attach the approved plan; generate only A's tests/fixtures/design record, and do not write src."

opencode run --agent papertrace-verify --model <approved-provider/model-id> \
  "Read-only check of the diff and the verification results; point out negative cases, unverified items and limits, and do not approve."
```

These commands do not automatically check a real person's identity or an approval; roles such as `papertrace-build-A` are not an authorization to bypass Human Review either. Do not paste keys or private approval material into shell history. When approval material really must be given to an agent, attach only secret-free references to version numbers/scope/status.

## Static preflight and real engine probes

```sh
# Default: portable, read-only static checks; starts no OpenCode, model or network request.
.venv/bin/python scripts/opencode_support.py

# CI should call this from a trusted base script and explicitly check the target checkout, not the directory the script lives in.
.venv/bin/python scripts/opencode_support.py --root "$TARGET_CHECKOUT"

# macOS optional: read back the OpenCode v2 configuration and query the permission engine; still starts no model or tool.
.venv/bin/python scripts/opencode_support.py --verify-runtime \
  --binary "$HOME/.opencode/bin/opencode" --root "$PWD"
```

`--root PATH` verifies, inside the given checkout, the governance markers/synchronization of `opencode.jsonc`, `.opencode/permissions.jsonc`, `.opencode/rules.md` and `AGENTS.md`, as well as the agent/manifest roles, read/write candidates, protected/sensitive paths, the command allowlist and symlink/traversal. It reads only configuration/rules, does not read environment credentials and starts no model; on failure it prints JSON `status: FAIL` on stdout and exits non-zero. CI can keep the trusted script outside the checkout, for example:

```sh
python "$CI_CONTROL/scripts/opencode_support.py" --root "$TARGET_CHECKOUT"
```

Do not execute the gate script itself from the untrusted target checkout. `--verify-runtime` is a different level: it runs the `/api/config` and `/api/session/.../permission` probes of the actually installed OpenCode and calls no model or file tool; it cannot pass as a tool E2E.

## Reproducible offline tests

```sh
.venv/bin/python -m pytest -c papertrace.pytest.ini -q \
  test/offline/test_opencode_configuration.py

.venv/bin/python -m pytest -c papertrace.pytest.ini -q \
  test/offline/test_opencode_workflow.py

.venv/bin/python -m pytest -c papertrace.pytest.ini -q test/offline
.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
.venv/bin/python -m mypy --config-file mypy.ini src/papertrace
.venv/bin/python scripts/gates.py --gate schema
```

`test_opencode_workflow.py` starts a loopback-only deterministic fake and, in a disposable checkout, actually drives Plan, the same Build role's test-only preparation, the source Build after a simulated test approval, and Verify through OpenCode v2.0.12; the fake tool first changes only tests and observes RED, asserts the source is unchanged, then simulates the approval, and finally verifies that this module's source write succeeds, a cross-module write is rejected, and the tests are GREEN. The test approval target is a simulated fixture, not a real student/GitHub approval, and it does not prove model compliance, identity or a machine gate at the source stage. Native path permissions still allow this module's src; the prohibition on writing src early is a behavioral rule. Path matching is lexical, and the symlink preflight is only a point-in-time check; macOS `sandbox-exec` confines only this verification process. The public JSON replaces personal absolute paths with `<repo>`/`$HOME`; the exact argv is kept only in `.local/unblock/opencode/workflow-commands.json`, and no process environment/keys are written. Without OpenCode/macOS the E2E is skipped; a skip does not equal a pass.
