# Gate 5 team-offline collection

## Scope

Keep CI's `--import-mode=importlib` and `test/offline` entry point. Ensure the team pytest configuration can load the existing test helpers imported by the tested evaluation-control and evaluator suites. No product code, CI workflow, model dispatch, scoring, gate verifier, upstream configuration, or existing approved test is in scope.

## Reproduction and acceptance

The supported Gate 5 runner invokes team-offline tests with `-c papertrace.pytest.ini --import-mode=importlib`. Pytest does not add the test directory to the import search path in this mode. With `pythonpath = src`, `test_evaluation_control_paths.py` fails on `from test_gate_evidence import ...`. The same problem affects the proposed #53 and #58 tests, which import their shared `test_semantic_evidence` helpers.

The proposal adds one subprocess regression against the exact team pytest configuration and import mode. It must observe successful collection of the existing evaluation-control file. An implementation may explicitly add the repository's `test/offline` directory to `papertrace.pytest.ini`. Keep `src` in the configured path, preserve the import mode and leave existing tests unchanged.

Run the new test on the baseline for the collection failure before independent review. After approval, repeat it using the proposed team-only import setting. Check the unchanged shared tests and validate collection of the #53 and #58 test blobs on a separate combined snapshot. Retain command output and distinguish collection from executed tests and from full upstream regression.
