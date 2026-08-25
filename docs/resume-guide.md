# 简历表述指南

## 可以写（以实际仓库为证）

**AgentGuard AI｜AI 智能体质量保障平台｜Python/FastAPI/SQLAlchemy/pytest/Playwright**

- 设计 7 个虚构金融业务工具及 12 条可执行安全策略，覆盖角色 + 对象级权限、二次确认、高额退款人工审批和写操作幂等；越权与审批评测阻断率均为 100%。
- 实现 15 类故障注入、脱敏 Trace 和零副作用离线 Replay，验证超时/500/429、脏数据、恶意输出、重复回调与安全降级。
- 构建 40 条版本化 AI Agent 评测集和 18 项核心指标，质量门禁实际运行 40/40 通过、PII 泄漏 0；明确区分确定性断言与启发式 Groundedness。
- 编写并实际执行 41 项单元/API 与 6 项 Playwright UI 测试，`app` 覆盖率 96%；Newman 11/11 断言、Locust 本机 335 请求零失败。
- 完成中英文文档、威胁模型、缺陷闭环、GitHub Actions、Docker 配置和真实运行截图。

投不同岗位时挑 2～3 条：软件测试突出分层用例和缺陷；AI 测试突出注入/评测/回归；金融科技突出对象权限/审批/幂等；测试开发突出代码与 CI。

## 暂时不能写

- “接入真实银行/支付/监管系统”或“达到生产/金融监管认证”。
- “真实大模型准确率 100%”或“Groundedness 等于事实准确率”。
- “支持 PostgreSQL/Docker/Kubernetes 生产部署”（Docker 仅配置，未在本机执行）。
- “高并发生产容量 37.47 req/s”；只能写“本机 5 用户 10 秒演示基线”。
- “已上线 GitHub Actions/公开仓库”（远端尚未创建和运行）。
- “精通 AI 安全/分布式系统/金融合规”。

## 面试携带证据

README、架构图、`reports/evaluation-latest.json`、覆盖率 HTML、三张截图、两份 actual defect 报告，以及现场 3 分钟演示。

