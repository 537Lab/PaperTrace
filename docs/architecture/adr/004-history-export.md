# ADR-004: Module E history storage and excerpt export boundary

Status: proposed, awaiting independent review of PR #14 current head.
Date: 2026-11-22.
Scope: FR-E-01/02, QA-01, SEC-01, INV-02/04/05/08.

## Context

Historical research must preserve the original snapshot, evidence, ledger tokens,
answer and recorded release state. Storing a package is not permission to share
paper excerpts. The shared contracts and other module authorization decisions
remain the source of truth. This document records the implemented design for
review; it does not assert an earlier ADR approval.

## Decision proposed for review

Use an E-owned version-1 closed research envelope around existing shared models.
Validate identity associations, ledger revision/digest and draft/release binding.
Do not recompute D's release decision or promote blocked/failed/abstained results.

Store one UUID-named JSON per record. Validate identifiers before file access,
reject symlink roots/record entries and refuse overwrites. Write a sibling
temporary file, flush/fsync it, then publish exclusively using a hard link.
Clean the temporary file on failure. Unsupported hard links fail closed; copying
directly into a final filename is disallowed because it exposes partial writes.
This is application path validation, not OS isolation or protection from a
concurrent attacker replacing ancestor directories. The host must control the
history directory and its ancestors.

Keep external export separate from internal serialized history. Exclude excerpts
by default, redact absolute local paths and reject credential-like metadata.
Excerpt inclusion requires both explicit request and a trusted verifier accepting
a grant bound to the record, evidence IDs and external-export purpose. Grant
fields and reviewer strings alone do not establish identity. The embedding
application must provide the trusted issuer/verifier; this module does not build
an identity service. Preserve recorded release state in both export formats.

Superseded is a read-only display comparison with the current snapshot supplied
by the caller. Never rewrite old research from a newer library snapshot.

## Alternatives and limits

A database would add dependencies and operational scope. Direct final-file
writing cannot guarantee clean failure. Replacing an existing final file would
violate append-only history. A caller-provided permission bool does not prove
export authority. Public-root Apache licensing does not license paper content.

No A-D interfaces, shared contracts, dependencies, CI policies or approved tests
are changed. Live semantic quality and final application orchestration are outside
this implementation. A hard-link-capable local filesystem is required.

## Evidence and approval

Metadata boundary follow-up for independent review: recursively reject sensitive
keys/absolute path values through every nested container. Because frozen=True
does not deeply freeze dict/list data, save serializes once and validates those
exact bytes before persistence, then writes the same validated bytes. This is a
runtime boundary and not a claim of deep in-memory immutability. New test head
1506de96a8da396d2e6852c7abccd8a8ecde8b25 was independently approved; the new
implementation and this ADR follow-up still require exact-head source review.

Approved tests: PR #8, head 81e834596771cfbf5d140b2e68cb9431fcf083af.
After synchronization with main, all 32 E tests, E ruff and E mypy passed on the
submitted 5af4292 snapshot. Full local regression had 312 pass, 74 fail and two
skip; its limitations are recorded separately. These results do not constitute
independent approval. A non-author must review the current implementation head
and this ADR in PR #14. Both PRs remain open; no merge is authorized.
