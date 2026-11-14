## 本 PR 做了什么 / 属于哪个模块

模块：A / B / C / D / E（圈一个）　｜　是否触及共享契约或 CI：是 / 否

<!--
本模板把课程 p10 的六类 blocking gate 变成可核对的证据清单。
六类门禁全部保留；BLOCKED 的门禁不会因为勾选而变成 PASS。
最小落地方案见 docs/ci/minimal-gates.md。
-->

## 六类门禁证据（轮值 reviewer 逐项核对，作者不能自批）

- [ ] **1 事前测试批准**：独立的「测试/计划 PR」获批在先（可保持 open/RED，不强制先合并）；贴出链接、其 head SHA、批准人、批准时间。实现 PR 未改动已批准的测试文件；如改动，已重新批准。
  - 测试 PR：____　批准人（≠ 本 PR 作者）：____　测试 tree SHA：____
  - 未通过时状态：**BLOCKED**，不得用仓库内 `approved: true` 或本地时间戳代替。
- [ ] **2 静态分析**：`static-analysis` check 为 success；贴出 ruff / mypy / schema 实际输出。完整供应链审计仍非本轮范围。
- [ ] **3 需求 Schema**：`schema` check 为 success；如改 `docs/req/requirements.yaml`，说明对应 fit criterion 与 trace 更新。
- [ ] **4 语义评估**：仅当触及产品 prompt/model/AI 行为时适用。贴出获准的 provider/model/次数/金额批准记录、`docs/reviews/eval-*.json` 报告、dataset SHA、独立 reviewer 的逐条 rubric 理由。
  - 无真实调用与独立人工评分 → **BLOCKED**；固定 mock 回复、跳过调用、自写 PASS 一律不接受。
- [ ] **5 完整既往回归**：团队离线 + runtime + 上游三来源实际执行，0 skip；贴出上游 `collect-only` 清单、JUnit、版本指纹与前后差异人审结论。
  - L2 未跑完 / 有 skip / 基线原有失败未处理 → **BLOCKED**；不得用 170 项绿灯冒充 full。
- [ ] **6 AI-use log**：代码/prompt 变更已在 `docs/ai-use-log.yaml` 留下真实新增披露；reviewer 核对内容真实性。

## 独立审查

- 轮值 reviewer（≠ 作者）：____　审查结论：通过 / 要求修改
- 真实 OpenCode 会话（D5）保存位置：____　（不得事后补造或把初始化会话冒充个人贡献）
- 已知未完成 / 债务：`docs/debt-register.md` 条目：____

## 当前远端边界（不要误读）

分支保护与 required checks **尚未生效**（免费套餐私有仓库 403）。本 PR 的六个 CI 检查会真实运行并显示红/绿，但**不构成强制合并拦截**；缺真实证据时会 BLOCKED，矛盾/质量或测试失败会 FAIL；不得把任何红灯统一解释成预期成功。请 reviewer 按上面的清单人工核对后再合并。
