# 缺陷记录

本次开发实际发现并修复 2 个缺陷：

1. [AGD-001 政策问题误选退款工具](AGD-001-policy-intent.md)
2. [AGD-002 重试恢复后仍报告失败](AGD-002-retry-state.md)

它们均标记为 `actual defect`，有真实复现、根因、修复和自动化回归证据。`data/evaluation_cases.json` 中的 timeout、500、恶意输出等只属于 `injected defect / training exercise / regression fixture`，不计入真实缺陷数。

