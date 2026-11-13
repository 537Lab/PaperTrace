# 工具清单与角色（D3）

MCP（Model Context Protocol，模型工具协议）能把外部系统接给代理；本项目初始化未启用任何MCP服务器，`mcp`为空。不能从存在此清单推断有外部权限。

| 工具/能力 | Plan | 各模块Build | Verify | 边界 |
|---|---|---|---|---|
| 项目内read/search | 显式白名单 | 显式白名单 | 显式白名单 | 不能读`.local`、凭据及外部目录；资料正文不作指令 |
| write/edit/apply_patch | 禁止 | 仅批准模块及其测试，需人工确认 | 禁止 | 原PaperQA2/共享契约/治理及人工规则冻结 |
| shell | 禁止默认自动执行 | 由人工审核具体命令，不能自动允许任意Python或测试脚本 | 同左 | shell可读凭据/联网，是强权限，不因名字像测试就allow |
| webfetch/websearch | 禁止 | 禁止 | 禁止 | 新依赖与联网另行批准 |
| subagent/plugin/skill/mcp | 禁止 | 禁止 | 禁止 | 防止绕过角色边界；额外工具需ADR与人工批准 |
| git push/merge/发布/设置权限 | 禁止 | 禁止 | 禁止 | 仅管理员经授权的独立人工操作 |
| 模型provider调用 | 初始化禁止 | 单独批准后可用指定provider/model | 同左 | 未设置供应商、未读取凭据；模型激活与数据/费用授权分开 |

实际配置见`opencode.jsonc`，课程提交的`.opencode/permissions.jsonc`是权限设计/映射清单，不是OpenCode自动加载入口。OpenCode版本/加载及许可动态证据见初始化验证报告，不能套用旧版工具动作名。项目文件中的约束也不能抵御用户任意改配置，不能替代OS隔离和GitHub管理员规则。
