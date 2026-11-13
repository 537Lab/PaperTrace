# Live tests：待功能开发与另行授权

此目录不是已通过的测试套件；目前没有业务adapter、真实模型测试或提供商凭据注入配置，不能运行空目录并报告PASS。默认初始化不调用模型、不读取API key，`test/offline`与live严格分离。

成员完成A–E业务后，为真实adapter添加可定位到需求ID的正负live用例，取得独立学生审核、计划及事前测试批准。调用前批准provider/model/version、合成数据范围、次数、单次timeout、最大金额及中止策略，密钥从受控服务注入但不存仓库/转录/报告。使用`test/evaluation/README.md`约定保存输入/prompt/source/test哈希、真实content/usage/finish_reason及费用。初始化门禁不接受仓库内自行声明的批准。

完整既往回归必须覆盖上游`tests/`、`packages/*/tests`及所有团队历史套件，见`docs/ci/full-regression.md`。只有离线契约通过不代表PaperQA2集成、live或语义质量通过。
