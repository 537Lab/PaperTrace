# A library synthetic fixtures

All text is handwritten synthetic material: no real papers or personal data.
The PDF reproduces the supplied ASCII payload including LF endings, trailing
spaces in xref entries and the terminal LF. Expected length: 634 bytes;
SHA256: `970046dfe2ba98dcfde18be259a7d72fc2554c9b92fd8cb1b62d15c75b966ed6`.
It contains one page, a Helvetica resource, content stream and xref/trailer.
Fixture integrity checks do not prove real PDF parsing.

`broken-delta.txt` is valid nonempty synthetic text. FakeIngest injects
`PARSE_FAILED` by basename; it is not a naturally corrupted parser input.
The fake records actual request bytes, identity, SHA and calls, and substitutes
only the proposed external ingest port, never A storage, hashing or service.
No PaperQA/model/network/OCR/metadata calls are made. A/B receipt semantics
remain PROPOSED_INTEGRATION, not a frozen B API.

Alternate versions, missing/empty/unsupported/oversize files, symlinks,
unselected sources and corrupted managed bytes are built only under tmp_path.
Validation results（监督端实际执行并在聊天提供，非本助手运行）：显式policy_ref
修正后测试SHA256为 `e056958793f7661f52075f8b0baffe2628ed36a50b3d47fe407e7c04cf0e3037`。
无凭据、全英文scratch路径的最终验证：A pytest 33 collected/selected，2 passed /
31 failed，exit1；全offline 365 collected/selected，334 passed /31 failed，exit1。
两者collection/config errors均为空，skip/xfail/xpass均0；31项全为
IMPLEMENTATION_MISSING: papertrace.library; ASSERTIONS_NOT_REACHED 前置失败，
不是业务RED。既有332项及2个新基础自检通过不等于全套或完整上游回归PASS。
Ruff、mypy（仅既有src）、schema和默认静态preflight均exit0；preflight
model_started=false，未运行--verify-runtime。原命令见test-plan第6节，无凭据runner
插件参数/实际argv由监督端外部记录提供。
监督端另以系统sips渲染本PDF为PNG，exit0；原PDF仍634字节、上述SHA256不变且与
patch payload逐字节相同，仅证明系统可打开，不是PaperQA解析或A导入通过。
历史validation-01全suite曾332 passed/33 failed，其中2个既有loopback沙箱测试因
非ASCII临时路径EPERM mkdir失败；未改共享测试/权限，仅切换ASCII HOME/TMP及报告
目录后validation-02-ascii为334 passed/31 failed，当前validation-final再次同数。
旧失败日志保留；完整证据由监督端外部记录/最终审核ZIP提供，本助手未读取。
尚无独立学生对具体测试commit的GitHub Approve，仍禁止源码实现。
Fixture/contract PASS alone is not A import PASS.
