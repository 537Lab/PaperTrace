# OpenCode v2.0.12 项目接线与验证

本轮实测版本2.0.12。`opencode.jsonc`为引擎配置；`.opencode/permissions.jsonc`仅是课程要求的机器可读权限设计与映射，不会被引擎自动当配置读取。所有未列工具默认deny，Plan只读，Build仅对应模块精确文件ask，原核心/共享契约/规则/权限/工作流/凭据/shell/推送不授权。

## 为什么没有instructions数组
固定官方v2.0.12的`instructions`虽可解析，却尚不解析其中的文件/glob/URL。因此`.opencode/rules.md`原文被明确镜像到每个papertrace角色的`agents.<角色>.system`。配置测试比较原文与镜像，实际`GET /api/config`回读再次核对。本轮没有真实模型会话，所以不能把配置回读升级为“模型已经遵守全部规则”。根AGENTS.md由该版指令发现机制处理；它不是任意路径读写的授权。

## 已执行的零模型验证
```sh
.venv/bin/python scripts/opencode_support.py
.venv/bin/python scripts/opencode_support.py --verify-runtime --binary <本机opencode可执行文件>
```
第二条只适用macOS：隔离HOME/XDG和所有运行状态，使用一次性loopback standalone服务器、阻断非回环网络及仓库外home读取，最后退出；不会发起模型生成。真实结果在`artifacts/verification/opencode-runtime.json`。

13项真实许可引擎探针覆盖Plan读允许/写拒绝、A写ask、跨模块写拒绝、B读原码允许/写拒绝、共享契约和human-only规则写拒绝、凭据/外部目录/路径穿越拒绝、shell和git push拒绝。该API判定的是`Permission.ask`，**没有执行read/edit/shell工具**；不能称完整工具端到端通过。独立OS探针如执行，另列结果，不混成Agent操作证据。

## 学生如何启用后续开发
配置默认`papertrace-plan`，所有provider.use目前deny，未配置真实模型或凭据。因此尚不能直接运行生成。学生先确认课程工具/共享起点和ADR、认领模块，选择获准provider/model及文献/次数/费用范围；由凭据持有人通过安全机制接线，不将密钥放Git或聊天。人工仅为指定provider添加窄范围allow并审查有效配置；不得用`--auto`、宽松shell或临时session allow绕过保护。

Plan阶段只输出Prompt.md要求的计划，学生与非实现者真实批准后，选择对应`papertrace-build-A`至`papertrace-build-E`角色；候选文件仍每次ask。当前没有本轮模型连接/Build工具写入或人工审批记录。不要用本轮初始化的schema/lint/JSON往返冒充正式OpenCode过程。

普通在用户全局环境中启动的OpenCode可能合并其他配置；本轮隔离验证不证明那些启动方式安全。完整无模型官方工具suite还需Bun与固定源码依赖，本轮未安装/执行。v2.0.12路径判断为lexical，官方测试显示symlink可别名到外部目标；这里预检查拒绝所有白名单symlink，但检查与后续使用之间仍可能有竞态，不能承诺OS级永久防护。

## 官方固定来源
- https://github.com/anomalyco/opencode/tree/v2.0.12
- https://github.com/anomalyco/opencode/blob/v2.0.12/services/www/src/docs/content/instructions.mdx
- https://github.com/anomalyco/opencode/blob/v2.0.12/packages/core/src/config/plugin/agent.ts
- https://github.com/anomalyco/opencode/blob/v2.0.12/packages/core/src/permission.ts
- https://github.com/anomalyco/opencode/blob/v2.0.12/packages/core/src/file-access.ts
- https://github.com/anomalyco/opencode/blob/v2.0.12/packages/core/test/tool-edit.test.ts

滚动官网可作补充，版本判断以固定源码与本机实际OpenAPI/回读为准。没有修改用户全局OpenCode配置，没有读取个人认证文件。
