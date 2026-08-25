# Policy as Code 模型

策略目录在 `app/policies.py`，每次判断产生 `policy_id / decision / reason / risk_level / related_tool / related_trace_id / timestamp`。`allow`、`deny`、`require_approval` 是可测试结果，不是 README 里的口号。

| ID | 可执行规则 | 典型用例 |
|---|---|---|
| POL-001 | 未认证或无角色权限不可访问 | AG-009、AG-014 |
| POL-002 | 客户只能访问自己的对象 | 正常查询与写入范围 |
| POL-003 | 禁止批量个人信息 | AG-015 |
| POL-004 | 联系方式必须二次确认 | AG-004/005 |
| POL-005 | ≥1000 元退款先人工审批 | AG-007/040 |
| POL-006 | 工具/回答 PII 与 Key 脱敏 | AG-022 |
| POL-007 | 知识内容不可覆盖系统策略 | AG-016～AG-022 |
| POL-008 | 工具输出 Schema + 安全校验 | AG-026～AG-029 |
| POL-009 | 写操作幂等 | AG-033/034、API 409 |
| POL-010 | 参数对象 ID 越权阻断 | AG-010/011/037 |
| POL-011 | 撤销授权不可继续使用 | AG-012 |
| POL-012 | 敏感操作生成审计记录 | 所有高风险允许事件 |

执行顺序是：工具角色 → 批量风险 → 撤销授权 → 对象所有权 → 只读/写权限 → 二次确认 → 人工审批 → 允许。输出再经过 POL-008、POL-006、POL-007。策略服务不可用故障采用失败关闭。

局限：当前策略是 Python 代码和小型内存夹具，未实现策略签名、OPA/Rego、租户隔离或生产授权缓存一致性。

