# Regression diagnostics fixture follow-up

Implementing approved #79 exposed a fixture defect: workflow_with_transport clones the real workflow and inserts a second qualification/upload/summary chain. After installation, ten positive mutation controls fail on duplicates.

Validate an installed chain first, then remove only that validated chain from the synthetic copy before mutation. Invalid or broader uploads still fail. The real workflow test, exact six-file allowlist, failure/cancellation conditions, qualification protocol, original 76 nodes and existing assertions remain unchanged. Two new controls prove valid-chain replacement and rejection of a broader invalid upload.

This proposal changes tests and documentation only. Workflow controls: 31 PASS; real-workflow acceptance remains availability RED on the unimplemented baseline. Total collection: 78 nodes. The original implementation replay was 64/76, with ten duplicate-fixture failures and two native-Windows executable-shebang fixture failures. The latter require supported POSIX execution and are not PASS.

A non-implementer must approve this exact new test head before implementation adopts it. Keep the proposal open. No gate verdict, permission, dependency, test selection or paid-call authorization changes.
