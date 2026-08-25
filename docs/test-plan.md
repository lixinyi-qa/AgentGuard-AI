# 测试计划

## 范围与策略

目标是证明离线智能体链路能运行，并对工具契约、权限、安全、故障、Trace/Replay、评测门禁和 Dashboard 建立分层证据。

| 层级 | 覆盖 | 工具 | 通过准则 |
|---|---|---|---|
| 单元 | Schema、Policy、对象权限、PII/注入、Fault、幂等、指标、序列化、Replay、Gate | pytest | 全部通过 |
| API | health、运行、422/404/409、越权、审批、Fault、Trace/Replay、Evaluation/Compare/Report | TestClient | 全部通过，错误不泄露内部信息 |
| UI | 加载、正常/越权、Fault、Evaluation、Trace、Compare、Download、Focus、Mobile | Playwright | 全部通过，0 控制台错误 |
| 工作流 | 变量链传递和端到端 API 顺序 | Postman/Newman | 0 请求/断言失败 |
| AI 评测 | 40 条版本化案例、18 指标 | Evaluation Engine | Quality Gate PASS |
| 性能 | 只读 Agent、Trace、评测历史 | TestClient + Locust | 0 失败；仅记录本机基线 |
| 安全卫生 | Key/Token/密码、数据库、缓存、大文件 | `rg`、Git 状态 | 不提交真实凭据/运行库 |

## 环境

实际验收环境：Windows 11、Python 3.13.5、Node 24.12.0、pytest 8.4.2、Playwright 1.62（复用本机 Chrome）、Newman 6.2.1、Locust 2.46.4。Docker 不可用，因此只提供配置，未实测。

## 入口/退出准则

入口：依赖可安装、FastAPI 可导入、虚构数据可加载。退出：项目启动、47 项 pytest 通过、40/40 评测、硬门禁通过、Newman 0 失败、性能请求 0 失败、3 张真实截图、文档与安全扫描完成。

## 缺陷规则

只有开发中真实复现的问题可写为 `actual defect`。Fault 数据只写 `injected defect / training exercise / regression fixture`，不计真实缺陷数量。真实缺陷见 `docs/defects/`。

## 风险

规则 Provider 可能让测试看起来过于稳定，因此不把 100% 指标外推到真实大模型。浏览器、Node、Docker 与网络依赖可能受环境影响；CI 会从干净依赖重新执行。

