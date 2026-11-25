# Bounded regression diagnostics implementation candidate

Owner: LIN ZIQI, assigned shared CI closeout by the student. This branch starts from independently approved #79 head 13d2051bb7225aac49dda04f9db15feb82f98df9 and preserves main history through 23074c96734927c6148ccf8b3dc17b4a1944f073. Original approved test and plan blobs are unchanged. No new OpenCode implementation session is claimed: this is disclosed Codex runner-authored work, requiring independent source/process review.

The original certification path remains authoritative. A thin wrapper adds fresh bounded per-suite event/manifest files and catches diagnostic packaging failures without upgrading or hiding legacy failures. Child events retain collection nodes and setup/call/teardown outcomes, including subtests; terminal/budget/partial flags are explicit. Arbitrary exception bodies are deliberately unavailable, since document text and credentials need not have recognizable syntax. Only the bounded exception class is exported. Raw stdout/stderr and the legacy pytest report remain local and unchanged.

Events are capped at 1,228,800 bytes, each manifest at 65,536, and the six current/prior directories at 7,766,016 total. Existing links are unlinked without following; unexpected directories are retained and diagnosed. The parent records target/control/base/tree identities without forwarding trusted metadata or credentials to children. Qualification checks independent identity and actual tree, regular files, links, bounds and advisory status. A failure-only upload names precisely six current-suite files, opts in hidden files and excludes cancellation. The always-run summary reports actual gate, qualification and upload outcomes. Other jobs and the original failing regression command are unchanged.

Verification boundaries:

- Configured Ruff passed.
- First unchanged #79 replay: 64 PASS / 12 FAIL. Ten positive mutation-fixture controls append duplicate transport to an already installed workflow. Two executable-shebang fixtures do not launch on native Windows.
- Pure test follow-up #89 (f6f286b1) corrects that fixture while retaining every original test/assertion and adding two controls. It is not included in this implementation and must be independently approved first.
- An external diagnostic overlay of that proposal and this implementation, plus the original runner tests, produced 91 PASS / 4 FAIL. The failures are two shebang fixtures, an existing cross-drive relative-path fixture and a POSIX ps/process fixture. No fail is called PASS and no assertion is removed. Supported POSIX replay is required before readiness.

Keep this implementation Draft. After #89 approval, open the chronological implementation inheritance PR from its exact approved head with the required test-approval reference; retain both histories and repeat supported-runtime verification. This candidate is reviewable work, not authorization to bypass the chronology rule.

The currently adopted verifier does not yet implement the diagnostic qualification CLI. Before independent adoption, a PR run may therefore withhold transport; changing the job to execute its unmerged candidate verifier would violate the existing trust boundary and is deliberately avoided. After normal protected adoption, failing main checks can carry qualified advisory artifacts. Remaining failures must then be diagnosed individually; documentation never converts regression FAIL into green.

No model request, provider credential, Environment/Secret change, dependency installation, test selection exemption, branch-protection bypass or merge is part of this implementation.
