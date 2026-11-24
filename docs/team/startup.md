# Startup command page

> **The only entry is [`TEAM_START_HERE.md`](../../TEAM_START_HERE.md).** This page keeps only the clone and environment initialization commands; it is not a second onboarding and does not replace the module Plan/approval.

## Joining the repository

The PaperTrace team repository is private. First ask the repository owner to invite your GitHub account; after accepting the invitation:

```sh
git clone https://github.com/537Lab/PaperTrace.git
cd PaperTrace
```

While the current main has not yet adopted PR #1, do not start business code from the old main. First claim a module/work on the Plan according to [the current stage of the team entry](../../TEAM_START_HERE.md#0-what-can-be-done-now-and-the-single-adoption-step); once the maintainer has completed the reviewed adoption, create separate test branches from the latest main. If you only need to prepare ahead of time, you may select the reviewed `fix/development-unblock` in GitHub Desktop and create a personal `plan/<module>-<name>` branch; this is not authorization to modify the shared fix branch directly.

Install Python 3.14 and the official `uv`. If a usable `.venv` already exists, skip creating the environment and only sync the lock file as needed.

## Initializing the offline environment

macOS / Linux:

```sh
uv venv .venv --python 3.14
uv pip sync --python .venv/bin/python requirements-init.lock
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
```

Windows PowerShell:

```powershell
uv venv .venv --python 3.14
uv pip sync --python .venv\Scripts\python.exe requirements-init.lock
.venv\Scripts\python.exe -m pytest -c papertrace.pytest.ini test/offline
```

This is the initialization/shared-contract environment; `requirements-init.lock` does not mean PaperQA2, Streamlit or the business parsers are installed. Judge command results from the real terminal and [`docs/ci/gates.md`](../ci/gates.md); do not take the example output as a local pass. Do not use a root `uv sync` to install all upstream extras, and do not run the upstream `tests/` in place of the team offline suite.

## Follow-up actions

1. Go back to the [single team entry](../../TEAM_START_HERE.md), claim one module and enter the Plan following the root `AGENTS.md` / `Prompt.md`.
2. The Plan lists the positive/negative tests, fake ports, module-relative path scope and tool/network/dependency needs; the supervising student approves the plan and a non-implementer approves the tests beforehand, and once the scope is confirmed for this round you Build without per-item approval of routine edits and offline commands.
3. B/D's PaperQA2 business dependencies and the real offline adapter need a separate plan/licence review; provider/model, data, attempt counts, retries, cost and deadline need a separate live approval. A/C/D/E can work in parallel on synthetic fixtures/fakes without waiting for a real model.
4. For OpenCode version/configuration see [`docs/tooling/opencode-setup.md`](../tooling/opencode-setup.md); the PaperQA2 smoke command and actual run receipts follow the runbook merged by the lead. B/D's current candidate runtime dependencies are in [`requirements-runtime.in`](../../requirements-runtime.in) and [`requirements-runtime.lock`](../../requirements-runtime.lock); listing them alone does not prove installation/integration passed. Licence and live conditions are in [`docs/licenses/license-review.md`](../licenses/license-review.md) and [`test/live/README.md`](../../test/live/README.md). Configuration/scripts existing does not mean the tool passes end to end, the student has supervised a Build, or real-model semantics passed.

`.opencode/rules.md` is the course-required human-only rule; coding agents must not modify it to approve themselves. The default provider makes no model calls; credentials are injected only by the student, through a controlled method, into an approved runtime environment, and are never written into the repository or chat. All six course gates remain in force; live status is in [`docs/ci/gates.md`](../ci/gates.md).
