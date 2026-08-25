# 作品集演示脚本

## 演示前

运行 `uvicorn app.main:app --reload`，打开 Dashboard，确认“虚构沙箱”和 API 在线。准备 `reports/evaluation-latest.json`，不要配置真实 Key。

## 0:00～0:30 价值

指出普通聊天 Demo 看不到工具权限和副作用；本项目为 Agent 生成可审计证据。用架构图快速指到 Policy、Fault、Trace、Replay、Gate。

## 0:30～1:10 正常与越权

执行 CUST-001 查询 ACC-001：展示 query_account、参数、POL-002/POL-008。点击越权示例执行：展示 POL-010、blocked、side_effect=false。

## 1:10～1:50 故障与恢复

注入 query_account timeout 一次，再执行。展示 attempt 1 timeout、attempt 2 success，说明只读有限重试；写操作不自动重试。打开 `docs/defects/AGD-002` 说明真实缺陷闭环。

## 1:50～2:20 Replay

点击离线重放，说明使用保存且脱敏的响应，事件全部 `replayed`，不会重复退款或改联系方式。指出 trace_id 可查完整证据。

## 2:20～3:00 Evaluation 与边界

展示 40/40、PII 0、Gate PASS、版本对比和报告导出。最后主动说明：数据和银行虚构，离线 Provider 是测试替身，性能是本机基线，没有生产/监管认证。

## 失败时的备用路线

若现场端口被占用，改 `--port 8010`；若浏览器不可用，展示 `docs/assets` 截图和 reports；若依赖无法下载，使用已建 `.venv`。不要把未运行结果说成成功。

