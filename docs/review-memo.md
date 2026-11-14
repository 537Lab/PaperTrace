# PR审查索引（D4）

初始化提交时团队仓库尚未创建；现已建立私有仓库 https://github.com/537Lab/PaperTrace。本轮仍没有学生 PR，也没有学生人工 APPROVE。此文件只索引真实发生的审查，不能替代GitHub审批。

每PR在`docs/reviews/PR-<编号>.md`记录：需求/fit criterion与变更范围；架构/INV对齐；实现及正常/负面测试质量；安全/权限/效率；操作元数据（基线/HEAD、工具、命令、依赖、模型与费用授权、真实运行和未运行）；发现与处置；独立审查者真实结论APPROVE/CHANGES REQUIRED/REJECT。批准要绑定实际版本，不能由作者改文档自证。

本轮初始化及工程解阻的交付检查见`INITIALIZATION_STATUS.md`及`artifacts/verification/unblock-*`；主控已复跑全部250离线测试和真实PaperQA API smoke。独立AI复核发现base信任、live标记删除、runxfail等缺口，已用负例修复。其性质是AI辅助工程核验，不是课程要求的真人审批。
