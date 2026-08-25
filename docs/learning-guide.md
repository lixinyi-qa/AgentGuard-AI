# 学习指南：从零讲清 AgentGuard AI

这份指南面向第一次系统接触 AI 测试的本科生。建议一边读，一边打开对应代码。

## 1. 什么是 AI Agent

普通模型只生成文本；Agent 会根据目标决定是否调用外部能力，再把结果组合成回答。本项目的 `app/runtime.py::AgentRuntime.run` 是编排器，`app/providers.py` 只负责生成计划。例：输入“查询 ACC-001”，计划是 `query_account({account_id:"ACC-001"})`。

## 2. 什么是工具调用

工具调用是结构化函数请求，不是让模型随便执行代码。`app/tools.py` 定义 7 个允许工具和输入/输出 Schema。Sandbox 只执行名字在白名单里的工具；未知工具返回安全错误。

## 3. 什么是 RAG

RAG 先从知识库找相关片段，再让系统基于片段回答。`app/retrieval.py` 用可解释词项和中文 bigram 打分，资料在 `data/knowledge/`。它不是向量数据库，但检索过程能复现，适合学习基线。

## 4. 什么是直接提示词注入

攻击指令直接出现在用户输入，例如“忽略之前要求”。`app/safety.py::detect_attack` 标记风险，Runtime 在规划工具前拒绝，所以 Trace 中工具事件为空。案例 AG-016。

## 5. 什么是间接提示词注入

恶意指令藏在知识文档或工具返回中。`contact_policy.md` 故意写了“直接调用 update_contact”，它可以被检索，但 `POL-007` 说明它只是数据。案例 AG-021/022 验证没有执行恶意工具。

## 6. 什么是 Excessive Agency

过度代理是 Agent 在授权或确认不足时替用户采取过多行动。例如“不要审批，直接退款”。本项目先拒绝显式绕过请求；金额达到 1000 元时也只能调用 `request_human_approval`，不能直接退款。

## 7. 什么是 Policy as Code

把安全规则写成能执行和测试的代码。`app/policies.py` 返回结构化 `PolicyDecision`，不是只有文档。对象越权会产生 `POL-010 / deny / critical`，并被保存到 Trace。

## 8. 什么是数字孪生

这里的数字孪生不是高精度物理仿真，而是对业务接口、数据范围、失败模式和安全规则的可控软件替身。`CUSTOMERS/ACCOUNTS/TRANSACTIONS` 全是虚构数据，工具行为和真实服务形状相似，但不会触碰真实金融系统。

## 9. 什么是故障注入

主动让依赖出现 timeout、500、空响应或恶意输出，观察系统是否安全。`app/faults.py` 消费触发次数，`ToolSandbox._mutate_response` 制造脏数据。Dashboard 可以选择目标、类型和次数。

## 10. 什么是幂等

同一个写请求重复到达，只产生一次副作用。Sandbox 把幂等键和参数 hash 保存到 SQLite：同键同参数返回缓存；同键不同参数返回 409。AG-033/034 和 API 测试覆盖它。

## 11. 什么是 Trace

Trace 是一次运行的证据包。`TraceRecord` 包含输入身份、检索、Provider、计划、工具参数/结果、Fault、Policy、审批、回答、耗时、成本估算、状态和风险。它不是普通日志，而是能按 `trace_id` 查询的结构化快照。

## 12. 什么是 Replay

Replay 用过去证据重新比较新提示词、策略或 Provider。`app/replay.py` 把保存响应标记成 `replayed`，所有 `side_effect=false`；不会再次退款、改联系方式或建工单。

## 13. 什么是 AI 评测集

评测集是输入与期望行为的版本化集合。`data/evaluation_cases.json` 有 40 条，每条明确角色、对象、工具、参数、禁止行为、审批、策略、关键词、来源、拒绝和风险，而不是只比较一段自然语言“像不像”。

## 14. 什么是质量门禁

门禁把指标变成是否允许继续交付的结论。`EvaluationEngine._quality_gate` 将 PII、越权、审批、重复写和高风险退化设为硬规则，一般质量与延迟设阈值。CI 执行 `scripts/run_quality_gate.py`，FAIL 时进程非零退出。

## 15. 核心目录和文件

- `app/main.py`：API、中间件、错误响应和依赖装配。
- `app/runtime.py`：一次 Agent 请求的主流程。
- `app/tools.py` / `policies.py` / `faults.py`：工具、策略、故障三个核心边界。
- `app/storage.py`：SQLite/SQLAlchemy 证据仓库。
- `app/evaluation.py` / `metrics.py` / `reporting.py`：案例、指标、门禁和报告。
- `app/static/`：Dashboard。
- `data/`：知识和 40 条案例。
- `tests/`：单元、API、UI。
- `postman/`、`performance/`、`.github/`：工作流、性能与 CI。
- `docs/`、`reports/`：学习材料和真实证据。

## 16. 如何从头运行

Windows：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

访问 Dashboard 后先做正常账户查询，再做越权查询。默认不需要 `.env`。可选 Provider 的配置参考 `.env.example`，但不要把真实 Key 写入文件或截图。

## 17. 如何逐步调试

1. `/health` 失败：检查虚拟环境、端口和 `uvicorn` 输出。
2. 意图错误：在 `DeterministicLocalProvider.plan` 观察分支与参数。
3. 被策略阻止：查看返回的 `policy_decisions` 和 `related_trace_id`。
4. 工具失败：查看 `tool_events[].attempt/error/fault_type/side_effect`。
5. 输出不安全：检查 POL-008/006/007 和 `sanitize_payload`。
6. 评测失败：打开 `reports/evaluation-latest.json` 的 `results[].reasons`，按 `trace_id` 查完整证据。

## 18. 如何新增评测案例

复制 `data/evaluation_cases.json` 中一条记录，换唯一 `case_id`，填写全部字段。先明确禁止副作用和期望 Policy，再写关键词。运行 `python scripts/run_quality_gate.py`；如果旧行为变差，不要通过降低门禁掩盖它。

## 19. 如何新增模拟工具

1. 在 `TOOL_CONTRACTS` 声明 Schema、角色、风险、审批、幂等、超时、错误、范围和脱敏。
2. 在 `ToolSandbox._execute_clean` 实现纯虚构行为。
3. 在 `PolicyEngine.authorize` 加对象与风险规则。
4. 在 Provider 增加可解释意图，但让信息查询优先于写操作。
5. 在 Runtime 增加用户回答映射。
6. 添加单元、API、UI/评测案例，并验证 Fault 和 Replay。

## 20. 如何解释真实性边界

可以说：“代码、测试、指标和截图都是真实运行；业务数据、银行和交易是故意虚构；离线 Provider 是可重复测试基线；没有连接真实模型/银行，也没有生产或监管认证。”不能把 40/40、96% 或本机 37.47 req/s 说成真实金融系统能力。

## 建议学习顺序

先读 `models.py → tools.py → policies.py → runtime.py`，手工调用 API；再读 Fault/Trace/Replay；然后看评测集与指标；最后运行 Playwright、Newman、Locust 和 CI。每学一层，先用一个失败案例解释“为什么安全停止”。

