# AgentGuard AI

> 用数字孪生、Policy as Code、故障注入和可重放 Trace，为会调用工具的 AI 智能体生成可复现、可审计的质量证据。

[English](README_EN.md) · [学习指南](docs/learning-guide.md) · [面试指南](docs/interview-guide.md) · [测试计划](docs/test-plan.md)

![AgentGuard AI Dashboard](docs/assets/dashboard.png)

## 为什么它不是普通聊天机器人

普通聊天演示关注“回答像不像人”。AgentGuard AI 关注的是：智能体选了哪个工具、参数是否正确、对象是否属于当前用户、高风险写操作有没有先审批、依赖故障时有没有错误声称成功、升级后有没有发生安全退化。每次运行都有 `trace_id`，可离线重放并进入质量门禁。

项目模拟一个**完全虚构**的银行与企业服务智能体。7 个沙箱工具可以检索政策、查询虚构账户/交易、修改虚构联系方式、创建虚构退款/工单和请求人工审批。默认 `DeterministicLocalProvider` 不需要 API Key，能稳定复现实验；可选 Provider 使用官方 OpenAI Python SDK 的 [Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create)，且密钥只读环境变量。

## 架构

![AgentGuard AI architecture](docs/assets/architecture.svg)

```mermaid
flowchart LR
    U[User / Dashboard] --> A[Agent Runtime]
    A --> R[Knowledge / RAG]
    A --> P[Policy Engine]
    P --> T[Tool Sandbox]
    F[Fault Injection] --> T
    A --> X[(Trace + Audit Store)]
    T --> X
    X --> RP[Offline Replay / Compare]
    X --> E[Evaluation Engine]
    E --> Q{Quality Gate}
    Q --> D[Dashboard / JSON / HTML / CI]
```

核心模块见 [架构文档](docs/architecture.md)。

## 核心创新

- **可执行的双层授权**：角色权限之外，还校验账户、交易、客户 ID 的对象所有权；撤销授权立即失败关闭。
- **故障不是文档里的列表**：Dashboard 可为目标工具注入 15 类异常，Trace 会记录尝试次数、失败类型和副作用。
- **安全的离线 Replay**：重放使用保存且脱敏的工具响应，高风险写操作永远不会再次执行。
- **恶意知识也能被检索**：回归语料真实进入 RAG 结果，但知识内容没有系统权限，不能覆盖 Policy。
- **硬门禁与普通阈值分离**：PII 泄露、越权、审批、重复写和高风险退化是硬失败；Groundedness 明确标注为启发式。
- **证据链完整**：API、SQLite Trace、评测结果、JUnit、覆盖率、Newman、Locust、JSON/HTML 报告和截图互相可追溯。

## 3 分钟快速运行

Windows PowerShell：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

打开 <http://127.0.0.1:8000>。无需 `.env`、Docker 或 API Key。

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Docker 是可选路径：`docker compose up --build`。本次 Windows 实机没有 Docker，因此 Docker 配置已静态检查但未实际构建；这项不能写成已验证结果。

## 演示路径

1. 保持 `customer / CUST-001 / ACC-001`，点击“执行并记录 Trace”，展示正确工具和两个 ALLOW 决策。
2. 点击“填入越权示例”再执行，展示 `POL-010` 阻断且 `side_effect=false`。
3. 给 `query_account` 注入一次 `timeout`，再次执行，展示 attempt 1 失败、attempt 2 成功。
4. 点击“离线重放当前 Trace”，说明保存响应被复用、写操作不会重做。
5. 运行 40 条评测，展示 Quality Gate、失败列表、版本对比和报告导出。

![Trace timeline](docs/assets/trace.png)

![Fault injection recovery](docs/assets/fault-injection.png)

## 测试命令

```powershell
# 单元 + API + 覆盖率
pytest tests/test_unit.py tests/test_api.py --cov=app --cov-report=term-missing --cov-report=html

# Playwright UI（先安装浏览器；本机验收复用了已有 Chrome）
python -m playwright install chromium
pytest tests/test_ui.py -m ui

# 评测与硬门禁
python scripts/run_quality_gate.py

# Postman/Newman：先在 8000 端口启动 API
npm install
npm run test:postman

# 本机顺序性能基线
python scripts/performance_baseline.py

# 逐类故障证据
python scripts/run_fault_matrix.py

# Locust 示例：先启动 API
locust -f performance/locustfile.py --headless -u 5 -r 5 -t 10s --host http://127.0.0.1:8000
```

## 2026-08-25 实际验证结果

这些数字来自本仓库当次实际运行，不是目标值：

| 验证项 | 实际结果 |
|---|---:|
| 单元 + API | 41 passed / 0 failed / 0 skipped |
| Playwright UI | 6 passed / 0 failed / 0 skipped |
| 合计 pytest 用例 | 47 passed |
| `app` 覆盖率（单元 + API） | 96%（942 statements，35 missed） |
| AI 智能体评测 | 40/40 passed |
| Quality Gate | PASS，0 hard failures，0 soft failures |
| PII Leak Count | 0 |
| 越权阻断 / 人工审批 / 注入阻断 | 100% / 100% / 100% |
| 评测 P95 | 10.52 ms（`evaluation-latest.json`；不同运行会波动） |
| Newman | 11 requests、11 assertions、0 failed |
| 15 类 Fault Matrix | 15/15 安全观察，0 次错误成功声明 |
| 顺序性能基线 | 每接口 100 次，300 请求，0 failed |
| Locust 本机基线 | 5 users / 10s / 335 requests / 0 failed / 37.47 req/s / 聚合 P95≈83 ms |
| 浏览器控制台 | 0 error / 0 warning |

可核验文件：[`reports/evaluation-latest.json`](reports/evaluation-latest.json)、[`reports/performance-baseline.json`](reports/performance-baseline.json)。指标公式、阈值和局限见 [评测方法](docs/evaluation-methodology.md)。

## API

主要端点：`GET /health`、`GET /api/tools`、`GET /api/policies`、`POST /api/agent/run`、Trace 查询/重放、Fault CRUD、Evaluation 运行/比较、JSON/HTML 报告。交互式契约在 `/docs`。

所有错误返回统一的 `code / message / request_id`；404、409、422、500 不返回堆栈、文件路径或密钥。

## 项目结构

```text
app/                 FastAPI、运行时、策略、工具、故障、Trace、Replay、评测
app/static/          可用 Dashboard（HTML/CSS/JS）
data/knowledge/      6 类虚构政策与恶意回归语料
data/evaluation_cases.json  40 条版本化案例
tests/               单元、API、Playwright UI
postman/             顺序集合与环境变量链
performance/         Locust 场景
scripts/             Quality Gate 与本机基线入口
docs/                架构、威胁、策略、测试、学习与面试材料
reports/             小型可审计运行结果；临时 XML/CSV 默认忽略
.github/workflows/   CI 质量门禁与证据上传
```

## 安全边界与真实性声明

- 所有银行、客户、手机号、邮箱、身份证、账户、交易、退款、审批和政策都是虚构回归数据。
- 项目不会连接真实银行、支付、短信、征信或身份系统，也不代表通过金融监管或生产认证。
- 离线 Provider 是为智能体编排和测试链路提供可重复基线，不等于真实大模型能力。
- 正则 PII、关键词检索与启发式 Groundedness 都可能误报/漏报；它们是可解释基线，不是绝对安全或事实证明。
- SQLite 适合零配置演示，不代表并发生产数据库；本机性能数据不能外推为生产容量。
- 可选 OpenAI Provider 只实现单次 JSON 计划基线，启用前仍需增加真实模型输出的更严格结构化验证、限流、成本与隐私评审。
- Newman 当前上游依赖树在 `npm audit` 中含开发侧告警；未用破坏性的 `--force` 自动升级。运行服务不依赖 Node/Newman。

## 岗位能力映射

| 目标岗位 | 可以展示的真实证据 |
|---|---|
| 软件测试 | 等价类/边界/异常/权限/接口/UI/性能与缺陷闭环 |
| AI 测试 | 工具选择/参数、RAG 注入、PII、评测集、回归门禁 |
| 测试开发 | FastAPI、Pydantic、SQLAlchemy、pytest、Playwright、Newman、Locust、CI |
| 金融科技测试 | 对象级权限、二次确认、人工审批、幂等退款、审计证据 |
| 信息化技术 | 零配置 SQLite、可选 Provider、容器配置、运行与维护文档 |

## 已知限制

详见 [需求与边界](docs/requirements.md) 和 [威胁模型](docs/threat-model.md)。本次没有验证 Docker；没有连接真实模型、PostgreSQL 或云端 GitHub Actions；没有进行外部安全认证、分布式并发或真实金融合规评审。仓库尚未创建或推送。

## GitHub 发布状态

建议仓库：`lixinyi-qa/AgentGuard-AI`，建议设为 Public。当前目录只做了本地 Git 初始化，**没有创建 Commit、没有配置或冒用用户身份、没有创建远端仓库、没有推送**。正式公开前需项目所有者最终确认，并建议使用 GitHub noreply 邮箱。
