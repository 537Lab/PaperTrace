# 六类门禁：初始化运行合同

来源：`docs/sources/materials-manifest.json` 所列本学期 Project Requirement Sheet 第10页（六类及分支保护）；第6页D4要求每轮完整既往套件。本地脚本不等于GitHub已部署。

## 现在能运行什么

在仓库根目录、独立初始化虚拟环境中运行：

```sh
.venv/bin/python scripts/gates.py --gate schema --base c692d0dfeac4a0296599f7fe21a253a58b7ac12a
.venv/bin/python scripts/gates.py --gate static --scope initialization --base c692d0dfeac4a0296599f7fe21a253a58b7ac12a
.venv/bin/python scripts/gates.py --gate ai-log --base c692d0dfeac4a0296599f7fe21a253a58b7ac12a
.venv/bin/python scripts/gates.py --gate regression --scope initialization --base c692d0dfeac4a0296599f7fe21a253a58b7ac12a
.venv/bin/python scripts/gates.py --gate all --scope initialization --base c692d0dfeac4a0296599f7fe21a253a58b7ac12a
```

省略`--head`检查当前工作树（包括已暂存、未暂存、删除和未跟踪文件）。提交后使用`--head`加完整40位小写SHA；base须是head的祖先，不能用缩写、分支名或悄悄修复大小写。静态/回归执行前要求工作树输入与head一致。固定上游完整性比较始终对上述课程审计基线，不随PR base滚动。

所有输出为单个JSON：`schema_version/scope/target/status/exit_code/results/full_course_status/remote_enforcement`。退出码0=选定本地范围通过或确无触发变化，1=已发现失败，2=被缺少可信证据/授权/环境阻断。NOT_REQUIRED仅用于差异证明没有适用变化，不代表运行过评估。`all`即使局部离线通过，也不能返回0掩盖未部署的课程门禁。

|课程门禁|本地实现及真实范围|完整课程状态|
|---|---|---|
|1 test approval|差异识别；拒绝PR自写批准|BLOCKED：可信事前批准渠道未部署|
|2 static|ruff团队路径、mypy团队包、25项初始化依赖版本/闭包、AST导入边界、五契约API存在、受控新增文件秘密启发式、原版源码/包/测试/锁字节完整性|初始化检查可PASS；完整漏洞/运行时权限/API集成审计仍BLOCKED|
|3 schema|实际JSON Schema；唯一ID；不变量严格`== 0`；上游来源路径/行范围可定位|本地可PASS；远端未验证|
|4 semantic|prompt/model/source变化保守触发；不接收仓库内自写PASS|BLOCKED：真实adapter、费用授权与可信评估供应链未部署|
|5 regression|initialization实际运行整个`test/offline`，无过滤；失败/报错/skip/空集合均不认证|full永远不能用此结果替代上游`tests`、`packages`、live和全部既往团队套件|
|6 AI log|相对base新增语义日志项；已有项保留；只重排/只存在文件不通过|本地可PASS；不证明披露真实性或学生贡献|

静态命令只检查团队新增路径，不重写原版的静态配置、测试或依赖。子进程有超时，使用无提供商变量、隔离HOME的白名单环境，pytest禁用socket；这不是对恶意Python/OS进程的安全沙箱。秘密扫描不读私人目录或凭据文件，不输出命中值；仅启发式，不能认证秘密不存在。工具失败返回码及输出摘要保留在JSON，避免把含秘密的源码行复制到CI日志；需要诊断时在受控本地直接运行对应工具。

## GitHub工作流与远端真实边界

`.github/workflows/ci.yml`提供六个稳定job：`test-approval`、`static-analysis`、`schema`、`semantic-evaluation`、`regression`、`ai-use-log`，workflow名为`gates`。push（每次提交）与pull_request均运行；无路径skip/continue-on-error，无pull_request_target，不传提供商密钥，不触发收费评估。actions版本固定为官方tag查询得到的commit SHA，checkout不保留凭据，顶层权限仅contents:read。安装初始化锁需要包下载；这不是离线安装或软件供应链审计。

远端 https://github.com/537Lab/PaperTrace 已建立并真实运行六个 job（[首跑](https://github.com/537Lab/PaperTrace/actions/runs/43434164875)：static/schema/ai-log success；test-approval/semantic-evaluation/regression BLOCKED exit 2）。**分支保护、required checks、CODEOWNERS/独立审批规则、失败 PR 演示均未生效/未做**：经典保护 API 与 Rulesets API 均返回 403（免费套餐私有仓库限制）。管理员部署后必须回读规则，并创建真实失败PR核对阻断；不能仅凭本文件宣称生效。PR可修改工作流和门禁脚本，因此现有PR-head工作流**不具抗绕过保证**。正式部署需组织规则/受信任base或外部固定workflow、不可由被审PR替换的验证程序、独立受保护审批来源和禁止自行批准的权限；所有安全路径需ADR及人审。action SHA固定不等于工作流本身不可被PR替换。

**学生团队最小落地方案见 [minimal-gates.md](minimal-gates.md)**（用 GitHub PR 事件与轮值人工复核替代企业级认证系统）；严格参考合同见[事前批准](test-approval.md)、[完整回归](full-regression.md)与[语义运行](../../test/evaluation/README.md)。
