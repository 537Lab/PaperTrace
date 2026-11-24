# Upstream baseline and this round's boundaries

Source: https://github.com/Future-House/paper-qa
Pinned commit: `c692d0dfeac4a0296599f7fe21a253a58b7ac12a`.
Local tag: `papertrace-upstream-baseline`. The complete original Git history is preserved; the team initialization is a successor commit to it and does not impersonate the original authors. `src/paperqa/`, `packages/`, the original `tests/`, `pyproject.toml`, `uv.lock` and `LICENSE` are unchanged this round.

The original README bytes are preserved in `README.paperqa.md`; the original GitHub workflows are preserved byte-for-byte in `workflows/` with a `.disabled` suffix and do not run automatically in Actions, avoiding inheriting release/provider-credential flows. The root README and `.github/workflows/ci.yml` are newly added team governance surfaces; these layout changes are recorded separately and are not called upstream core modifications.

Only a read-only upstream fetch remote is kept; the push URL is `disabled://papertrace-read-only-upstream` and `push.default=nothing`. After the user's explicit authorization on 2026-11-13, the team `origin` was set to https://github.com/537Lab/PaperTrace (private) and main plus the 3 `papertrace-*` tags were pushed; the complete upstream history and the baseline SHA are preserved. Branch protection is not in effect (403 under the free plan).

Copyright/licenses follow each package's LICENSE. Papers/recorded responses carried in the upstream history do not automatically obtain a redistribution license; preserving them on this machine is not permission to upload. This round's team materials package contains no upstream papers, original course PDFs, API recordings, .git or any credentials. Before uploading the complete repository, the redistribution scope must be reviewed per `docs/licenses/license-review.md`.
