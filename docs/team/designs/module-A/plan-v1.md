# A 文库核心 Plan v1｜已批准仅测试准备

## 1. 当前批准、来源与范围

2026-11-17，监督学生在当前聊天正式批准所附 Plan v1 进入**仅测试准备**，
并允许现有官方 ChatGPT Plus OAuth / `openai/gpt-6.1-sol`。
这不是另一位未参与测试实现的学生对具体测试 commit 的 GitHub Approve，
不是源码授权，也不是角色/工具权限可以代替的身份证明。
附件原题为“待学生批准测试准备”，原文“本轮只 Plan / 此刻不创建 / 等待批准”
描述历史规划阶段；当前批准只推进到生成这 8 个测试材料文件。

历史规划会话：`ses_e16b06bc3ffeYTsjilqwrt1854`。
当前会话：`ses_e16070785ffeHshzjX8s115x1L`。
监督端报告起点为 `test/A-corpus-management`，
HEAD `7b5549ced8b5c9c1c1eb35576da95bc1381e858a`、工作树干净；
这是监督端陈述，不是本会话执行 Git 核验所得。

仅规划并测试 A 文库核心：显式选择、导入结果、logical document identity、
源字节 SHA256、托管原件、不可变快照、受限读取。A 不导入 PaperQA；
B 仍是唯一 PaperQA2 解析/表示适配所有者。A view、首个 UI 装配及共享入口另阶段。
排除检索、人审、回答/发布、报告、向量数据库、跨存储事务。

## 2. 原 registry 验收阈值（保留）

下表沿用批准附件；本会话没有重新读取 registry 或重新定义需求。

| ID | metric / fit criterion |
|---|---|
| FR-A-01 | `import_case_pass_ratio >= 1.0` |
| FR-A-02 | `mutated_historical_snapshots == 0` |
| INV-02 | `identity_or_version_mismatches == 0` |
| INV-05 | `overwritten_history_records == 0` |
| INV-06 | `unauthorized_tool_effects == 0` |
| QA-01 | `contract_roundtrip_and_negative_test_pass_ratio == 1.0` |
| SEC-01 | `detected_secrets_or_member_identity_fields == 0` |
| COST-01 | `initialization_model_requests == 0` |

A 单模块测试不能宣称整个项目满足共享质量、安全或治理验收。

## 3. 核心方案及三项强制修正

逻辑 ID 表示“哪篇”，SHA256 表示实际托管源字节，不用文件名、mtime、
解析文本或上游 MD5 替代。使用真实 `DocumentVersion`、`CorpusSnapshot`；
不复制共享快照哈希算法。标题/安全显示文件名也参与共享快照身份。
逐项状态、失败阶段和原因属 A-local；共享快照只包含 ready 版本。

1. **complete 仅属 A-local 批次结果**，绝不给 frozen `CorpusSnapshot` 增字段；
   实际测试用真实模型校验 extra 禁止。
2. **合法明确选中的绝对路径必须接受**。受控来源根加显式已选文件清单，
   拒绝未选中（包括根内文件）、越根、`..` 穿越和文件/目录链 symlink 逃逸。
   不新增身份服务或全目录授权扫描；服务直调也检查，不靠 UI。
3. **A→B 回执、部分库、失败换版 current 投影、freshness/ABA 都是提案**。
   测试本地 Fake 可验证 A 的假设；docstring/测试表标记
   `PROPOSED_INTEGRATION`，不能冻结共享 B API。未确认仅暂停受影响集成。

拟议策略：已成功且版本核验一致的重复选择复用；失败重复提交不自动重试。
显式 retry 仅处理失败项并追加尝试，不能把 ready 伪装失败重摄取。
明确指定 logical ID 换字节时保持 ID，产生新版本，旧源/快照/历史不覆写。
同名不同来源默认不同逻辑文献，不按 basename 静默覆盖。

单机单写者存储：先写托管源、不可变快照及版本化 manifest，最后原子替换
小型 current 指针。中断不推进 current，重启只加载指针所指且核验通过的记录；
损坏则只读/待修复，不自动挑最新或重放摄取。

待团队确认的三项完整语义：
- A/B 回执：输入受控源字节、ID、SHA、安全文件名、人工元数据和策略引用；
  输出实际 ID/version、阶段/原因、表示引用；缺失、身份不符、未知成功状态不 ready。
- A/B（涉及发布时 D）部分库：3/4 成功只返回三个 ready，批次 complete=false；
  换版失败拟从 current 排除旧版，旧版仅留历史，不冒充新版成功。
- A/B/D 及相关 C/E freshness：A-local `(snapshot_id, 单调 corpus_revision)`
  防止移除再恢复 ABA；不往 frozen snapshot 填 revision/complete。

## 4. 精确路径与冻结范围

本轮唯一允许的项目文件：
1. `test/offline/test_library.py`
2. `test/fixtures/library/normal-alpha.txt`
3. `test/fixtures/library/normal-beta.txt`
4. `test/fixtures/library/normal-gamma.pdf`
5. `test/fixtures/library/broken-delta.txt`
6. `test/fixtures/library/README.md`
7. `docs/team/designs/module-A/plan-v1.md`
8. `docs/team/designs/module-A/test-plan-v1.md`

Fake/spy/helper 都留测试文件，换版、异常、越界 sentinel、超限和损坏源在
`tmp_path` 动态生成。没有真实论文或个人资料。
未来独立测试审批后才考虑
`src/papertrace/library/{__init__.py,models.py,ports.py,storage.py,service.py}`，
分别为出口、A-local 记录、获批端口、存储和服务；**本轮绝不创建**。

冻结 `src/paperqa/`、`packages/`、旧 `tests/`、`pyproject.toml`、`uv.lock`、
`LICENSE`；不改 `contracts.py`、schema、共享 fixtures/config、CI、权限/规则、
依赖、日志、其他模块、上游。不读取 `.env`、`.local/`、凭据、私人目录或 `.git/`。
本轮禁止读取 `docs/ci/test-approval.md`；没有通过其他工具绕取。

## 5. 测试重点（原计划覆盖保留）

1. 两 TXT 一 PDF 成功 + 非空 delta Fake 注入 PARSE_FAILED；四结果、三 ready、
   complete=false、四次真实字节/ID/SHA 输入，真实快照恰三成员。
2. 重复提交零新增调用；失败不自动重试。
3. 显式 retry 仅失败项，恰一次调用，历史保留，成功可生成四项快照。
4. 同 ID 换真实字节改变 SHA/快照；失败换版不伪装 ready（current 策略仍提案）。
5. 旧快照文件/历史源字节不变，外部源变化不回写托管；ABA 单调修订提案。
6. 绝对路径授权正例和未选中/越根/穿越/symlink 负例；空、缺失、不支持类型、
   超限拒绝。可配置初始 **20 MiB** 上限仍待确认；测试用 128 字节小阈值。
7. 托管丢失/hash 错、串快照读取、回执缺失/错 ID/version/未知状态、超时/异常；
   隔离单项失败，脱敏，不自动重试。
8. 复制/manifest/切 current 中断不前移、不覆盖旧记录；无法持久记录明确失败，
   不承诺不存在的审计证据。

原“35 项”仅覆盖清单，不是凑数目标。本轮形成 19 个核心测试函数（参数化 33 nodes），
其中 2 个 fixture/contract 基础测试，17 个 A 行为测试函数。精确映射/API 见 test-plan。

## 6. 工具、验证与费用

仅 native read/patch 创建材料，无 Shell/Python 写文件绕过、插件、MCP、subagent
或 `--auto`。本轮不在原仓库执行 Shell 测试。
监督端将在同基线无凭据隔离副本中复制 8 文件，用现有解释器验证：

```sh
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline/test_library.py
.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline
.venv/bin/python -m ruff check --config papertrace.ruff.toml src/papertrace test/offline scripts
.venv/bin/python -m mypy --config-file mypy.ini src/papertrace
.venv/bin/python scripts/gates.py --gate schema
.venv/bin/python scripts/opencode_support.py
```

preflight 原 Plan 未核验实现/角色许可，执行前仍由监督端核对，不适用则停报。
结果一律**待监督端执行**；不借用旧 332 项结果，不预填通过。
分开报告结构/完整既往回归/行为，缺环境或授权为 BLOCKED，真实模型评测 NOT_RUN。
缺实现前置 FAIL 或 import/collection ERROR 不是业务断言已观察到的 RED。
不 skip/XFAIL/importorskip，不吞错误或删测试求绿；允许修正测试自身语法/契约错误，
保留真实失败日志。

产品 LLM/embedding/OCR/metadata/其他付费 API 预算 **0**，自动模型重试 **0**。
沿用现有 Plus 助手，开发助手用量由监督端导出，不称无限免费；不换模型/provider、
不装依赖、不新增订阅/API、不运行常驻任务。

## 7. 真人检查点、证据和停止条件

需求/计划 → 学生批准（本轮仅测试准备）→ 生成测试/fixture/设计 →
**另一位未参与测试实现的学生在 GitHub 对具体测试 commit 实际 Approve** →
才可实现。当前没有独立测试批准证据，不代写 Approve/PR/ADR 编号。
测试 proposal PR 可 open 且 RED，不为审批合并；远端操作由真人负责，本轮不
commit/push/PR/merge。未来实现 PR 从测试 head 创建，描述必须写精确行
`Test approval PR: #N`（届时填写真实编号）。测试语义变更须重新审批。

安全路径/共享契约变化需适用 ADR 和受影响 owner 人审；普通 A 细节不逐函数 ADR。
项目规则不冒称教师原件逐条要求。模型建议不等于人工授权，角色/权限不证明审批。
共享 AI-use log、review memo 由有权维护者后续追加；不把初始化工程修复冒称学生
OpenCode 贡献，不写成员姓名/邮箱，保留真实会话/人工干预。

权限拒绝、扩大路径、契约/依赖/安全边界变化或费用/网络需求立即停报，请求人工
窄授权，不放宽或绕行。恢复保留旧 current、隔离未完成暂存，不 reset/clean 或删
他人文件。后续独立人审、三级验证和真实 PR 状态尚未完成。
