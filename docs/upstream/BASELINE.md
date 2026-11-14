# 上游基线与本轮边界

来源：https://github.com/Future-House/paper-qa
固定提交：`c692d0dfeac4a0296599f7fe21a253a58b7ac12a`。
本地tag：`papertrace-upstream-baseline`。完整原Git历史保留；团队初始化是它的后继提交，不冒充原作者。`src/paperqa/`、`packages/`、原`tests/`、`pyproject.toml`、`uv.lock`、`LICENSE`本轮不变。

原README原字节保存在`README.paperqa.md`；原GitHub工作流原字节保存在`workflows/`并采用`.disabled`后缀，不在Actions自动执行，避免继承发布/提供商凭据流程。根README与`.github/workflows/ci.yml`属于团队新增治理界面；这些布局改变单独记录，不称上游核心修改。

仅保留只读upstream fetch remote；push URL为`disabled://papertrace-read-only-upstream`，`push.default=nothing`。经用户 2026-11-13 明确授权后，已设置团队 `origin` = https://github.com/537Lab/PaperTrace（私有）并推送 main 与 3 个 `papertrace-*` 标签；完整上游历史与基线 SHA 保留。分支保护未生效（免费套餐 403）。

版权/许可证以各包LICENSE为准。上游历史夹带论文/录制响应不自动获得再分发许可；本机保全不等于获准上传。本轮团队材料包不含上游论文、原课程PDF、API录制、.git或任何凭据。上传完整仓库前必须按`docs/licenses/license-review.md`审查再分发范围。
