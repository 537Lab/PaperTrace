# Module D generation and attempt accounting

Test approval PR: #42

Architecture decision: docs/architecture/adr/001-architecture.md

The generation service transfers configured provider and model identifiers and the
attempt count reported by B. It preserves zero, an unknown count, and the absence
of an accounting object as distinct values. It rejects unsupported evidence and
unknown citation keys before publication. Gateway errors propagate with their
original cause and diagnostics. Accounting does not enter report exports.

The two newly authored files are `generation.py` and `b_gateway_adapter.py`.
The candidate follows the approved test commit `aa9283d1928299d0c50ae55272477cc52c593834`.
Source prerequisites come verbatim from D #32 `6a98c9c7b2069c8329237c15e82bdbf60097c5c7` and B #34 `a9440e6767e9ba90642dbe5cf2bb46a526125540`.
The ADR retains its recorded limited scope. The #32 release check remains under review.
The candidate includes B as a local dependency snapshot for reproducible verification.

The supervisor reproduced 7 failing accounting behaviours and 4 passing controls
before the change. With the pinned runtime, 253 D/C tests and one PaperQA2 smoke test passed.
With the initialization interpreter, 580 offline tests passed, two were skipped, and
three bridge tests stopped at missing `lmi`. That interpreter differs from the runtime lock.
Targeted Ruff, mypy (18 files), and the architecture import check passed. The full
Ruff scan reports the existing smoke script import ordering failure.

In the offline replay, the real B bridge, C ledger, D generation service, #41 app renderer,
and real E panel process synthetic text with scripted UI and fake model calls. One successful
attempt and one failed attempt retained their accounting. The failed attempt retained its
original cause. Explicit save, reopen, default export, blocked saves on upstream errors,
and immutable history passed. Review reset blocked the old draft. The release status remains
`blocked / PUBLICATION_COMMIT_UNAVAILABLE`.

OpenCode performed both generation and accounting source preparation in the D Build role.
Codex conducted verification and assembled this local candidate. Original prompts, API receipts,
and session records are retained privately. Formal review of a published implementation head,
the public application's runtime B/C/D wiring, and real semantic evaluation remain pending.
