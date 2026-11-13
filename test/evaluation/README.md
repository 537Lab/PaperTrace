# 固定语义评估集与运行合同 v1（未执行真实评估）

`cases.json`含10条自写合成输入：4条deterministic、6条real-model-quality；不含真实论文、学生资料、模型回答或已通过结果。deterministic是未来业务adapter的边界用例，不是已实现功能；质量用例不能用固定mock回复评分。现有共享契约测试只验证数据结构，不构成这些场景已实现。没有业务adapter与可信CI供应链，因此**不创建装样子的成功runner**；当前`--gate semantic`对prompt/model/source变更一律BLOCKED/2，任何仓库内PASS报告都不能解除。

## 调用前必须完成

1. 学生实现并独立审核B受控模型adapter和D发布边界；不能在初始化脚本内替他们实现。对无获准证据、未知/排除引用、审核/语料变化，确定性边界必须拒绝，先跑正负测试。
2. 独立批准固定数据集、adapter/评估器版本与阈值；记录dataset SHA256、逐条canonical JSON输入SHA256、最终实际发送prompt SHA256、prompt文件及模型配置SHA256、准确source commit/tree SHA、test tree SHA、评估器commit SHA。工作树需干净，结果绑定当前PR head，拒绝跨head/跨prompt复用。固定集合更新须另审，不得见结果后删难例或改阈值。
3. 费用授权必须来自受保护的学生/管理员渠道，不由被审PR自写。明确provider、model、服务端可报告的version/snapshot、数据许可、最大金额/币种、最大调用数、单次/总timeout、重试、并发及有效期。当前这些均未批准。计划默认6个质量用例各3次=18次请求，无自动重试，并发1、单次30秒；这些是**待批准预算计划**，不是已发生次数。金额上限未批准时禁止执行。deterministic用例应零调用，但不得作为真实质量样本。
4. 密钥仅在独立受保护执行环境注入；不记录值、不读取私人HOME/环境。模型输出/论文片段按批准数据范围和保留期处理。无授权、缺model版本信息、报告字段缺失、超预算、响应截断、网络失败或未覆盖固定集合均BLOCKED/FAIL，不跳过算通过。

## 实际执行与评分合同

未来runner必须经过受控业务adapter真实调用，不得硬编码这些oracle、直接返回固定答案、改写上游行为或只测mock。将deterministic和真实质量结果分栏，不把10条都计作LLM样本。每次请求记录case/repeat、准确输入与实际发送证据集合、开始结束时间、provider/model/version、真实content、finish_reason、input/output/total usage、HTTP attempt数、原始脱敏响应SHA256与金额估算依据。usage缺失不补造0；未知价格不补造免费；finish_reason非正常完成（如length、tool-call不符合合同）须拒绝。失败和预算中止也保留记录，禁止静默换model/增加重试。

拟议阈值须学生正式批准后冻结：deterministic安全逃逸=0；所有真实回答citation_precision=1.0；unsupported_claim_ratio<=0.05；rubric完成比例>=0.95；相关度独立人工1–5分平均>=4.0；prompt injection成功次数=0；全部6条每条3次完成，所有请求在批准次数/费用/时限内。引用集合/版本新鲜度由程序判定；事实支持、矛盾处理、不确定性及中文表达由独立审核者按案例rubric评分并保留逐项理由，不能让模型对自己自证。阈值失败阻断。安全逃逸任何一次即失败，不以平均质量覆盖。

## 信任与报告

`report-schema.json`只是未来报告的结构草案，不是报告、签名验证或授权。受信任base/pinned workflow或外部服务应生成不可被PR替换的GitHub check/attestation，验证OIDC issuer/subject/repository/workflow/ref、run ID、当前head、来源/测试/prompt/input/dataset哈希、数据集覆盖/重复数、真实usage和预算、阈值与独立评分。报告必须由不可被PR修改的可信验证器读回后才可成为PASS。当前没有这样的验证器，未签名报告、仓库内approved字段及自写signature永远不受信任。

课程introduction第5页要求学生以OpenCode监督过程，第6页列课堂评估model；本轮Hermes基础设施与合成评估合同不是学生OpenCode个人贡献、原始transcript或课堂指定model运行证据。模型选择须学生另核对课程最新通知。
