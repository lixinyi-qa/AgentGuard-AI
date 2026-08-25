# 数字孪生工具契约

完整机器可读契约由 `GET /api/tools` 和 `app/tools.py` 提供。每个工具都声明描述、输入/输出 JSON Schema、角色、高风险/审批、幂等、超时、错误、数据范围和脱敏规则。

| 工具 | 角色摘要 | 风险/审批 | 幂等 | 数据范围 |
|---|---|---|---|---|
| `search_policy` | 所有角色 | 低/否 | 不需要 | 公开虚构政策 |
| `query_account` | customer、客服、审计、管理员 | 低/否 | 不需要 | 单个授权账户 |
| `query_transaction` | customer、客服、审计、管理员 | 低/否 | 不需要 | 单笔授权交易 |
| `update_contact` | customer、管理员 | 高/二次确认 | 必需 | 本人客户对象 |
| `create_refund` | customer、客服、管理员 | 高/≥1000 元人工审批 | 必需 | 授权交易 |
| `create_ticket` | customer、客服、管理员 | 低/否 | 必需 | 授权客户 |
| `request_human_approval` | customer、客服、管理员 | 中/自身不需审批 | 必需 | 授权动作 |

写工具以 `tool + arguments` 计算 payload hash。同一键同一请求返回缓存且 `side_effect=false`；同一键不同请求返回 HTTP 409。只读工具对 timeout/500/429 最多重试 2 次（总尝试 3 次），写工具不自动重试。

所有银行、客户、账户、交易和工具结果均为虚构夹具。这里的 timeout 是测试契约，不代表真实银行接口 SLA。

