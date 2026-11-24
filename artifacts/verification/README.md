# Initialization verification evidence notes

- `final-offline.xml`: the real final pytest JUnit run, 170 items, 0 failed / 0 errors / 0 skipped; it is not the full upstream PaperQA2 regression.
- `offline-tests.txt`: actual offline pass output; the timestamp may come from an earlier re-run of the same version, so treat `final-offline.xml` and the final-submission-bound receipt as the latest record.
- `contracts-tdd.txt`, `gates-tdd.txt`: real RED/GREEN process; `*-red*.txt` intentionally keeps failed experiments, not the current failure state.
- `opencode-runtime.json`: actual project configuration readback and 13 real permission-engine probes; it does not execute the model or the read/edit/shell tools and is not end-to-end tool equivalence.
- `*-gate.json`, `all-gates-initialization.json`: local initialization gates and the full course gap. `all` is exit 2 / BLOCKED; unexecuted parts are not marked PASS.
- `delivery-audit.json`: programmatic checks of required files, links, traceability, source freeze, anonymity and small-sample timing; it is not a human APPROVE.

For shared privacy, some real logs replace only the local home path with `<HOME>`, without changing assertions, errors, pass counts or timings; the original logs stay in the locally ignored directory `.local/raw-evidence/` and are not distributed with the material package. Failed experiments, post-fix passes and unexecuted scope are recorded separately; the existence of this directory is not proof that all course requirements are complete.
