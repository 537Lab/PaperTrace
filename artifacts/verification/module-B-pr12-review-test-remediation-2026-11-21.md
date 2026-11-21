# Module B PR #12 review test remediation — 2026-11-21

## Trigger

GitHub review `PRR_kwDOVtJ17M8AAAABZeU9_g` requested changes on implementation
commit `ea1bfed328528d11578980a757c80bef1c7a84b0`. This record covers only the
test-proposal remediation; no business source was changed.

## Added RED constraints

- A page-only locator with forged excerpt text must fail closed after consulting
  controlled source bytes.
- The concrete `PaperQA2Adapter` must exercise the `Docs.aadd`,
  `Docs.aget_evidence`, and `Docs.aquery` API shapes on synthetic data, preserving
  actual sent evidence and an unambiguous citation mapping.

The original 48 tests were not weakened or deleted.

## Commands and observed results

```text
PYTHONPATH=src <approved-runtime-python> -m pytest -c papertrace.pytest.ini \
  test/offline/test_retrieval.py \
  -k 'forged_excerpt_with_page_only_locator or concrete_paperqa2_adapter' -q

2 failed, 48 deselected
```

Both failures are the expected B1 RED assertion that
`papertrace.retrieval.gateway` is absent on the test-only branch.

```text
<existing-ruff> check --config papertrace.ruff.toml test/offline/test_retrieval.py
All checks passed!

PYTHONPYCACHEPREFIX=<temporary-path> python3 -m py_compile \
  test/offline/test_retrieval.py
exit 0

git diff --check
exit 0
```

## Governance state

The prior PR #9 approval binds only exact head `7833527`. The amended test head
must receive a new independent GitHub approval before implementation changes.
