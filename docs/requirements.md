# 需求与范围

## 目标

AgentGuard AI 用于展示 AI 智能体质量工程能力：测试任务理解、工具选择与参数、角色和对象权限、人工审批、PII、提示词注入、故障恢复、回归与审计证据。

## 功能需求

系统提供 7 个虚构工具、12 条可执行策略、15 类故障、6 类知识政策与恶意回归语料、Trace/Replay、40 条版本化评测、18 项核心指标、Quality Gate、运行历史、JSON/HTML 报告和 Web Dashboard。API 契约以 `/openapi.json` 为准。

## 非功能需求

- Python 3.11+；默认 SQLite 和离线 Provider，零凭据启动。
- 统一错误响应与请求 ID；写操作幂等；输出、Trace 和审计日志脱敏。
- 基本键盘可达、焦点可见、触控尺寸和 390px 响应式布局。
- pytest、Playwright、Postman/Newman、Locust 与 GitHub Actions 可重复执行。

## 范围外

真实银行/支付/短信/征信/身份连接、真实个人数据、生产容量、金融监管认证、外部渗透测试、完整大模型智能、分布式事务和 PostgreSQL 实测均不在本版本范围内。

## 验收追踪

| 需求 | 代码/证据 |
|---|---|
| 工具与对象权限 | `app/tools.py`、`app/policies.py`、`tests/test_unit.py` |
| 运行、Trace、Replay | `app/runtime.py`、`app/storage.py`、`app/replay.py` |
| 故障注入 | `app/faults.py`、Dashboard、AG-022～AG-036 |
| 评测与门禁 | `app/evaluation.py`、`data/evaluation_cases.json`、`reports/evaluation-latest.json` |
| API/错误 | `app/main.py`、`tests/test_api.py` |
| UI/可访问性 | `app/static/`、`tests/test_ui.py`、`docs/assets/*.png` |
| CI/报告 | `.github/workflows/ci.yml`、`app/reporting.py` |

