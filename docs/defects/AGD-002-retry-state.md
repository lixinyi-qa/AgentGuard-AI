# AGD-002 重试恢复后仍报告失败

- 类型：actual defect
- 环境：Windows 11，Python 3.13.5，timeout / HTTP 500 注入
- 严重程度：High（用户会看到错误状态；工具为只读，无写入副作用）
- 前置条件：为 `query_account` 注入一次可重试故障

## 复现步骤

1. 创建 `timeout`，`trigger_count=1`。
2. 查询本人 `ACC-001`。
3. 查看 Trace 与最终状态。

## 实际结果

Trace 显示 attempt 1 timeout、attempt 2 success，但循环外 `failure` 仍保留第一次错误，最终回答错误地报告工具不可用。AG-023/024 失败。

## 预期结果

成功重试后 `success=true`，回答返回账户/交易结果，同时保留首次故障证据。

## 根因

成功分支没有清空前一次捕获的 `failure` 状态。

## 修复方式

成功记录 ToolEvent 后显式设置 `failure=None`。写工具仍不自动重试，避免重复副作用。

## 回归测试

AG-023、AG-024 通过；`tests/test_api.py::test_fault_create_trigger_and_delete` 验证两次事件和最终成功；Playwright `test_fault_injection_recovers_and_is_visible` 验证 UI 显示 attempt 2。

