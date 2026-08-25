# 架构说明

![Architecture](assets/architecture.svg)

## 一次请求如何流动

1. FastAPI 中间件生成 `request_id` 并进入 Agent Runtime。
2. KnowledgeBase 做可解释的词项检索；恶意文档允许被检索，但标记为 untrusted。
3. Provider 只生成工具计划。默认规则 Provider 可重复；可选 OpenAI Provider 使用 Responses API。
4. Policy Engine 在执行前检查角色、对象所有权、撤销授权、二次确认和审批。
5. Tool Sandbox 校验参数、幂等键并执行虚构工具；Fault Engine 可在边界处注入异常或污染输出。
6. 输出经过 Schema、注入和 PII 检查，只把脱敏值写入 Trace。
7. SQLite 保存 Trace、Fault、Evaluation、Idempotency 和 Audit；Dashboard 使用同一 API 展示证据。
8. Replay 复制已保存工具响应，所有事件标记 `replayed` 且 `side_effect=false`。
9. Evaluation 将 40 个案例转为确定性断言和启发式评分，Quality Gate 给出 PASS/FAIL。

## 设计取舍

- 未引入复杂 Agent 框架：关键决策能在本科生面试中逐行解释。
- SQLite 是零配置默认；Store 边界允许以后换 PostgreSQL，但本版本未声称已适配验证。
- HTML/CSS/JS 避免前端构建链；Playwright 仍能覆盖真实交互。
- Tool 响应先保存脱敏结果，牺牲原始取证细节来避免日志泄密；真实系统应在受控加密审计域保存必要原始证据。

## 数据模型

`TraceRecord` 是主证据：输入身份、检索内容、Provider、计划、工具事件、Fault、Policy、审批、回答、耗时、Token/成本估算、成功与风险标签。SQLAlchemy 表把 Pydantic JSON 作为稳定快照存储，并单独维护幂等与审计表。

