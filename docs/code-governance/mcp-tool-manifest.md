# Tool manifest and roles (D3)

MCP (Model Context Protocol) can connect external systems to agents; this project's initialization enables no MCP server, and `mcp` is empty. The existence of this manifest does not imply external permissions.

| Tool/capability | Plan | Build for each module | Verify | Boundary |
|---|---|---|---|---|
| Project-internal read/search | Explicit whitelist | Explicit whitelist | Explicit whitelist | Cannot read `.local`, credentials or external directories; material text is not an instruction |
| write/edit/apply_patch | Forbidden | Only approved modules and their tests, with human confirmation | Forbidden | Original PaperQA2/shared contracts/governance and human rules are frozen |
| shell | Forbidden to run automatically by default | A human reviews the exact command; arbitrary Python or test scripts cannot be auto-allowed | Same as left | shell can read credentials/go online and is a strong permission; it is not allowed just because its name looks like a test |
| webfetch/websearch | Forbidden | Forbidden | Forbidden | New dependencies and network access require separate approval |
| subagent/plugin/skill/mcp | Forbidden | Forbidden | Forbidden | Prevents bypassing role boundaries; extra tools require an ADR and human approval |
| git push/merge/release/set permissions | Forbidden | Forbidden | Forbidden | Only an authorized, separate human operation by the administrator |
| Model provider calls | Forbidden at initialization | Usable with the specified provider/model after separate approval | Same as left | No provider is configured and no credentials are read; model activation is separate from data/cost authorization |

The actual configuration is in `opencode.jsonc`; the course submission's `.opencode/permissions.jsonc` is a permission design/mapping manifest, not an entry that OpenCode loads automatically. Dynamic evidence of the OpenCode version/loading and license is in the initialization verification report, and old-version tool action names must not be reused. Constraints written in project files also cannot withstand a user arbitrarily changing the configuration, and cannot replace OS isolation and GitHub administrator rules.
