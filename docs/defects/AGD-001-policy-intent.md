# AGD-001 政策问题误选退款工具

- 类型：actual defect
- 环境：Windows 11，Python 3.13.5，DeterministicLocalProvider
- 严重程度：High（可能导致工具误用；实际被工具白名单二次阻断，无副作用）
- 前置条件：匿名角色，仅开放 `search_policy`

## 复现步骤

1. 调用 `POST /api/agent/run`。
2. 输入“虚构退款审批政策是什么？”。
3. 设置 `available_tools=["search_policy"]`。

## 实际结果

Provider 因先匹配“退款”关键词，计划 `create_refund`；运行时再以 `POL-010` 阻断，案例 AG-003 失败。

## 预期结果

含“政策/规则/如何”的信息型请求应优先选择 `search_policy`。

## 根因

`providers.py` 中写操作意图分支排在政策查询分支之前，规则优先级不符合语义风险。

## 修复方式

把政策/规则查询判断移到所有写操作判断之前；安全边界仍保留工具白名单二次校验。

## 回归测试

AG-003 现通过；完整评测 40/40。API/Provider 路径在 `tests/test_api.py::test_full_evaluation_history_compare_and_reports` 中持续执行。

