# 六类门禁：面向五人学生团队的最小落地方案

更新：2026-11-14。来源：课程 Project Requirement Sheet p10（六类 blocking gates + 分支保护）、p6 D4（每轮完整既往套件），口径见 [../sources/course-compliance.md](../sources/course-compliance.md)。

**六类门禁全部保留，一门不放宽。** 本文只解决一个具体问题：原 `test-approval.md`、`test/evaluation/README.md`、`full-regression.md` 把「可信」实现为自建外部审批服务、OIDC attestation、不可由 PR 修改的信任配置与服务器事件 ID —— 那是对抗恶意供应链的企业级认证，五人课程团队既没有条件部署，也不是老师要求的重点。课程要的是**真实行为**：测试确实先被非作者批准、模型评估确实发生过且被独立复核、既往测试确实跑完且没有 skip。

因此改用 **GitHub 原生 PR 事件 + 轮值人工复核 + 可核对的记录文件** 作为可信来源，不自建 PKI、不设外部服务、不伪造任何 PASS。

## 一、可信来源：为什么 GitHub PR 够用

GitHub 服务器记录 PR 的创建时间、commit 时间、review 提交时间与 reviewer 身份、head SHA、merge 时间。**PR 作者无法改写服务器时间戳，也无法冒充别人的 Approve。** 对五人互评的课程项目，这已经满足「独立于实现者的可信审批」；再叠一层自建认证系统不增加真实性，只会让流程跑不起来。

固定分工（沿用 `TEAM_WORK_PLAN.md` 的轮值）：每个 PR 由**非作者**同学担任 reviewer；作者不能自批；测试变动后须重新批准。reviewer 姓名写在 PR 里，不匿名、不代签。

## 二、三类原先「永远 BLOCKED」门禁的最小实现路线

### Gate 1 事前测试批准（test-approval）

**两步 PR 流程**，把「事前」变成可核对的服务器时序：

1. **测试/计划 PR**：只含 `test/offline/test_<module>.py`、fixtures、计划文档；**不含实现代码**。
2. 轮值 reviewer（≠ 作者）在 GitHub 上 `Approve`，PR 描述记下测试 PR 的 head SHA 与批准人。
3. 合并该 PR，然后才开**实现 PR**，描述里贴测试 PR 链接 + merge commit SHA + 批准人。
4. CI/人工校验（可用只读 `gh api`，无需外部服务）：

```sh
gh api repos/537Lab/PaperTrace/pulls/<测试PR号>/reviews \
  --jq '.[] | {user:.user.login, state:.state, submitted_at:.submitted_at, commit_id:.commit_id}'
gh api repos/537Lab/PaperTrace/pulls/<测试PR号> \
  --jq '{head:.head.sha, merged_at:.merged_at, user:.user.login}'
```

核对：存在 `state=APPROVED`、reviewer 与实现 PR 作者不同、`submitted_at` 早于实现 PR 首个 commit、批准所指 SHA 与测试 PR head 一致、实现 PR 未改动测试文件（改了重新批准）。把输出 JSON 存进 `docs/reviews/`，由 reviewer 复核。

> **现在可做**：两步 PR 流程、PR 模板证据栏、轮值表、上面的只读校验命令。
> **必须等学生**：真实的非作者 Approve、真实的测试先行 PR。没有就保持 **BLOCKED**，不许用仓库内 `approved: true` 或本地时间戳代替。

### Gate 4 语义评估（semantic）

保留固定集 `test/evaluation/cases.json` 与 `report-schema.json` 不变，去掉「可信 CI 供应链 / OIDC / 不可替换验证器」这一层：

1. 学生先按 [../team/startup.md](../team/startup.md) 第 2 层取得 provider/model、数据范围、次数与金额批准（**学生本人批准并记录**，不是仓库内自写字段）。
2. 在自己的受控环境用真实 provider 跑固定集，产出 `docs/reviews/eval-<PR>-<head前7位>.json`：每个 case 的 `repeat`、实际发送 prompt SHA256、provider/model/version、真实 `input/output/total usage`、`finish_reason`、脱敏响应 SHA256、head SHA、dataset SHA256。失败/预算中止也保留记录，不静默换模型或加重试。
3. **独立 reviewer 按 rubric 逐条人工评分**（引用/支持度/矛盾处理/不确定性/中文表达），在 PR 里写明理由并 Approve；事实质量由人判断，不让模型自证。
4. 轻量校验只做**结构与绑定**：字段齐全、dataset SHA 匹配固定集、10 条全覆盖、usage 非空、head SHA 绑定当前 PR、reviewer ≠ 作者、阈值（安全逃逸=0、citation_precision=1.0 等）经学生批准冻结后才比较。校验器**不**声称证明输出真实性 —— 那由第 3 步的人工复核承担。

> **现在可做**：报告字段清单、rubric 表、PR 模板勾选项、结构校验规则、把「待批准预算计划」写成学生需确认的表格。
> **必须等学生**：provider/金额批准、真实调用与 usage、独立人工评分。缺任一项保持 **BLOCKED**；固定 mock 回复、跳过调用、仓库内自写 PASS 一律不接受。

### Gate 5 完整既往回归（regression）

把「full」从一个遥不可及的整体，拆成**三层可分别执行、分别记录**的清单：

| 层 | 内容 | 现在状态 |
|---|---|---|
| L1 团队离线 suite | `.venv/bin/python -m pytest -c papertrace.pytest.ini test/offline`（全部 170 项，无过滤），读 JUnit 确认 tests>0 且 0 failure/error/skip | **已真实通过**（本机 + GitHub Actions）。每次 PR 都跑 |
| L2 上游 prior suites（离线） | 在独立冻结环境 `uv sync --frozen` 后跑 `pytest -m 'offline and not live_api' tests`、`... packages`；先 `collect-only` 建立不丢失的 item 清单，保存 JUnit、版本指纹、代码/测试 SHA、前后差异 | **待第 1 层业务环境就绪**；本次因本机临时目录限制未能在本地验证，命令是合同而非已验证结果 |
| L3 live / 需模型范围 | 枚举需真实 API 的用例，单独申请数据、provider、次数与金额 | **BLOCKED**，未授权，不混入 L1/L2 结论 |

「完整既往回归」= L1 + L2（+ 获批准后的 L3）。**L2 没跑完、有 skip、有基线原有失败但未人审处理，就仍是 BLOCKED**，不能用 L1 的 170 项绿灯冒充。结果写入 `docs/reviews/regression-<sha>.md` 由 reviewer 核对。

> **现在可做**：L1 已跑；L2 的 collect-only 与 JUnit 归档命令、PR 模板勾选、轮值复核。
> **必须等学生**：装好完整业务依赖、真实跑完 L2、人审前后差异与 L3 授权。

### 另外三类（保持现状，无需新机制）

| 门禁 | 现状 | 说明 |
|---|---|---|
| 2 static | `static-analysis` = **success** | 初始化 scope 的 lint/类型/锁一致/冻结/AST/契约表面/机密启发式；完整供应链审计仍非本轮范围 |
| 3 schema | `schema` = **success** | 27 条 registry 结构校验；远端已真实执行 |
| 6 AI-use log | `ai-use-log` = **success** | 相对 base 的真实新增披露；不证明披露内容真实性，仍需人审 |

CI 首跑（[run 43434164875](https://github.com/537Lab/PaperTrace/actions/runs/43434164875)）真实结论：3 success / 3 failure(BLOCKED, exit 2)，整体 `failure` —— 这是**预期的 fail-closed**，不是配置错误。六个 job 名保持不变，便于日后设为 required checks。

## 三、分支保护限制的调研结论（不擅自升级、不公开）

**实测**：仓库 `537Lab/PaperTrace` 为私有、账号套餐为 GitHub Free。经典分支保护 API 与新版 Rulesets API（含仅禁强推的最小规则）均返回 `403 Upgrade to GitHub Pro or make this repository public to enable this feature`。

**官方文档口径**（2026-11-14 查证）：

- [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)：*“Protected branches are available in public repositories with GitHub Free… also available in public **and private** repositories with GitHub Pro, GitHub Team, GitHub Enterprise…”* → **免费套餐的私有仓库不支持**，`Require status checks before merging` 是保护规则的一项设置，同样受限。
- [GitHub's plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)：GitHub Pro / Team 在私有仓库提供 `Protected branches`、`Required pull request reviewers`、`Code owners`。
- [About GitHub Education for students](https://docs.github.com/en/education/about-github-education/github-education-for-students/about-github-education-for-students)：明确的学生 GitHub 自有权益是 **Copilot 免费**与 **Codespaces 每月 180 核心小时（配额等同 Pro）**；原文另写 *“a teacher can apply for GitHub Education so your team can collaborate using GitHub Team… **for free**”*。
- [Student Developer Pack](https://education.github.com/pack/) 页面当前**未把 “GitHub Pro” 列为权益名称**。社区/第三方资料称历史上包含 Pro，但官方页面没有明确表述 → **不能假定学生包一定给 Pro**，须由学生本人在 <https://github.com/settings/education/benefits> 核实自己账号实际获得什么。

**可行路径（按推荐顺序，均需学生/教师本人操作，本次一律不代做）**：

1. **最推荐：请课程教师申请 GitHub Education，为团队开免费 GitHub Team 组织**（官方文档明写教师可为团队免费取得 Team）。把仓库转入该组织后，私有仓库即可启用 protected branches、required reviewers、required status checks。零费用、最贴合五人团队。
2. 学生各自查看 Education benefits；若账号确实获得 GitHub Pro，则个人私有仓库可直接启用保护。**先核实，不假定**。
3. 自费 GitHub Pro（个人付费）—— 用户未授权，不执行。
4. 把仓库设为 public（Free 即支持保护）—— 上游论文/录制资料许可尚未逐件审查，且用户明确要求保持私有，**排除**。

在保护生效前：用 `.github/pull_request_template.md` 的六类证据清单 + 轮值人工 review + 六个 CI 检查的可见状态作为**流程约束**。必须明确：这**不构成强制合并拦截**，不能写成「门禁已生效」。

## 四、现在可做 / 必须等真实证据（对照表）

| 项 | 现在可做（本次已做或可立即采用） | 必须等学生产生真实证据 |
|---|---|---|
| Gate 1 | 两步 PR 流程、PR 模板证据栏、轮值表、`gh api` 只读核对命令 | 非作者 Approve、测试先行 PR、时序记录 |
| Gate 4 | 报告字段清单、rubric、结构校验规则、待批准预算表 | provider/金额批准、真实调用与 usage、独立人工评分 |
| Gate 5 | L1 已跑、L2 collect-only/JUnit 归档命令、PR 模板 | 完整业务依赖、L2 真实跑完、前后差异人审、L3 授权 |
| Gate 2/3/6 | 三个 CI job 已真实运行并 success | 供应链审计、披露真实性人审（课程完整范围） |
| 分支保护 | PR 模板 + 轮值复核作为流程约束（**非强制**） | 教师 Team 组织 / 学生 Pro 资格核实 → 真正启用规则 |
| BLOCKED 状态 | **保持** 3 项 BLOCKED，不改名、不改成 PASS、不加 `continue-on-error` | 只有上述真实证据齐全且复核通过，才由学生/教师改判定 |

**红线**：不得把 `test-approval`/`semantic-evaluation`/`regression` 改成 `PASS`、不得把 CI 的 `--scope full` 降级为 `initialization` 来骗绿、不得用 `continue-on-error` 掩盖失败、不得删掉未跑的用例。本轮修正**没有改动 `scripts/gates.py` 的判定逻辑，也没有改动 `.github/workflows/ci.yml` 的六个 job 与 scope**。

## 五、启用后的验收（学生执行）

1. 由教师/学生在具备 Pro/Team 的仓库启用：required status checks 选真实通过的 `static-analysis`、`schema`、`ai-use-log`（以及完成 L2 后的 `regression`）；`Required approvals ≥ 1`、dismiss stale reviews、禁止 force push。
2. **回读规则**确认生效（不能只凭设置页面宣称）：`gh api repos/<owner>/<repo>/branches/main/protection`。
3. 用**六类单点违规 PR 与合法对照**实证：无批准、自批、改测试后未重批、错 dataset SHA、L2 有 skip、缺 AI-use 披露、以及一份证据齐全的合法 PR。保留每个 PR 的 check 结果与 reviewer 结论。
4. 三门原 BLOCKED 门禁只有在真实证据齐全、人工复核通过后，才由学生按上述最小路线实现判定并留下记录；在此之前保持 BLOCKED。

相关：[gates.md](gates.md)、[README.md](README.md)、[事前批准原合同（严格参考）](test-approval.md)、[完整回归原合同](full-regression.md)、[真实评估合同](../../test/evaluation/README.md)、[新人启动流程](../team/startup.md)。
